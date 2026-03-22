from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .database import get_db
from .users import get_current_user
from .schemas import EventOut, EventCreate
from . import models
from .dts.crud_audit_dts import (
    append_audit_event_to_dts,
    list_audit_events_from_dts,
    get_audit_event_from_dts,
)
from .utils import local_now

router = APIRouter(prefix="/audit", tags=["audit"])


def _ensure_can_view_study(db: Session, user, study_id: int) -> None:
    # still using your study permission model for now
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


@router.get("/studies/{study_id}/events", response_model=List[EventOut])
def get_study_events(
    study_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    _ensure_can_view_study(db, current_user, study_id)
    return list_audit_events_from_dts(study_id=study_id)


@router.get("/studies/{study_id}/subjects/{subject_index}/events", response_model=List[EventOut])
def get_subject_events(
    study_id: int,
    subject_index: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    _ensure_can_view_study(db, current_user, study_id)
    return list_audit_events_from_dts(study_id=study_id, subject_index=subject_index)


@router.post("/events", response_model=EventOut)
def create_audit_event(
    event: EventCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    if event.study_id:
        _ensure_can_view_study(db, current_user, int(event.study_id))

    role = getattr(getattr(current_user, "profile", None), "role", None)
    payload = append_audit_event_to_dts(
        scope="study" if event.study_id else "system",
        action=event.action,
        event_time=local_now(),
        study_id=event.study_id,
        subject_index=event.subject_index,
        subject_id=event.subject_id,
        actor_user_id=getattr(current_user, "id", None),
        actor_username=getattr(current_user, "username", None),
        actor_display_name=(
            f"{getattr(getattr(current_user, 'profile', None), 'first_name', '')} "
            f"{getattr(getattr(current_user, 'profile', None), 'last_name', '')}"
        ).strip() or getattr(current_user, "username", None),
        actor_role=role,
        has_diff=bool(event.has_diff),
        diff_kind=event.diff_kind,
        diff_payload=event.diff,
        details=event.details or {},
    )
    out = get_audit_event_from_dts(payload["event_id"])
    if not out:
        raise HTTPException(status_code=500, detail="Audit event created but readback failed")
    return out


@router.get("/events/{event_id}/diff")
def read_audit_event_diff(
    event_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    ev = get_audit_event_from_dts(event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Audit event not found")

    if ev.get("study_id"):
        _ensure_can_view_study(db, current_user, int(ev["study_id"]))

    if not ev.get("has_diff"):
        raise HTTPException(status_code=404, detail="No diff available for this event")

    return {
        "event_id": ev["id"],
        "study_id": ev.get("study_id"),
        "diff_kind": ev.get("diff_kind"),
        "diff": ev.get("diff"),
    }