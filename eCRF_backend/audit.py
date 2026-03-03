from typing import List, Optional, Any, Dict
import os
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .database import get_db
from .users import get_current_user
from .crud import record_event
from .models import AuditEvent, User  # keep consistent
from .schemas import EventOut, EventCreate
from .bids_exporter import _dataset_path
from . import models  # for StudyMetadata / StudyAccessGrant (and models.User typing)

router = APIRouter(prefix="/audit", tags=["audit"])


# -------------------- permissions --------------------

def _ensure_can_view_study(db: Session, user: models.User, study_id: int) -> None:
    meta = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == study_id).first()
    if not meta:
        raise HTTPException(status_code=404, detail="Study not found")

    role = (getattr(getattr(user, "profile", None), "role", "") or "").strip()
    is_admin = role == "Administrator"
    is_owner = (meta.created_by == user.id)

    if is_admin or is_owner:
        return

    grant = db.query(models.StudyAccessGrant).filter_by(study_id=study_id, user_id=user.id).first()
    perms = (grant.permissions or {}) if grant else {}
    if not perms.get("view", False):
        raise HTTPException(status_code=403, detail="Not authorized")


def _safe_rel_path(rel_path: str) -> str:
    """
    Accept only a *relative* path (POSIX-ish or OS specific) and normalize.
    Reject absolute paths and parent traversal.
    """
    if not rel_path or not isinstance(rel_path, str):
        raise HTTPException(status_code=400, detail="Invalid diff path")

    # no absolute paths
    if os.path.isabs(rel_path):
        raise HTTPException(status_code=400, detail="Invalid diff path")

    # normalize, then reject traversal
    norm = os.path.normpath(rel_path).replace("\\", "/")
    if norm.startswith("../") or norm == ".." or "/../" in norm:
        raise HTTPException(status_code=400, detail="Invalid diff path")

    return norm


# -------------------- list endpoints --------------------

@router.get("/studies/{study_id}/events", response_model=List[EventOut])
def get_study_events(
    study_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Retrieve all audit events for a given study (including subject events).
    """
    _ensure_can_view_study(db, current_user, study_id)

    events = (
        db.query(AuditEvent)
        .filter(AuditEvent.study_id == study_id)
        .order_by(AuditEvent.timestamp)
        .all()
    )
    return events


@router.get("/studies/{study_id}/subjects/{subject_id}/events", response_model=List[EventOut])
def get_subject_events(
    study_id: int,
    subject_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Retrieve audit events for a specific subject within a study.
    """
    _ensure_can_view_study(db, current_user, study_id)

    events = (
        db.query(AuditEvent)
        .filter(AuditEvent.study_id == study_id, AuditEvent.subject_id == subject_id)
        .order_by(AuditEvent.timestamp)
        .all()
    )
    return events


# -------------------- create endpoint --------------------

@router.post("/events", response_model=EventOut)
def create_audit_event(
    event: EventCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Create a new audit event entry.
    Usually used by internal services/admin tools.
    """
    # optional: require view permission for that study (or restrict to admins)
    if event.study_id:
        _ensure_can_view_study(db, current_user, int(event.study_id))

    user = db.query(User).filter(User.id == event.user_id).first()
    if user is None:
        raise HTTPException(status_code=400, detail="User not found")

    new_event = record_event(
        db,
        user_id=event.user_id,
        study_id=event.study_id,
        subject_id=event.subject_id,
        action=event.action,
        details=event.details or {},
    )
    return new_event


# -------------------- diff endpoint (event-based) --------------------

@router.get("/events/{event_id}/diff")
def read_audit_event_diff(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Reads diff JSON for ONE audit event row.
    Uses diff_path stored in DB row (relative to dataset root).
    """
    ev = db.query(AuditEvent).filter(AuditEvent.id == event_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Audit event not found")

    if not ev.study_id:
        raise HTTPException(status_code=400, detail="This event is not study-scoped")

    _ensure_can_view_study(db, current_user, int(ev.study_id))

    # diff_path can be a dedicated column OR inside details
    details = ev.details or {}
    diff_path = getattr(ev, "diff_path", None) or details.get("diff_path")
    if not diff_path:
        raise HTTPException(status_code=404, detail="No diff available for this event")

    diff_path = _safe_rel_path(str(diff_path))

    # Resolve dataset root from study metadata
    meta = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == int(ev.study_id)).first()
    if not meta:
        raise HTTPException(status_code=404, detail="Study not found")

    dataset_root = _dataset_path(meta.id, meta.study_name)
    if not os.path.isdir(dataset_root):
        raise HTTPException(status_code=404, detail="BIDS dataset not found")

    # Resolve and re-check inside root
    full_path = os.path.abspath(os.path.join(dataset_root, diff_path))
    root_abs = os.path.abspath(dataset_root)
    if not full_path.startswith(root_abs + os.sep) and full_path != root_abs:
        raise HTTPException(status_code=400, detail="Invalid diff path")

    if not os.path.isfile(full_path):
        raise HTTPException(status_code=404, detail="Diff file missing on disk")

    try:
        with open(full_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read diff: {e}")

    return {
        "event_id": int(ev.id),
        "study_id": int(ev.study_id),
        "diff_path": diff_path,  # relative to dataset root
        "diff": payload,
    }