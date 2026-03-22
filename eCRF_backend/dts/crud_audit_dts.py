from __future__ import annotations

from typing import Any, Dict, List, Optional

from eCRF_backend.dts.dts_client import DTSClient
from .dts_audit_mapping import (
    AUDIT_COLLECTION,
    AUDIT_CLASS,
    make_event_id,
    audit_event_pid,
    audit_event_to_dts_record,
    dts_audit_record_to_out,
)


def append_audit_event_to_dts(
    *,
    scope: str,
    action: str,
    event_time,
    study_id: Optional[int] = None,
    subject_index: Optional[int] = None,
    subject_id: Optional[str] = None,
    visit_index: Optional[int] = None,
    group_index: Optional[int] = None,
    actor_user_id: Optional[int] = None,
    actor_username: Optional[str] = None,
    actor_display_name: Optional[str] = None,
    actor_role: Optional[str] = None,
    ui_label: Optional[str] = None,
    has_diff: Optional[bool] = None,
    diff_kind: Optional[str] = None,
    diff_payload: Optional[Any] = None,
    related_entry_id: Optional[int] = None,
    related_file_id: Optional[int] = None,
    related_share_token: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    extra_json: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    client = DTSClient()
    event_id = make_event_id()
    payload = audit_event_to_dts_record(
        event_id=event_id,
        scope=scope,
        action=action,
        event_time=event_time,
        study_id=study_id,
        subject_index=subject_index,
        subject_id=subject_id,
        visit_index=visit_index,
        group_index=group_index,
        actor_user_id=actor_user_id,
        actor_username=actor_username,
        actor_display_name=actor_display_name,
        actor_role=actor_role,
        ui_label=ui_label,
        has_diff=has_diff,
        diff_kind=diff_kind,
        diff_payload=diff_payload,
        related_entry_id=related_entry_id,
        related_file_id=related_file_id,
        related_share_token=related_share_token,
        details=details,
        extra_json=extra_json,
    )
    client.post_record(AUDIT_COLLECTION, AUDIT_CLASS, payload)
    return payload


def get_audit_event_from_dts(event_id: str) -> Optional[Dict[str, Any]]:
    client = DTSClient()
    try:
        rec = client.get_record(AUDIT_COLLECTION, audit_event_pid(event_id))
        return dts_audit_record_to_out(rec) if rec else None
    except Exception:
        return None


def list_audit_events_from_dts(
    *,
    study_id: Optional[int] = None,
    subject_index: Optional[int] = None,
    action: Optional[str] = None,
    scope: Optional[str] = None,
) -> List[Dict[str, Any]]:
    client = DTSClient()
    records = client.list_records(AUDIT_COLLECTION, AUDIT_CLASS) or []
    out: List[Dict[str, Any]] = []

    for rec in records:
        if study_id is not None and rec.get("study_id") != study_id:
            continue
        if subject_index is not None and rec.get("subject_index") != subject_index:
            continue
        if action is not None and rec.get("action") != action:
            continue
        if scope is not None and rec.get("scope") != scope:
            continue
        out.append(dts_audit_record_to_out(rec))

    out.sort(key=lambda x: x.get("timestamp") or 0)
    return out