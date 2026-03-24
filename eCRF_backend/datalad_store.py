# eCRF_backend/datalad_store.py
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from sqlalchemy.orm import Session

from . import models
from .bids_exporter import _dataset_path, upsert_bids_dataset  # existing dataset root logic
from .datalad_config import DataladConfig, is_datalad_enabled
from .datalad_worker import DataladWorker

try:
    from datalad.api import Dataset  # type: ignore
except Exception:  # pragma: no cover
    Dataset = None  # type: ignore


@dataclass(frozen=True)
class StudyDatasetRefs:
    dataset_path: Path
    canonical_dir: Path


def _json_dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _study_slug_path(study_id: int, study_name: Optional[str]) -> Path:
    return Path(_dataset_path(study_id, study_name or f"study{study_id}"))


class DataladStudyStore:
    """
    DataLad-first persistence helper.
    - Uses the existing BIDS exporter dataset folder as the dataset root.
    - Writes canonical JSON snapshots under <dataset>/canonical/.
    - Schedules DataLad save/push via DataladWorker.
    """

    def __init__(self, cfg: DataladConfig, worker: Optional[DataladWorker]) -> None:
        self.cfg = cfg
        self.worker = worker

    def ensure_dataset(
        self,
        *,
        study_id: int,
        study_name: str,
        study_description: Optional[str],
        study_data: Dict[str, Any],
    ) -> StudyDatasetRefs:
        ds_path = _study_slug_path(study_id, study_name)

        # Ensure BIDS dataset structure exists (idempotent)
        # This preserves current behaviour and dataset layout.
        upsert_bids_dataset(
            study_id=study_id,
            study_name=study_name,
            study_description=study_description,
            study_data=study_data,
        )

        # Ensure it is a DataLad dataset (if enabled)
        if is_datalad_enabled(self.cfg):
            if Dataset is None:
                raise RuntimeError("DataLad not installed")
            ds = Dataset(str(ds_path))
            if not ds.is_installed():
                ds.create(force=True, cfg_proc="text2git")

        canonical = ds_path / "canonical"
        canonical.mkdir(parents=True, exist_ok=True)
        return StudyDatasetRefs(dataset_path=ds_path, canonical_dir=canonical)

    def write_study_snapshot(self, db: Session, study_id: int) -> StudyDatasetRefs:
        meta = db.query(models.StudyMetadata).filter_by(id=study_id).first()
        if not meta:
            raise ValueError(f"Study not found: {study_id}")
        content = db.query(models.StudyContent).filter_by(study_id=study_id).first()
        if not content:
            raise ValueError(f"Study content not found: {study_id}")

        sd = (content.study_data or {}) if isinstance(content.study_data, dict) else {}
        refs = self.ensure_dataset(
            study_id=study_id,
            study_name=meta.study_name,
            study_description=meta.study_description,
            study_data=sd,
        )

        # Canonical study files (schema-compatible JSON)
        _json_dump(
            refs.canonical_dir / "study_metadata.json",
            {
                "id": meta.id,
                "created_by": meta.created_by,
                "study_name": meta.study_name,
                "study_description": meta.study_description,
                "status": getattr(meta, "status", None),
                "draft_of_study_id": getattr(meta, "draft_of_study_id", None),
                "last_completed_step": getattr(meta, "last_completed_step", None),
                "created_at": meta.created_at.isoformat() if meta.created_at else None,
                "updated_at": meta.updated_at.isoformat() if meta.updated_at else None,
            },
        )
        _json_dump(
            refs.canonical_dir / "study_content.json",
            {
                "study_id": study_id,
                "study_data": sd,
            },
        )

        # Template versions
        tvs = (
            db.query(models.StudyTemplateVersion)
            .filter_by(study_id=study_id)
            .order_by(models.StudyTemplateVersion.version.asc())
            .all()
        )
        for tv in tvs:
            _json_dump(
                refs.canonical_dir / "templates" / f"v{int(tv.version):03d}" / "schema.json",
                {"study_id": study_id, "version": int(tv.version), "schema": tv.schema},
            )

        # Access grants snapshot (RBAC projection)
        grants = db.query(models.StudyAccessGrant).filter_by(study_id=study_id).all()
        _json_dump(
            refs.canonical_dir / "access_grants.json",
            [
                {
                    "study_id": g.study_id,
                    "user_id": g.user_id,
                    "permissions": g.permissions,
                    "created_by": g.created_by,
                    "created_at": g.created_at.isoformat() if g.created_at else None,
                }
                for g in grants
            ],
        )

        return refs

    def write_entry_snapshot(self, db: Session, entry_id: int) -> Tuple[int, Path]:
        entry = db.query(models.StudyEntryData).filter_by(id=entry_id).first()
        if not entry:
            raise ValueError(f"Entry not found: {entry_id}")

        meta = db.query(models.StudyMetadata).filter_by(id=entry.study_id).first()
        content = db.query(models.StudyContent).filter_by(study_id=entry.study_id).first()
        sd = (content.study_data or {}) if content and isinstance(content.study_data, dict) else {}
        refs = self.ensure_dataset(
            study_id=entry.study_id,
            study_name=meta.study_name if meta else f"study{entry.study_id}",
            study_description=meta.study_description if meta else None,
            study_data=sd,
        )

        # Sharded directory layout to avoid too many files per directory
        p = (
            refs.canonical_dir
            / "entries"
            / f"v{int(entry.form_version):03d}"
            / f"subject_{int(entry.subject_index):05d}"
            / f"visit_{int(entry.visit_index):05d}"
            / f"group_{int(entry.group_index):05d}"
            / f"entry_{int(entry.id):09d}.json"
        )
        _json_dump(
            p,
            {
                "id": entry.id,
                "study_id": entry.study_id,
                "form_version": entry.form_version,
                "subject_index": entry.subject_index,
                "visit_index": entry.visit_index,
                "group_index": entry.group_index,
                "data": entry.data or {},
                "skipped_required_flags": entry.skipped_required_flags,
                "created_at": entry.created_at.isoformat() if entry.created_at else None,
            },
        )
        return entry.study_id, p

    def schedule_save(self, refs: StudyDatasetRefs, message: str) -> None:
        if not is_datalad_enabled(self.cfg):
            return
        if self.worker is None:
            # synchronous fallback: try to save directly
            if Dataset is None:
                raise RuntimeError("DataLad not installed")
            Dataset(str(refs.dataset_path)).save(message=message)
            return
        self.worker.enqueue_save(refs.dataset_path, message=message)
