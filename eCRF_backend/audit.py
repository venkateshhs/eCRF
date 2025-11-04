from fastapi import  Depends, HTTPException, APIRouter
from typing import List
from sqlalchemy.orm import Session
from .database import get_db
from .crud import record_event
from .models import AuditEvent, User
from .schemas import EventOut, EventCreate

router = APIRouter(prefix="/audit", tags=["audit"])

@router.get("/studies/{study_id}/events", response_model=List[EventOut])
def get_study_events(study_id: int, db: Session = Depends(get_db)):
    """Retrieve all audit events for a given study (including subject events)."""
    events = db.query(AuditEvent).filter(AuditEvent.study_id == study_id).order_by(AuditEvent.timestamp).all()
    return events

@router.get("/studies/{study_id}/subjects/{subject_id}/events", response_model=List[EventOut])
def get_subject_events(study_id: int, subject_id: int, db: Session = Depends(get_db)):
    """Retrieve audit events for a specific subject within a study."""
    events = db.query(AuditEvent).filter(
        AuditEvent.study_id == study_id,
        AuditEvent.subject_id == subject_id
    ).order_by(AuditEvent.timestamp).all()
    return events

@router.post("/events", response_model=EventOut)
def create_audit_event(event: EventCreate, db: Session = Depends(get_db)):
    """
    Create a new audit event entry.
    (This could be used by internal services or admin tools to log events programmatically.)
    """
    # (Optional) validate that the referenced user exists
    user = db.query(User).filter(User.id == event.user_id).first()
    if user is None:
        raise HTTPException(status_code=400, detail="User not found")
    # Use the record_event utility to log the event
    new_event = record_event(
        db,
        user_id=event.user_id,
        study_id=event.study_id,
        subject_id=event.subject_id,
        action=event.action,
        details=event.details or {}
    )
    return new_event