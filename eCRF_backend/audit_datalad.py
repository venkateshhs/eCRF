from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .database import get_db
from . import models
from .users import get_current_user
from .datalad_repo import DataladStudyRepo

router = APIRouter(prefix="/audit", tags=["audit"])
repo = DataladStudyRepo()


def _is_admin(user: models.User) -> bool:
    role = (getattr(getattr(user, "profile", None), "role", "") or "").strip()
    return role == "Administrator"


def _ensure_can_view_study(db: Session, user: models.User, study_id: int) -> models.StudyMetadata:
    meta = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == study_id).first()
    if not meta:
        raise HTTPException(status_code=404, detail="Study not found")

    if _is_admin(user) or int(meta.created_by) == int(user.id):
        return meta

    grant = (
        db.query(models.StudyAccessGrant)
        .filter(
            models.StudyAccessGrant.study_id == study_id,
            models.StudyAccessGrant.user_id == user.id,
        )
        .first()
    )
    perms = (grant.permissions or {}) if grant else {}
    if not bool(perms.get("view", False)):
        raise HTTPException(status_code=403, detail="Not authorized")

    return meta


def _paths_for_study(study_id: int, study_name: str):
    p = repo.paths(study_id, study_name)
    return {
        "dataset": p.dataset_path,
        "study_dir": p.audit_system_study_dir,
        "subjects_root": p.audit_subject_dir,
        "canonical_dir": p.canonical_dir,
    }


def _subject_dir_prefix(subject_index: int) -> str:
    return f"subject_{int(subject_index):05d}"


def _resolve_subject_events_file(subjects_root: Path, subject_index: int) -> Path:
    """
    Supports both old and new folder naming:
      - subject_00000/events.jsonl
      - subject_00000_SUBJ-MC-001/events.jsonl
    """
    prefix = _subject_dir_prefix(subject_index)

    exact = subjects_root / prefix / "events.jsonl"
    if exact.exists() and exact.is_file():
        return exact

    matches = sorted(subjects_root.glob(f"{prefix}*"))
    for subdir in matches:
        if subdir.is_dir():
            events_file = subdir / "events.jsonl"
            if events_file.exists() and events_file.is_file():
                return events_file

    return subjects_root / prefix / "events.jsonl"


def _safe_iso_to_dt(value: Any) -> datetime:
    s = str(value or "").strip()
    if not s:
        return datetime.min.replace(tzinfo=timezone.utc)
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return datetime.min.replace(tzinfo=timezone.utc)


def _tail_lines(path: Path, limit: int) -> List[str]:
    if not path.exists() or not path.is_file():
        return []
    if limit <= 0:
        return []

    with path.open("rb") as f:
        f.seek(0, 2)
        end = f.tell()
        block_size = 8192
        data = b""
        pos = end
        newline_count = 0

        while pos > 0 and newline_count <= limit:
            read_size = min(block_size, pos)
            pos -= read_size
            f.seek(pos)
            chunk = f.read(read_size)
            data = chunk + data
            newline_count = data.count(b"\n")

        text = data.decode("utf-8", errors="ignore")
        lines = [ln for ln in text.splitlines() if ln.strip()]
        return lines[-limit:]


def _count_jsonl_lines(path: Path) -> int:
    if not path.exists() or not path.is_file():
        return 0
    count = 0
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                count += 1
    return count


def _load_jsonl_tail(path: Path, limit: int) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for line in _tail_lines(path, limit):
        try:
            row = json.loads(line)
            if isinstance(row, dict):
                rows.append(row)
        except Exception:
            continue
    rows.sort(key=lambda e: _safe_iso_to_dt(e.get("timestamp")), reverse=True)
    return rows[:limit]


def _iter_jsonl(path: Path):
    if not path.exists() or not path.is_file():
        return
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            try:
                row = json.loads(s)
            except Exception:
                continue
            if isinstance(row, dict):
                yield row


