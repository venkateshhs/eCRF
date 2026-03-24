# eCRF_backend/datalad_api_routes.py
from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session


from .datalad_config import get_datalad_config, is_datalad_enabled
from .datalad_worker import DataladWorker
from .datalad_store import DataladStudyStore
from . import models
from .bids_exporter import _dataset_path
from .database import get_db
from .users import get_current_user

try:
    from datalad.api import Dataset  # type: ignore
except Exception:  # pragma: no cover
    Dataset = None  # type: ignore


router = APIRouter(prefix="/datalad", tags=["datalad-ops"])


@router.get("/status")
def datalad_status() -> Dict[str, object]:
    cfg = get_datalad_config()
    return {
        "mode": cfg.mode,
        "sync_mode": cfg.sync_mode,
        "push_on_save": cfg.push_on_save,
        "primary_study_ids": sorted(cfg.primary_study_ids),
        "ria_url": cfg.ria_url,
        "ria_name": cfg.ria_name,
    }


@router.get("/studies/{study_id}/dataset")
def inspect_study_dataset(
    study_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> Dict[str, object]:
    meta = db.query(models.StudyMetadata).filter_by(id=study_id).first()
    if not meta:
        raise HTTPException(404, "Study not found")
    ds_path = Path(_dataset_path(meta.id, meta.study_name))
    info = {"dataset_path": str(ds_path), "exists": ds_path.exists(), "is_datalad": (ds_path / ".datalad").exists()}
    if Dataset is not None and ds_path.exists():
        try:
            ds = Dataset(str(ds_path))
            info["installed"] = ds.is_installed()
        except Exception:
            info["installed"] = False
    return info


@router.post("/studies/{study_id}/push")
def push_study_dataset(
    study_id: int,
    to: Optional[str] = Query(None, description="Sibling name (defaults to cfg.ria_name)"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> Dict[str, str]:
    cfg = get_datalad_config()
    if not is_datalad_enabled(cfg):
        raise HTTPException(400, "DataLad mode is off")
    meta = db.query(models.StudyMetadata).filter_by(id=study_id).first()
    if not meta:
        raise HTTPException(404, "Study not found")
    ds_path = Path(_dataset_path(meta.id, meta.study_name))
    if not ds_path.exists():
        raise HTTPException(404, "Dataset path missing")
    if Dataset is None:
        raise HTTPException(500, "DataLad not installed")

    sib = to or cfg.ria_name
    ds = Dataset(str(ds_path))
    ds.push(to=sib, data="auto-if-wanted")
    return {"status": "ok", "pushed_to": sib}
