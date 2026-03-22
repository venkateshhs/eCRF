from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, Optional


AUTH_COLLECTION = "casee_auth"
USER_CLASS = "CaseeUser"
SESSION_CLASS = "CaseeUserSession"


def _safe_json_string(value: Any) -> str:
    try:
        return json.dumps(value if value is not None else {}, ensure_ascii=False)
    except Exception:
        return "{}"


def _safe_iso(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    try:
        return str(value)
    except Exception:
        return None


def _thing(pid: str, schema_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "pid": pid,
        "schema_type": schema_type,
        **payload,
    }


def user_pid(user_id: int) -> str:
    return f"casee:user:{int(user_id)}"


def session_pid(user_id: int, jti: str) -> str:
    return f"casee:user:{int(user_id)}:session:{jti}"


def user_to_dts_record(
    *,
    user_id: int,
    username: str,
    email: str,
    password_hash: str,
    first_name: str,
    last_name: str,
    role: str,
    status: str = "ACTIVE",
    created_at: Optional[Any] = None,
    updated_at: Optional[Any] = None,
    extra_json: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return _thing(
        user_pid(user_id),
        USER_CLASS,
        {
            "user_id": int(user_id),
            "username": username,
            "email": email,
            "password_hash": password_hash,
            "first_name": first_name,
            "last_name": last_name,
            "role": role,
            "status": status,
            "created_at": _safe_iso(created_at),
            "updated_at": _safe_iso(updated_at or created_at),
            "extra_json": _safe_json_string(extra_json or {}),
        },
    )


def session_to_dts_record(
    *,
    user_id: int,
    username: str,
    jti: str,
    created_at: Optional[Any],
    last_activity_at: Optional[Any],
    absolute_expires_at: Optional[Any],
    revoked_at: Optional[Any] = None,
    client_info: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return _thing(
        session_pid(user_id, jti),
        SESSION_CLASS,
        {
            "user_id": int(user_id),
            "username": username,
            "jti": jti,
            "created_at": _safe_iso(created_at),
            "last_activity_at": _safe_iso(last_activity_at),
            "absolute_expires_at": _safe_iso(absolute_expires_at),
            "revoked_at": _safe_iso(revoked_at),
            "client_info_json": _safe_json_string(client_info or {}),
            "extra_json": _safe_json_string({}),
        },
    )


def _parse_dt(value: Optional[str]):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


class DTSUserProfileShim:
    def __init__(self, record: Dict[str, Any]):
        self.first_name = record.get("first_name") or ""
        self.last_name = record.get("last_name") or ""
        self.role = record.get("role") or "Investigator"


class DTSUserShim:
    def __init__(self, record: Dict[str, Any]):
        self.id = int(record["user_id"])
        self.username = record["username"]
        self.email = record["email"]
        self.password = record.get("password_hash") or ""
        self.created_at = _parse_dt(record.get("created_at"))
        self.updated_at = _parse_dt(record.get("updated_at"))
        self.status = record.get("status") or "ACTIVE"
        self.profile = DTSUserProfileShim(record)


class DTSUserSessionShim:
    def __init__(self, record: Dict[str, Any]):
        self.user_id = int(record["user_id"])
        self.username = record.get("username")
        self.jti = record["jti"]
        self.created_at = _parse_dt(record.get("created_at"))
        self.last_activity_at = _parse_dt(record.get("last_activity_at"))
        self.absolute_expires_at = _parse_dt(record.get("absolute_expires_at"))
        self.revoked_at = _parse_dt(record.get("revoked_at"))