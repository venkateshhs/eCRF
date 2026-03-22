from __future__ import annotations

from typing import Dict, Any, List, Optional
from datetime import datetime

from eCRF_backend.dts.dts_client import DTSClient
from .dts_auth_mapping import (
    AUTH_COLLECTION,
    USER_CLASS,
    SESSION_CLASS,
    user_pid,
    session_pid,
    user_to_dts_record,
    session_to_dts_record,
    DTSUserShim,
    DTSUserSessionShim,
)


def _parse_dt(value: Optional[str]):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def list_users_from_dts() -> List[Dict[str, Any]]:
    client = DTSClient()
    records = client.list_records(AUTH_COLLECTION, USER_CLASS) or []
    out: List[Dict[str, Any]] = []
    for rec in records:
        out.append({
            "id": int(rec["user_id"]),
            "username": rec["username"],
            "email": rec["email"],
            "password_hash": rec.get("password_hash") or "",
            "first_name": rec.get("first_name") or "",
            "last_name": rec.get("last_name") or "",
            "role": rec.get("role") or "Investigator",
            "status": rec.get("status") or "ACTIVE",
            "created_at": _parse_dt(rec.get("created_at")),
            "updated_at": _parse_dt(rec.get("updated_at")),
            "pid": rec.get("pid"),
        })
    out.sort(key=lambda x: x["id"])
    return out


def get_user_from_dts_by_id(user_id: int):
    client = DTSClient()
    rec = client.get_record(AUTH_COLLECTION, user_pid(user_id))
    return DTSUserShim(rec) if rec else None


def get_user_from_dts_by_username(username: str):
    users = list_users_from_dts()
    for u in users:
        if u["username"] == username:
            return DTSUserShim({
                "user_id": u["id"],
                "username": u["username"],
                "email": u["email"],
                "password_hash": u["password_hash"],
                "first_name": u["first_name"],
                "last_name": u["last_name"],
                "role": u["role"],
                "status": u["status"],
                "created_at": u["created_at"].isoformat() if u["created_at"] else None,
                "updated_at": u["updated_at"].isoformat() if u["updated_at"] else None,
            })
    return None


def get_user_from_dts_by_email(email: str):
    users = list_users_from_dts()
    for u in users:
        if u["email"] == email:
            return DTSUserShim({
                "user_id": u["id"],
                "username": u["username"],
                "email": u["email"],
                "password_hash": u["password_hash"],
                "first_name": u["first_name"],
                "last_name": u["last_name"],
                "role": u["role"],
                "status": u["status"],
                "created_at": u["created_at"].isoformat() if u["created_at"] else None,
                "updated_at": u["updated_at"].isoformat() if u["updated_at"] else None,
            })
    return None


def next_user_id_from_dts() -> int:
    users = list_users_from_dts()
    if not users:
        return 1
    return max(u["id"] for u in users) + 1


def upsert_user_to_dts(
    *,
    user_id: int,
    username: str,
    email: str,
    password_hash: str,
    first_name: str,
    last_name: str,
    role: str,
    status: str = "ACTIVE",
    created_at=None,
    updated_at=None,
):
    client = DTSClient()
    payload = user_to_dts_record(
        user_id=user_id,
        username=username,
        email=email,
        password_hash=password_hash,
        first_name=first_name,
        last_name=last_name,
        role=role,
        status=status,
        created_at=created_at,
        updated_at=updated_at,
    )
    return client.post_record(AUTH_COLLECTION, USER_CLASS, payload)


def list_sessions_from_dts(user_id: Optional[int] = None) -> List[Dict[str, Any]]:
    client = DTSClient()
    records = client.list_records(AUTH_COLLECTION, SESSION_CLASS) or []
    out = []
    for rec in records:
        if user_id is not None and int(rec.get("user_id")) != int(user_id):
            continue
        out.append(rec)
    return out


def get_session_from_dts(jti: str):
    records = list_sessions_from_dts()
    for rec in records:
        if rec.get("jti") == jti:
            return DTSUserSessionShim(rec)
    return None


def upsert_session_to_dts(
    *,
    user_id: int,
    username: str,
    jti: str,
    created_at,
    last_activity_at,
    absolute_expires_at,
    revoked_at=None,
    client_info: Optional[Dict[str, Any]] = None,
):
    client = DTSClient()
    payload = session_to_dts_record(
        user_id=user_id,
        username=username,
        jti=jti,
        created_at=created_at,
        last_activity_at=last_activity_at,
        absolute_expires_at=absolute_expires_at,
        revoked_at=revoked_at,
        client_info=client_info,
    )
    return client.post_record(AUTH_COLLECTION, SESSION_CLASS, payload)


def revoke_session_in_dts(jti: str, revoked_at):
    sess = get_session_from_dts(jti)
    if not sess:
        return None
    return upsert_session_to_dts(
        user_id=sess.user_id,
        username=sess.username or "",
        jti=sess.jti,
        created_at=sess.created_at,
        last_activity_at=sess.last_activity_at,
        absolute_expires_at=sess.absolute_expires_at,
        revoked_at=revoked_at,
        client_info=None,
    )


def revoke_all_sessions_for_user_in_dts(user_id: int, revoked_at):
    sessions = list_sessions_from_dts(user_id=user_id)
    for rec in sessions:
        if rec.get("revoked_at"):
            continue
        upsert_session_to_dts(
            user_id=int(rec["user_id"]),
            username=rec.get("username") or "",
            jti=rec["jti"],
            created_at=_parse_dt(rec.get("created_at")),
            last_activity_at=_parse_dt(rec.get("last_activity_at")),
            absolute_expires_at=_parse_dt(rec.get("absolute_expires_at")),
            revoked_at=revoked_at,
            client_info=None,
        )
    return True