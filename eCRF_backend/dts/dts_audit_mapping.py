from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, Dict, Optional


AUDIT_COLLECTION = "casee_audit"
AUDIT_CLASS = "CaseeAuditEvent"


def audit_event_pid(event_id: str) -> str:
    return f"casee:audit:{event_id}"


def make_event_id() -> str:
    return uuid.uuid4().hex


def study_pid(study_id: int) -> str:
    return f"casee:study:{int(study_id)}"


def _safe_json_string(value: Any) -> str:
    try:
        return json.dumps(value if value is not None else {}, ensure_ascii=False)
    except Exception:
        return "{}"


def _json_loads_safe(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (dict, list, int, float, bool)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return value


def _safe_iso(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    try:
        return str(value)
    except Exception:
        return None


def _parse_dt(value: Optional[str]):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _thing(pid: str, schema_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "pid": pid,
        "schema_type": schema_type,
        **payload,
    }


def audit_event_to_dts_record(
    *,
    event_id: str,
    scope: str,
    action: str,
    event_time: Any,
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
    return _thing(
        audit_event_pid(event_id),
        AUDIT_CLASS,
        {
            "event_id": event_id,
            "scope": scope,
            "action": action,
            "event_time": _safe_iso(event_time),

            "study_id": study_id,
            "study_pid": study_pid(study_id) if isinstance(study_id, int) and study_id > 0 else None,

            "subject_index": subject_index,
            "subject_id": subject_id,

            "visit_index": visit_index,
            "group_index": group_index,

            "actor_user_id": actor_user_id,
            "actor_username": actor_username,
            "actor_display_name": actor_display_name,
            "actor_role": actor_role,

            "ui_label": ui_label,

            "has_diff": bool(has_diff) if has_diff is not None else False,
            "diff_kind": diff_kind,
            "diff_payload_json": _safe_json_string(diff_payload) if diff_payload is not None else None,

            "related_entry_id": related_entry_id,
            "related_file_id": related_file_id,
            "related_share_token": related_share_token,

            "details_json": _safe_json_string(details or {}),
            "extra_json": _safe_json_string(extra_json or {}),
        },
    )


def dts_audit_record_to_out(record: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(record.get("event_id") or ""),
        "study_id": record.get("study_id"),
        "subject_index": record.get("subject_index"),
        "subject_id": record.get("subject_id"),
        "visit_index": record.get("visit_index"),
        "group_index": record.get("group_index"),
        "action": record.get("action"),
        "timestamp": _parse_dt(record.get("event_time")),

        "actor_user_id": record.get("actor_user_id"),
        "actor_username": record.get("actor_username"),
        "actor_display_name": record.get("actor_display_name"),
        "actor_role": record.get("actor_role"),

        "details": _json_loads_safe(record.get("details_json")) or {},

        "has_diff": bool(record.get("has_diff", False)),
        "diff_kind": record.get("diff_kind"),
        "diff": _json_loads_safe(record.get("diff_payload_json")),

        "scope": record.get("scope"),
    }