def _human_action(action: str) -> str:
    mapping = {
        "study_created": "Study created",
        "study_edited": "Study edited",
        "study_snapshot_written": "Published snapshot written",
        "entry_upserted": "Data entry saved",
        "entry_cloned_forward": "Data cloned forward",
        "file_added": "File added",
        "share_link_created": "Share link created",
        "access_changed": "Access changed",
        "access_revoked": "Access revoked",
    }
    return mapping.get(action, action.replace("_", " ").strip().capitalize())


def _build_summary(payload: Dict[str, Any], action: str) -> str:
    actor = str(payload.get("actor_name") or payload.get("actor") or "").strip()
    subject_raw = str(payload.get("subject_raw") or "").strip()
    visit_raw = str(payload.get("visit_raw") or "").strip()
    group_raw = str(payload.get("group_raw") or "").strip()
    ui_label = str(payload.get("ui_label") or "").strip()

    chunks: List[str] = []

    if actor:
        chunks.append(actor)

    chunks.append(_human_action(action))

    loc_parts: List[str] = []
    if subject_raw:
        loc_parts.append(f"Subject {subject_raw}")
    if visit_raw:
        loc_parts.append(f"Visit {visit_raw}")
    if group_raw:
        loc_parts.append(f"Group {group_raw}")

    if loc_parts:
        chunks.append("· " + " / ".join(loc_parts))

    if ui_label:
        chunks.append(f"· {ui_label}")

    return " ".join(chunks).strip()


def _normalize_event(event: Dict[str, Any]) -> Dict[str, Any]:
    payload = event.get("payload") or {}
    action = str(event.get("action") or "").strip()

    return {
        "id": event.get("id"),
        "timestamp": event.get("timestamp"),
        "action": action,
        "scope": event.get("scope") or "study",
        "study_id": event.get("study_id"),
        "payload": payload,
        "details": payload,
        "summary": _build_summary(payload, action),
        "user": str(payload.get("actor_name") or payload.get("actor") or "").strip(),
        "user_id": payload.get("user_id"),
        "subject_index": payload.get("subject_index"),
        "visit_index": payload.get("visit_index"),
        "group_index": payload.get("group_index"),
        "subject_raw": payload.get("subject_raw"),
        "visit_raw": payload.get("visit_raw"),
        "group_raw": payload.get("group_raw"),
        "ui_label": payload.get("ui_label"),
        "diff_available": bool(event.get("diff_available")),
        "diff_path": event.get("diff_path"),
    }


def _read_events_from_jsonl(path: Path, limit: int) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for row in _load_jsonl_tail(path, limit):
        out.append(_normalize_event(row))
    return out


def _find_event_in_jsonl(path: Path, event_id: str) -> Optional[Dict[str, Any]]:
    if not path.exists() or not path.is_file():
        return None
    found: Optional[Dict[str, Any]] = None
    for row in _iter_jsonl(path):
        if str(row.get("id") or "") == str(event_id):
            found = row
    return found


def _find_event_record(
    study_id: int,
    study_name: str,
    event_id: str,
    *,
    subject_index: Optional[int] = None,
) -> Dict[str, Any]:
    paths = _paths_for_study(study_id, study_name)

    candidates: List[Path] = []
    if subject_index is not None:
        candidates.append(_resolve_subject_events_file(paths["subjects_root"], subject_index))
    candidates.append(paths["study_dir"] / "events.jsonl")

    for events_file in candidates:
        row = _find_event_in_jsonl(events_file, event_id)
        if row:
            return row

    if subject_index is None and paths["subjects_root"].exists():
        for subdir in sorted(paths["subjects_root"].glob("subject_*")):
            row = _find_event_in_jsonl(subdir / "events.jsonl", event_id)
            if row:
                return row

    raise HTTPException(status_code=404, detail="Audit event not found")


