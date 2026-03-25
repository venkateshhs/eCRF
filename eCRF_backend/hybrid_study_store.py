from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from sqlalchemy.orm import Session

from . import models
from .datalad_repo import DataladStudyRepo, _deepcopy_json
from .bids_exporter_datalad import _dataset_path
from .logger import logger


class HybridStudyStore:
    """
    Hybrid source-of-truth rules:
    - DRAFT study        -> DB StudyContent is authoritative
    - PUBLISHED/ARCHIVED -> DataLad canonical content is authoritative
    - Template versions  -> DB StudyTemplateVersion is authoritative
    - Entries/files/audit -> DataLad authoritative
    """

    def __init__(self) -> None:
        self.repo = DataladStudyRepo()

    def _latest_template_row(self, db: Session, study_id: int) -> Optional[models.StudyTemplateVersion]:
        return (
            db.query(models.StudyTemplateVersion)
            .filter(models.StudyTemplateVersion.study_id == study_id)
            .order_by(models.StudyTemplateVersion.version.desc())
            .first()
        )

    def read_study_full(self, db: Session, study_id: int) -> Tuple[models.StudyMetadata, Dict[str, Any]]:
        meta = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == study_id).first()
        if not meta:
            raise FileNotFoundError("Study not found")

        status = (meta.status or "PUBLISHED").upper().strip()

        if status == "DRAFT":
            content_row = (
                db.query(models.StudyContent)
                .filter(models.StudyContent.study_id == study_id)
                .first()
            )
            if not content_row:
                raise FileNotFoundError("Draft study content not found")

            content = {
                "id": content_row.id,
                "study_id": content_row.study_id,
                "study_data": _deepcopy_json(content_row.study_data or {}),
            }
            return meta, content

        ds_content = self.repo.read_study(meta.id, meta.study_name)["content"]
        if "id" not in ds_content:
            ds_content["id"] = meta.id
        if "study_id" not in ds_content:
            ds_content["study_id"] = meta.id
        return meta, ds_content

    def create_draft_content(
        self,
        db: Session,
        *,
        study_id: int,
        study_data: Dict[str, Any],
    ) -> models.StudyContent:
        row = models.StudyContent(
            study_id=study_id,
            study_data=_deepcopy_json(study_data or {}),
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row

    def update_draft_content(
        self,
        db: Session,
        *,
        study_id: int,
        study_data: Dict[str, Any],
    ) -> models.StudyContent:
        row = (
            db.query(models.StudyContent)
            .filter(models.StudyContent.study_id == study_id)
            .first()
        )
        if not row:
            row = models.StudyContent(study_id=study_id, study_data={})
            db.add(row)

        row.study_data = _deepcopy_json(study_data or {})
        db.commit()
        db.refresh(row)
        return row

    def publish_study_from_db(
        self,
        db: Session,
        *,
        study_id: int,
    ) -> Dict[str, Any]:
        meta = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == study_id).first()
        if not meta:
            raise FileNotFoundError("Study not found")

        content_row = (
            db.query(models.StudyContent)
            .filter(models.StudyContent.study_id == study_id)
            .first()
        )
        if not content_row:
            raise FileNotFoundError("Study content not found")

        latest_template = self._latest_template_row(db, study_id)
        if not latest_template:
            raise FileNotFoundError("Template version not found")

        result = self.repo.create_or_replace_published_snapshot(
            study_id=meta.id,
            study_name=meta.study_name,
            study_description=meta.study_description or "",
            study_data=_deepcopy_json(content_row.study_data or {}),
            template_version=int(latest_template.version),
            template_schema=_deepcopy_json(latest_template.schema or {}),
            created_by=meta.created_by,
            status="PUBLISHED",
            draft_of_study_id=meta.draft_of_study_id,
            last_completed_step=meta.last_completed_step,
        )

        # optional published tracking columns if you add them in DB
        if hasattr(meta, "published_dataset_path"):
            meta.published_dataset_path = str(Path(_dataset_path(meta.id, meta.study_name)))
        if hasattr(meta, "published_template_version"):
            meta.published_template_version = int(latest_template.version)

        meta.status = "PUBLISHED"
        db.commit()
        db.refresh(meta)

        return {
            "metadata": meta,
            "content": result["content"],
        }

    def read_template_for_study(self, db: Session, study_id: int, version: Optional[int] = None) -> Dict[str, Any]:
        meta = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == study_id).first()
        if not meta:
            raise FileNotFoundError("Study not found")

        q = db.query(models.StudyTemplateVersion).filter(models.StudyTemplateVersion.study_id == study_id)
        if version is not None:
            row = q.filter(models.StudyTemplateVersion.version == version).first()
        else:
            row = q.order_by(models.StudyTemplateVersion.version.desc()).first()

        if not row:
            raise FileNotFoundError("Template version not found")

        return {
            "study_id": study_id,
            "version": row.version,
            "schema": row.schema,
            "created_at": row.created_at,
        }