@router.get("/studies/{study_id}/events")
def get_study_events(
    study_id: int,
    limit: int = Query(200, ge=1, le=5000),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    meta = _ensure_can_view_study(db, current_user, study_id)
    paths = _paths_for_study(study_id, meta.study_name)
    return _read_events_from_jsonl(paths["study_dir"] / "events.jsonl", limit)


@router.get("/studies/{study_id}/subjects/{subject_index}/events")
def get_subject_events(
    study_id: int,
    subject_index: int,
    limit: int = Query(200, ge=1, le=5000),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    meta = _ensure_can_view_study(db, current_user, study_id)
    paths = _paths_for_study(study_id, meta.study_name)
    events_file = _resolve_subject_events_file(paths["subjects_root"], subject_index)
    return _read_events_from_jsonl(events_file, limit)


@router.get("/studies/{study_id}/subjects/{subject_index}/history")
def get_subject_history(
    study_id: int,
    subject_index: int,
    limit: int = Query(200, ge=1, le=5000),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    meta = _ensure_can_view_study(db, current_user, study_id)
    paths = _paths_for_study(study_id, meta.study_name)
    events_file = _resolve_subject_events_file(paths["subjects_root"], subject_index)
    events = _read_events_from_jsonl(events_file, limit)
    return {
        "study_id": study_id,
        "subject_index": subject_index,
        "events": events,
    }


@router.get("/studies/{study_id}/events/{event_id}")
def get_audit_event(
    study_id: int,
    event_id: str,
    subject_index: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    meta = _ensure_can_view_study(db, current_user, study_id)
    raw = _find_event_record(
        study_id,
        meta.study_name,
        event_id,
        subject_index=subject_index,
    )
    return _normalize_event(raw)


@router.get("/studies/{study_id}/events/{event_id}/diff")
def get_audit_event_diff(
    study_id: int,
    event_id: str,
    subject_index: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    meta = _ensure_can_view_study(db, current_user, study_id)
    raw = _find_event_record(
        study_id,
        meta.study_name,
        event_id,
        subject_index=subject_index,
    )

    diff_rel = raw.get("diff_path")
    if not diff_rel:
        raise HTTPException(status_code=404, detail="No diff available for this event")

    diff_abs = _paths_for_study(study_id, meta.study_name)["canonical_dir"] / str(diff_rel)
    if not diff_abs.exists() or not diff_abs.is_file():
        raise HTTPException(status_code=404, detail="Diff file not found")

    try:
        diff_data = json.loads(diff_abs.read_text(encoding="utf-8"))
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to read diff")

    return {
        "event_id": event_id,
        "study_id": study_id,
        "action": raw.get("action"),
        "diff_path": diff_rel,
        "diff": diff_data,
    }


@router.get("/studies/{study_id}/audit-overview")
def get_audit_overview(
    study_id: int,
    subject_limit: int = Query(100, ge=1, le=5000),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    meta = _ensure_can_view_study(db, current_user, study_id)
    paths = _paths_for_study(study_id, meta.study_name)

    study_events_file = paths["study_dir"] / "events.jsonl"
    latest_study_events = _read_events_from_jsonl(study_events_file, 50)

    subjects_root = paths["subjects_root"]
    subject_summaries: List[Dict[str, Any]] = []

    if subjects_root.exists() and subjects_root.is_dir():
        for subdir in sorted(subjects_root.glob("subject_*")):
            if not subdir.is_dir():
                continue

            events_file = subdir / "events.jsonl"
            latest = _read_events_from_jsonl(events_file, 1)
            if not latest:
                continue

            latest_event = latest[0]
            subject_summaries.append({
                "subject_index": latest_event.get("subject_index"),
                "subject_raw": latest_event.get("subject_raw"),
                "events_count": _count_jsonl_lines(events_file),
                "latest_event": latest_event,
            })

    subject_summaries.sort(
        key=lambda x: _safe_iso_to_dt((x.get("latest_event") or {}).get("timestamp")),
        reverse=True,
    )

    return {
        "study_id": study_id,
        "study_name": meta.study_name,
        "study_events_count": _count_jsonl_lines(study_events_file),
        "latest_study_events": latest_study_events,
        "subjects_count_with_audit": len(subject_summaries),
        "subjects": subject_summaries[:subject_limit],
    }