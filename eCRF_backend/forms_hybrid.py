from __future__ import annotations

import json
import os
import secrets
import shutil
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import jwt
from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File, Form, Body, Request, status
from fastapi import Header
from fastapi.responses import FileResponse, RedirectResponse

from sqlalchemy.orm import Session

from .database import get_db
from . import schemas, models
from .users import get_current_user
from .datalad_repo import DataladStudyRepo, _deepcopy_json, local_now
from .study_activity import (
    cleanup_stale_shared_views,
    expire_shared_view_for_token,
    record_study_activity,
    release_activity_by_session,
)
from .pending_remote_deletes import enqueue_pending_remote_delete
from .versions import VersionManager
from .settings import get_settings
from .auth import SECRET_KEY, ALGORITHM
from .logger import logger

router = APIRouter(prefix="/forms", tags=["forms"])
repo = DataladStudyRepo()
MAINTENANCE_MESSAGE = "eCRF is under maintenance. Please try again later."

settings = get_settings()
TEMPLATE_DIR = (
    Path(os.environ.get("ECRF_TEMPLATES_DIR", "")).expanduser().resolve()
    if os.environ.get("ECRF_TEMPLATES_DIR")
    else (
        settings.templates_dir
        if settings.templates_dir is not None
        else (Path(__file__).resolve().parent / "templates")
    )
)

ALLOWED_STUDY_STATUS = {"DRAFT", "PUBLISHED", "ARCHIVED"}


def _normalize_allowed_section_ids(section_ids: Optional[List[Any]]) -> List[str]:
    if not section_ids:
        return []
    out: List[str] = []
    seen = set()
    for x in section_ids:
        s = str(x or "").strip()
        if not s or s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out


def _norm_status(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    s2 = str(s).strip().upper()
    return s2 if s2 in ALLOWED_STUDY_STATUS else None


def _display_name(u) -> str:
    if not u:
        return ""
    first = getattr(getattr(u, "profile", None), "first_name", "") or ""
    last = getattr(getattr(u, "profile", None), "last_name", "") or ""
    full = (first + " " + last).strip()
    return full or getattr(u, "username", "") or getattr(u, "email", "") or f"User#{getattr(u, 'id', '')}"


def _actor_identifier(u) -> str:
    if not u:
        return ""
    return (
        getattr(u, "email", None)
        or getattr(u, "username", None)
        or _display_name(u)
        or f"User#{getattr(u, 'id', '')}"
    )


ENTRY_PROGRESS_STATUSES = {"none", "partial", "complete", "skipped"}


def _clamp_progress_int(value: Any, default: int = 0, max_value: Optional[int] = None) -> int:
    try:
        n = int(value)
    except Exception:
        n = default
    n = max(0, n)
    if max_value is not None:
        n = min(max_value, n)
    return n


def _entry_progress_values(payload: Any) -> Dict[str, Any]:
    total = _clamp_progress_int(getattr(payload, "progress_total", None))
    completed = _clamp_progress_int(getattr(payload, "progress_completed", None))
    skipped = _clamp_progress_int(getattr(payload, "progress_skipped", None))
    percentage = _clamp_progress_int(getattr(payload, "progress_percentage", None), max_value=100)
    status = str(getattr(payload, "progress_status", None) or "").strip().lower()

    if status not in ENTRY_PROGRESS_STATUSES:
        if total <= 0 or completed <= 0:
            status = "none"
        elif skipped > 0:
            status = "skipped"
        elif percentage >= 100:
            status = "complete"
        else:
            status = "partial"

    return {
        "progress_status": status,
        "progress_percentage": percentage,
        "progress_completed": completed,
        "progress_total": total,
        "progress_skipped": skipped,
    }


def _session_jti_from_authorization(authorization: Optional[str]) -> Optional[str]:
    try:
        if not authorization or not authorization.startswith("Bearer "):
            return None
        token = authorization.split("Bearer ", 1)[1]
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_exp": False},
        )
        return payload.get("jti")
    except Exception:
        return None


def _latest_remote_reference(db: Session, study_id: int) -> tuple[Optional[str], Optional[Path]]:
    rows = (
        db.query(models.StudyActivity)
        .filter(
            models.StudyActivity.study_id == int(study_id),
            models.StudyActivity.metadata_json.isnot(None),
        )
        .order_by(models.StudyActivity.last_sync_at.desc(), models.StudyActivity.id.desc())
        .all()
    )

    for row in rows:
        metadata = row.metadata_json or {}
        if isinstance(metadata, dict) and metadata.get("dataset_id"):
            source_path = None
            if row.dataset_path:
                source_path = Path(row.dataset_path).expanduser().resolve()
            return str(metadata["dataset_id"]), source_path
    return None, None


def _latest_remote_dataset_id(db: Session, study_id: int) -> Optional[str]:
    dataset_id, _source_path = _latest_remote_reference(db, study_id)
    return dataset_id


def _raise_storage_unavailable(exc: Exception, *, context: str) -> None:
    logger.exception("%s failed because JTrack/Juseless storage is unavailable", context)
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=MAINTENANCE_MESSAGE,
    ) from exc


def _local_study_dataset_is_usable(dataset_path: Path) -> bool:
    if not dataset_path.exists():
        return False
    return bool(repo.dataset_id(dataset_path))


def _move_invalid_local_study_dataset(dataset_path: Path, *, study_id: int) -> None:
    if not dataset_path.exists():
        return
    if not dataset_path.is_dir():
        raise RuntimeError(f"Study dataset path exists but is not a directory: {dataset_path}")

    root = repo.root.expanduser().resolve()
    resolved_path = dataset_path.expanduser().resolve()
    try:
        resolved_path.relative_to(root)
    except ValueError as exc:
        raise RuntimeError(f"Refusing to move dataset outside BIDS root: {resolved_path}") from exc

    expected_prefix = f"study_{int(study_id)}_"
    if not resolved_path.name.startswith(expected_prefix):
        raise RuntimeError(
            f"Refusing to move unexpected study folder '{resolved_path.name}' for study_id={study_id}"
        )

    backup_path = resolved_path.with_name(f"{resolved_path.name}.invalid-{int(time.time())}")
    suffix = 1
    while backup_path.exists():
        backup_path = resolved_path.with_name(
            f"{resolved_path.name}.invalid-{int(time.time())}-{suffix}"
        )
        suffix += 1
    logger.warning(
        "Local study dataset path exists but is not a DataLad dataset; moving aside path=%s backup=%s",
        resolved_path,
        backup_path,
    )
    shutil.move(str(resolved_path), str(backup_path))


def _ensure_local_study_dataset(db: Session, meta: models.StudyMetadata) -> Path:
    paths = repo.paths(meta.id, meta.study_name)
    if paths.dataset_path.exists():
        if _local_study_dataset_is_usable(paths.dataset_path):
            return paths.dataset_path
        _move_invalid_local_study_dataset(paths.dataset_path, study_id=meta.id)

    dataset_id, source_dataset_path = _latest_remote_reference(db, meta.id)
    if not dataset_id:
        raise RuntimeError(
            "Study dataset is not present on JTrack and no Juseless dataset id is available."
        )
    return repo.clone_study_from_remote(
        meta.id,
        meta.study_name,
        dataset_id,
        source_dataset_path=source_dataset_path,
    ).dataset_path


def _record_shared_activity(
    db: Session,
    *,
    meta: models.StudyMetadata,
    dataset_path: Path,
    token: str,
    session_jti: str,
    purpose: str,
) -> None:
    metadata = {
        "study_name": meta.study_name,
        "shared_token": token,
    }
    dataset_id = repo.dataset_id(dataset_path)
    if dataset_id:
        metadata["dataset_id"] = dataset_id

    record_study_activity(
        db,
        study_id=meta.id,
        dataset_path=dataset_path,
        user_id=None,
        session_jti=session_jti,
        purpose=purpose,
        metadata=metadata,
    )


def _activity_metadata(meta: models.StudyMetadata, dataset_path: Path, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    metadata: Dict[str, Any] = {"study_name": meta.study_name}
    dataset_id = repo.dataset_id(dataset_path)
    if dataset_id:
        metadata["dataset_id"] = dataset_id
    if extra:
        metadata.update(extra)
    return metadata


def _record_authenticated_activity(
    db: Session,
    *,
    meta: models.StudyMetadata,
    dataset_path: Path,
    user,
    authorization: Optional[str],
    purpose: str,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    record_study_activity(
        db,
        study_id=meta.id,
        dataset_path=dataset_path,
        user_id=getattr(user, "id", None),
        session_jti=_session_jti_from_authorization(authorization),
        purpose=purpose,
        metadata=_activity_metadata(meta, dataset_path, extra),
    )


def _ensure_local_study_dataset_for_write(
    db: Session,
    meta: models.StudyMetadata,
    *,
    allow_create_if_missing: bool = False,
) -> Path:
    paths = repo.paths(meta.id, meta.study_name)
    if paths.dataset_path.exists():
        if _local_study_dataset_is_usable(paths.dataset_path):
            return paths.dataset_path
        _move_invalid_local_study_dataset(paths.dataset_path, study_id=meta.id)

    dataset_id, source_dataset_path = _latest_remote_reference(db, meta.id)
    if dataset_id:
        return repo.clone_study_from_remote(
            meta.id,
            meta.study_name,
            dataset_id,
            source_dataset_path=source_dataset_path,
        ).dataset_path

    if allow_create_if_missing:
        return repo.ensure_dataset(meta.id, meta.study_name).dataset_path

    raise RuntimeError(
        "Study dataset is not present on JTrack and no Juseless dataset id is available."
    )


def _move_prepared_dataset_if_study_was_renamed(
    *,
    study_id: int,
    old_study_name: str,
    new_study_name: str,
    prepared_path: Optional[Path],
) -> Optional[Path]:
    if not prepared_path:
        return None

    old_path = repo.paths(study_id, old_study_name).dataset_path
    new_path = repo.paths(study_id, new_study_name).dataset_path
    if old_path == new_path:
        return prepared_path

    if old_path.exists() and not new_path.exists():
        new_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(old_path), str(new_path))
        return new_path

    return new_path if new_path.exists() else prepared_path


def _is_admin(user) -> bool:
    role = (getattr(getattr(user, "profile", None), "role", "") or "").strip()
    return role == "Administrator"


def _assert_owner_or_admin(meta: models.StudyMetadata, user) -> None:
    if meta.created_by != user.id and not _is_admin(user):
        raise HTTPException(status_code=403, detail="Not authorized")


def _effective_study_permissions(db: Session, meta: models.StudyMetadata, user) -> Dict[str, bool]:
    if _is_admin(user) or int(meta.created_by) == int(user.id):
        return {"view": True, "add_data": True, "edit_study": True}

    grant = (
        db.query(models.StudyAccessGrant)
        .filter(
            models.StudyAccessGrant.study_id == meta.id,
            models.StudyAccessGrant.user_id == user.id,
        )
        .first()
    )
    if not grant:
        return {"view": False, "add_data": False, "edit_study": False}

    perms = grant.permissions or {}
    return {
        "view": bool(perms.get("view", True)),
        "add_data": bool(perms.get("add_data", True)),
        "edit_study": bool(perms.get("edit_study", False)),
    }


def _assert_has_study_permission(db: Session, meta: models.StudyMetadata, user, required: str = "view") -> Dict[str, bool]:
    perms = _effective_study_permissions(db, meta, user)
    if not perms.get(required, False):
        raise HTTPException(status_code=403, detail="Not authorized")
    return perms

def _assert_can_download_study_file(db: Session, meta: models.StudyMetadata, user) -> Dict[str, bool]:
    """
    Allow file download only for:
    - owner
    - admin
    - users who have all 3 permissions: view, add_data, edit_study
    """
    perms = _effective_study_permissions(db, meta, user)

    if _is_admin(user) or int(meta.created_by) == int(user.id):
        return perms

    if perms.get("view") and perms.get("add_data") and perms.get("edit_study"):
        return perms

    raise HTTPException(status_code=403, detail="Not authorized to download files")

def _assert_not_locked_by_other(meta: models.StudyMetadata, user) -> None:
    """
    Block actions when another user currently holds the study edit lock.

    Allowed:
    - study is not locked
    - study is locked by the same user

    Blocked:
    - study is locked by a different user
    """
    # Locking mechanism is stopped for now.
    # if bool(getattr(meta, "is_locked", False)) and getattr(meta, "locked_by", None) not in (None, user.id):
    #     raise HTTPException(
    #         status_code=423,
    #         detail=f"Study is currently being edited by user_id={meta.locked_by}",
    #     )
    return

def _require_lock_holder(meta: models.StudyMetadata, user) -> None:
    """
    Require that the study is actively locked and that the current user holds the lock.

    Nobody bypasses this check.
    """
    # if not bool(getattr(meta, "is_locked", False)):
    #     raise HTTPException(status_code=409, detail="Study is not locked for editing")
    #
    # if getattr(meta, "locked_by", None) != user.id:
    #     raise HTTPException(status_code=423, detail="You do not hold the study edit lock")
    return



def _get_content_row_or_404(db: Session, study_id: int) -> models.StudyContent:
    row = db.query(models.StudyContent).filter(models.StudyContent.study_id == study_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Study content not found")
    return row





def _ensure_initial_version_if_missing(db: Session, study_id: int, study_data: Dict[str, Any]) -> models.StudyTemplateVersion:
    VersionManager.ensure_initial_version(db, study_id, study_data or {})
    row = VersionManager.latest(db, study_id)
    if row is None:
        raise HTTPException(status_code=500, detail="Failed to initialize template version")
    return row


def _latest_template_or_500(db: Session, study_id: int) -> models.StudyTemplateVersion:
    row = VersionManager.latest(db, study_id)
    if row is None:
        raise HTTPException(status_code=500, detail="Template version not found")
    return row


def _resolve_form_version_or_400(db: Session, study_id: int, version: Optional[int]) -> int:
    try:
        return VersionManager.assert_latest_is_used(db, study_id, version)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


def _parse_modalities_json(modalities_json: Optional[str]) -> List[str]:
    try:
        modalities = json.loads(modalities_json or "[]")
        if not isinstance(modalities, list):
            return []
        out: List[str] = []
        seen = set()
        for item in modalities:
            s = str(item or "").strip()
            if not s or s in seen:
                continue
            seen.add(s)
            out.append(s)
        return out
    except Exception:
        return []


def _write_published_snapshot_to_datalad(
    *,
    meta: models.StudyMetadata,
    study_data: Dict[str, Any],
    template_version: int,
    template_schema: Dict[str, Any],
    actor: Optional[str] = None,
    actor_name: Optional[str] = None,
    user_id: Optional[int] = None,
    audit_label: Optional[str] = None,
) -> Dict[str, Any]:
    schema_payload = _deepcopy_json(template_schema or {})
    if isinstance(schema_payload, dict):
        schema_payload["version"] = int(template_version)

    return repo.create_or_replace_published_snapshot(
        study_id=meta.id,
        study_name=meta.study_name,
        study_description=meta.study_description or "",
        study_data=_deepcopy_json(study_data or {}),
        template_schema=schema_payload,
        created_by=meta.created_by,
        status=(meta.status or "PUBLISHED"),
        draft_of_study_id=meta.draft_of_study_id,
        last_completed_step=meta.last_completed_step,
        actor=actor,
        actor_name=actor_name,
        user_id=user_id,
        audit_label=audit_label,
    )


def _filter_shared_study_data_by_sections(study_data: Dict[str, Any], allowed_section_ids: Optional[List[str]]) -> Dict[str, Any]:
    raw = _deepcopy_json(study_data or {})
    allowed_ids = set(_normalize_allowed_section_ids(allowed_section_ids))
    if not allowed_ids:
        return raw

    selected_models = raw.get("selectedModels") or []
    assignments = raw.get("assignments") or []

    filtered_models = []
    filtered_assignments = []

    for m_idx, sec in enumerate(selected_models):
        if not isinstance(sec, dict):
            continue
        sec_id = str(sec.get("_id") or sec.get("id") or "").strip()
        if sec_id and sec_id in allowed_ids:
            filtered_models.append(sec)
            if isinstance(assignments, list) and m_idx < len(assignments):
                filtered_assignments.append(assignments[m_idx])

    raw["selectedModels"] = filtered_models
    raw["assignments"] = filtered_assignments
    return raw


def _allowed_shared_section_title_map(study_data: Dict[str, Any], allowed_section_ids: Optional[List[str]]) -> Dict[str, str]:
    selected_models = (study_data or {}).get("selectedModels") or []
    allowed_ids = set(_normalize_allowed_section_ids(allowed_section_ids))
    out: Dict[str, str] = {}

    for sec in selected_models:
        if not isinstance(sec, dict):
            continue
        sec_title = str(sec.get("title") or "").strip()
        sec_id = str(sec.get("_id") or sec.get("id") or "").strip()
        if not sec_title:
            continue
        if not allowed_ids:
            out[sec_title] = sec_id
        elif sec_id and sec_id in allowed_ids:
            out[sec_title] = sec_id
    return out


def _validate_shared_payload_sections(payload_data: Dict[str, Any], study_data: Dict[str, Any], allowed_section_ids: Optional[List[str]]) -> None:
    if not isinstance(payload_data, dict):
        raise HTTPException(status_code=400, detail="Invalid payload data")

    allowed_title_map = _allowed_shared_section_title_map(study_data or {}, allowed_section_ids)
    allowed_titles = set(allowed_title_map.keys())

    if not allowed_titles and payload_data:
        raise HTTPException(status_code=403, detail="This shared link does not allow data entry for any section")

    unexpected = [k for k in payload_data.keys() if str(k) not in allowed_titles]
    if unexpected:
        raise HTTPException(
            status_code=403,
            detail=f"Payload contains non-shared sections: {', '.join(sorted(map(str, unexpected)))}"
        )


def _flags_dict_to_list(flags, selected_models):
    if isinstance(flags, list):
        return flags
    if not isinstance(flags, dict):
        return []
    out = []
    for sec in (selected_models or []):
        title = (sec.get("title") or "").strip()
        row = []
        fields = sec.get("fields") or []
        inner = flags.get(title, {}) if isinstance(flags.get(title), dict) else {}
        for idx, f in enumerate(fields):
            key = f.get("name") or f.get("label") or f.get("key") or f.get("title") or f"f{idx}"
            row.append(bool(inner.get(key, False)))
        out.append(row)
    return out


@router.get("/available-fields")
async def get_available_fields():
    path = TEMPLATE_DIR / "available-fields.json"
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        raise HTTPException(status_code=500, detail="Error loading available fields.")


@router.get("/specialized-fields")
async def get_specialized_fields():
    path = TEMPLATE_DIR / "specialized-fields.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Available fields file not found.")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading available fields: {str(e)}")


@router.post("/studies/", response_model=schemas.StudyFull)
def create_study(
    study_metadata: schemas.StudyMetadataCreate,
    study_content: schemas.StudyContentCreate,
    create_bids: bool = Query(True),
    status: Optional[str] = Query(None),
    draft_of_study_id: Optional[int] = Query(None),
    last_completed_step: Optional[int] = Query(None),
    audit_label: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    if study_metadata.created_by != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to create study for this user")

    desired_status = _norm_status(status) or "PUBLISHED"

    meta = models.StudyMetadata(
        created_by=study_metadata.created_by,
        study_name=study_metadata.study_name,
        study_description=study_metadata.study_description,
        status=desired_status,
        draft_of_study_id=draft_of_study_id,
        last_completed_step=last_completed_step,
        is_locked=False,
        locked_by=None,
        locked_at=None,
    )
    db.add(meta)
    db.commit()
    db.refresh(meta)

    content_row = models.StudyContent(
        study_id=meta.id,
        study_data=_deepcopy_json(study_content.study_data or {}),
    )
    db.add(content_row)
    db.commit()
    db.refresh(content_row)

    tv = _ensure_initial_version_if_missing(db, meta.id, content_row.study_data or {})

    datalad_refs = None
    if desired_status == "PUBLISHED":
        datalad_refs = _write_published_snapshot_to_datalad(
            meta=meta,
            study_data=content_row.study_data or {},
            template_version=tv.version,
            template_schema=tv.schema or {},
            actor=_actor_identifier(user),
            actor_name=_display_name(user),
            user_id=user.id,
            audit_label=audit_label,
        )
        try:
            dataset_path = Path(str(datalad_refs["dataset_path"]))
            metadata = {"study_name": meta.study_name}
            dataset_id = repo.dataset_id(dataset_path)
            if dataset_id:
                metadata["dataset_id"] = dataset_id
            record_study_activity(
                db,
                study_id=meta.id,
                dataset_path=dataset_path,
                user_id=user.id,
                session_jti=_session_jti_from_authorization(authorization),
                purpose="create_study",
                metadata=metadata,
            )
        except Exception:
            db.rollback()
            logger.exception("Failed to record study activity for study_id=%s", meta.id)

    meta_out = schemas.StudyMetadataOut.model_validate(meta).model_dump()
    meta_out["permissions"] = {"view": True, "add_data": True, "edit_study": True}
    return {
        "metadata": meta_out,
        "content": {
            "id": content_row.id,
            "study_id": content_row.study_id,
            "study_data": content_row.study_data or {},
        },
    }


@router.get("/studies", response_model=List[schemas.StudyMetadataOut])
def list_studies(
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    status_norm = _norm_status(status)
    q = db.query(models.StudyMetadata)

    if not _is_admin(current_user):
        q = q.filter(
            (models.StudyMetadata.created_by == current_user.id)
            | (models.StudyMetadata.id.in_(
                db.query(models.StudyAccessGrant.study_id).filter(models.StudyAccessGrant.user_id == current_user.id)
            ))
        )

    if status_norm:
        q = q.filter(models.StudyMetadata.status == status_norm)

    rows = q.order_by(models.StudyMetadata.updated_at.desc()).all()
    out = []
    for m in rows:
        item = schemas.StudyMetadataOut.model_validate(m).model_dump()
        item["permissions"] = _effective_study_permissions(db, m, current_user)
        out.append(item)
    return out


@router.get("/studies/{study_id}", response_model=schemas.StudyFull)
def read_study(
    study_id: int,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    meta = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == study_id).first()
    if not meta:
        raise HTTPException(status_code=404, detail="Study not found")

    perms = _assert_has_study_permission(db, meta, user, required="view")
    try:
        dataset_path = _ensure_local_study_dataset(db, meta)
        repo.get_study_content(study_id, meta.study_name)
        _record_authenticated_activity(
            db,
            meta=meta,
            dataset_path=dataset_path,
            user=user,
            authorization=authorization,
            purpose="view_study",
        )
    except Exception as e:
        _raise_storage_unavailable(e, context="read_study")

    content_row = _get_content_row_or_404(db, study_id)

    meta_out = schemas.StudyMetadataOut.model_validate(meta).model_dump()
    meta_out["permissions"] = perms

    return {
        "metadata": meta_out,
        "content": {
            "id": content_row.id,
            "study_id": content_row.study_id,
            "study_data": content_row.study_data or {},
        },
    }


@router.get("/studies/{study_id}/lock-status")
def get_study_lock_status(
    study_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    meta = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == study_id).first()
    if not meta:
        raise HTTPException(status_code=404, detail="Study not found")

    _assert_has_study_permission(db, meta, user, required="view")
    # Locking disabled for now: always report unlocked.
    return {
        "study_id": meta.id,
        "is_locked": False,
        "locked_by": None,
        "locked_at": None,
    }

@router.post("/studies/{study_id}/lock")
def lock_study_for_edit(
    study_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    meta = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == study_id).first()
    if not meta:
        raise HTTPException(status_code=404, detail="Study not found")

    _assert_has_study_permission(db, meta, user, required="edit_study")

    # Locking disabled for now.
    # Do not write any lock state to the DB.
    return {
        "study_id": meta.id,
        "is_locked": False,
        "locked_by": None,
        "locked_at": None,
    }

@router.post("/studies/{study_id}/unlock")
def unlock_study_for_edit(
    study_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    meta = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == study_id).first()
    if not meta:
        raise HTTPException(status_code=404, detail="Study not found")

    _assert_has_study_permission(db, meta, user, required="edit_study")

    # Locking disabled for now.
    # Best-effort cleanup of any stale legacy lock values.
    meta.is_locked = False
    meta.locked_by = None
    meta.locked_at = None
    db.commit()
    db.refresh(meta)

    return {
        "study_id": meta.id,
        "is_locked": False,
        "locked_by": None,
        "locked_at": None,
    }


@router.get("/studies/{study_id}/versions")
def list_study_versions(
    study_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    meta = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == study_id).first()
    if not meta:
        raise HTTPException(status_code=404, detail="Study not found")

    _assert_has_study_permission(db, meta, user, required="view")

    rows = (
        db.query(models.StudyTemplateVersion)
        .filter(models.StudyTemplateVersion.study_id == study_id)
        .order_by(models.StudyTemplateVersion.version.asc())
        .all()
    )
    return [{"version": r.version, "created_at": r.created_at} for r in rows]


@router.get("/studies/{study_id}/template")
def get_template_version(
    study_id: int,
    version: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    meta = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == study_id).first()
    if not meta:
        raise HTTPException(status_code=404, detail="Study not found")

    _assert_has_study_permission(db, meta, user, required="view")

    q = db.query(models.StudyTemplateVersion).filter(models.StudyTemplateVersion.study_id == study_id)
    if version is not None:
        row = q.filter(models.StudyTemplateVersion.version == version).first()
    else:
        row = q.order_by(models.StudyTemplateVersion.version.desc()).first()

    if not row:
        raise HTTPException(status_code=404, detail="Template version not found")

    return {
        "study_id": study_id,
        "version": row.version,
        "schema": row.schema,
        "created_at": row.created_at,
    }


@router.get("/studies/{study_id}/slot-data", response_model=schemas.StudyDataSlotStateOut)
def get_slot_data(
    study_id: int,
    subject_index: int = Query(...),
    visit_index: int = Query(...),
    group_index: int = Query(...),
    version: Optional[int] = Query(None),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    meta = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == study_id).first()
    if not meta:
        raise HTTPException(status_code=404, detail="Study not found")

    _assert_has_study_permission(db, meta, user, required="view")

    if (meta.status or "PUBLISHED").upper().strip() != "PUBLISHED":
        raise HTTPException(status_code=400, detail="Data entry is only available for published studies")

    try:
        dataset_path = _ensure_local_study_dataset(db, meta)
        _record_authenticated_activity(
            db,
            meta=meta,
            dataset_path=dataset_path,
            user=user,
            authorization=authorization,
            purpose="slot_data_view",
        )
    except Exception as e:
        _raise_storage_unavailable(e, context="get_slot_data")

    if version is None:
        latest_tv = _latest_template_or_500(db, study_id)
        form_version = int(latest_tv.version)
    else:
        try:
            form_version = int(version)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid version")

        row = (
            db.query(models.StudyTemplateVersion)
            .filter(
                models.StudyTemplateVersion.study_id == study_id,
                models.StudyTemplateVersion.version == form_version,
            )
            .first()
        )
        if not row:
            raise HTTPException(status_code=404, detail=f"Template version {form_version} not found")

    slot_state = repo.get_current_slot_state(
        study_id=study_id,
        study_name=meta.study_name,
        subject_index=subject_index,
        visit_index=visit_index,
        group_index=group_index,
        form_version=form_version,
    )

    return slot_state


@router.put("/studies/{study_id}", response_model=schemas.StudyFull)
def update_study(
    study_id: int,
    study_metadata: schemas.StudyMetadataUpdate = Body(..., embed=True),
    study_content: schemas.StudyContentUpdate = Body(..., embed=True),
    audit_label: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    meta = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == study_id).first()
    if not meta:
        raise HTTPException(status_code=404, detail="Study not found")

    _assert_has_study_permission(db, meta, user, required="edit_study")

    # Locking disabled for now.
    # _require_lock_holder(meta, user)

    content_row = _get_content_row_or_404(db, study_id)
    old_sd = _deepcopy_json(content_row.study_data or {})
    new_sd = _deepcopy_json(study_content.study_data or {})

    incoming_status = _norm_status(getattr(study_metadata, "status", None)) or (meta.status or "PUBLISHED")
    old_study_name = meta.study_name
    old_status = (meta.status or "DRAFT").upper().strip()
    prepared_dataset_path: Optional[Path] = None

    if incoming_status == "PUBLISHED":
        try:
            prepared_dataset_path = _ensure_local_study_dataset_for_write(
                db,
                meta,
                allow_create_if_missing=old_status != "PUBLISHED",
            )
        except Exception as e:
            _raise_storage_unavailable(e, context="update_study")

    if getattr(study_metadata, "study_name", None) is not None:
        meta.study_name = study_metadata.study_name
    if getattr(study_metadata, "study_description", None) is not None:
        meta.study_description = study_metadata.study_description
    if hasattr(study_metadata, "last_completed_step") and getattr(study_metadata, "last_completed_step", None) is not None:
        meta.last_completed_step = study_metadata.last_completed_step
    meta.status = incoming_status

    content_row.study_data = new_sd
    db.commit()
    db.refresh(meta)
    db.refresh(content_row)

    VersionManager.ensure_initial_version(db, study_id, old_sd)

    VersionManager.apply_on_update(
        db=db,
        study_id=study_id,
        old_sd=old_sd,
        new_sd=new_sd,
        audit_callback=None,
    )

    latest_tv = _latest_template_or_500(db, study_id)

    if incoming_status == "PUBLISHED":
        prepared_dataset_path = _move_prepared_dataset_if_study_was_renamed(
            study_id=study_id,
            old_study_name=old_study_name,
            new_study_name=meta.study_name,
            prepared_path=prepared_dataset_path,
        )
        datalad_refs = _write_published_snapshot_to_datalad(
            meta=meta,
            study_data=content_row.study_data or {},
            template_version=latest_tv.version,
            template_schema=latest_tv.schema or {},
            actor=_actor_identifier(user),
            actor_name=_display_name(user),
            user_id=user.id,
            audit_label=audit_label,
        )
        dataset_path = Path(str(datalad_refs["dataset_path"]))
        _record_authenticated_activity(
            db,
            meta=meta,
            dataset_path=dataset_path,
            user=user,
            authorization=authorization,
            purpose="update_study",
        )

    # Locking disabled for now.
    # Keep DB lock fields cleared in case of stale values from older runs.
    meta.is_locked = False
    meta.locked_by = None
    meta.locked_at = None
    db.commit()
    db.refresh(meta)

    meta_out = schemas.StudyMetadataOut.model_validate(meta).model_dump()
    meta_out["permissions"] = {"view": True, "add_data": True, "edit_study": True}
    return {
        "metadata": meta_out,
        "content": {
            "id": content_row.id,
            "study_id": content_row.study_id,
            "study_data": content_row.study_data or {},
        },
    }


@router.post("/studies/{study_id}/publish", response_model=schemas.StudyFull)
def publish_study(
    study_id: int,
    audit_label: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    meta = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == study_id).first()
    if not meta:
        raise HTTPException(status_code=404, detail="Study not found")

    _assert_has_study_permission(db, meta, user, required="edit_study")

    # Locking disabled for now.
    # _require_lock_holder(meta, user)

    content_row = _get_content_row_or_404(db, study_id)
    latest_tv = _ensure_initial_version_if_missing(db, study_id, content_row.study_data or {})
    old_status = (meta.status or "DRAFT").upper().strip()

    try:
        _ensure_local_study_dataset_for_write(
            db,
            meta,
            allow_create_if_missing=old_status != "PUBLISHED",
        )
    except Exception as e:
        _raise_storage_unavailable(e, context="publish_study")

    meta.status = "PUBLISHED"
    db.commit()
    db.refresh(meta)

    datalad_refs = _write_published_snapshot_to_datalad(
        meta=meta,
        study_data=content_row.study_data or {},
        template_version=latest_tv.version,
        template_schema=latest_tv.schema or {},
        actor=_actor_identifier(user),
        actor_name=_display_name(user),
        user_id=user.id,
        audit_label=audit_label,
    )
    dataset_path = Path(str(datalad_refs["dataset_path"]))
    _record_authenticated_activity(
        db,
        meta=meta,
        dataset_path=dataset_path,
        user=user,
        authorization=authorization,
        purpose="publish_study",
    )

    # Locking disabled for now.
    # Keep DB lock fields cleared in case of stale values from older runs.
    meta.is_locked = False
    meta.locked_by = None
    meta.locked_at = None
    db.commit()
    db.refresh(meta)

    meta_out = schemas.StudyMetadataOut.model_validate(meta).model_dump()
    meta_out["permissions"] = {"view": True, "add_data": True, "edit_study": True}
    return {
        "metadata": meta_out,
        "content": {
            "id": content_row.id,
            "study_id": content_row.study_id,
            "study_data": content_row.study_data or {},
        },
    }

@router.get("/studies/{study_id}/files", response_model=List[schemas.FileOut])
def read_files_for_study(
    study_id: int,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    meta = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == study_id).first()
    if not meta:
        raise HTTPException(status_code=404, detail="Study not found")

    _assert_has_study_permission(db, meta, user, required="view")
    try:
        dataset_path = _ensure_local_study_dataset(db, meta)
        _record_authenticated_activity(
            db,
            meta=meta,
            dataset_path=dataset_path,
            user=user,
            authorization=authorization,
            purpose="list_files",
        )
    except Exception as e:
        _raise_storage_unavailable(e, context="read_files_for_study")
    return repo.list_files(study_id, meta.study_name)

@router.get("/studies/{study_id}/download")
def download_full_study(
    study_id: int,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    meta = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == study_id).first()
    if not meta:
        raise HTTPException(status_code=404, detail="Study not found")
    # Only owner or admin can download study
    _assert_owner_or_admin(meta, user)

    try:
        dataset_path = _ensure_local_study_dataset(db, meta)
        _record_authenticated_activity(
            db,
            meta=meta,
            dataset_path=dataset_path,
            user=user,
            authorization=authorization,
            purpose="download_study",
        )
        zip_path, zip_name = repo.build_full_study_zip(
            study_id=study_id,
            study_name=meta.study_name,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to build study zip: {str(e)}")

    return FileResponse(
        path=str(zip_path),
        filename=zip_name,
        media_type="application/zip",
    )

@router.post("/studies/{study_id}/files", response_model=schemas.FileOut)
def upload_file(
    study_id: int,
    uploaded_file: UploadFile = File(...),
    description: str = Form(""),
    subject_index: Optional[int] = Form(None),
    visit_index: Optional[int] = Form(None),
    group_index: Optional[int] = Form(None),
    modalities_json: Optional[str] = Form("[]"),
    audit_label: Optional[str] = Form(None),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    meta = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == study_id).first()
    if not meta:
        raise HTTPException(status_code=404, detail="Study not found")

    _assert_has_study_permission(db, meta, user, required="add_data")
    _assert_not_locked_by_other(meta, user)
    try:
        dataset_path = _ensure_local_study_dataset(db, meta)
        _record_authenticated_activity(
            db,
            meta=meta,
            dataset_path=dataset_path,
            user=user,
            authorization=authorization,
            purpose="upload_file",
        )
    except Exception as e:
        _raise_storage_unavailable(e, context="upload_file_for_study")

    modalities = _parse_modalities_json(modalities_json)
    latest_tv = _latest_template_or_500(db, study_id)
    form_version = int(latest_tv.version)

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            delete=False,
            prefix=f"ecrf_study{study_id}_",
            suffix=f"_{uploaded_file.filename}",
        ) as tmp:
            shutil.copyfileobj(uploaded_file.file, tmp)
            tmp_path = tmp.name

        return repo.save_uploaded_file(
            study_id=study_id,
            study_name=meta.study_name,
            filename=uploaded_file.filename,
            source_path=tmp_path,
            description=description,
            subject_index=subject_index,
            visit_index=visit_index,
            group_index=group_index,
            modalities=modalities,
            form_version=form_version,
            actor=_actor_identifier(user),
            actor_name=_display_name(user),
            user_id=user.id,
            audit_label=audit_label,
        )
    finally:
        try:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass


@router.post("/studies/{study_id}/files/url", response_model=schemas.FileOut)
def create_url_file(
    study_id: int,
    url: str = Form(...),
    description: str = Form(""),
    subject_index: Optional[int] = Form(None),
    visit_index: Optional[int] = Form(None),
    group_index: Optional[int] = Form(None),
    modalities_json: Optional[str] = Form("[]"),
    audit_label: Optional[str] = Form(None),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    meta = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == study_id).first()
    if not meta:
        raise HTTPException(status_code=404, detail="Study not found")

    _assert_has_study_permission(db, meta, user, required="add_data")
    _assert_not_locked_by_other(meta, user)
    try:
        dataset_path = _ensure_local_study_dataset(db, meta)
        _record_authenticated_activity(
            db,
            meta=meta,
            dataset_path=dataset_path,
            user=user,
            authorization=authorization,
            purpose="create_url_file",
        )
    except Exception as e:
        _raise_storage_unavailable(e, context="add_url_file_for_study")

    modalities = _parse_modalities_json(modalities_json)
    latest_tv = _latest_template_or_500(db, study_id)
    form_version = int(latest_tv.version)

    return repo.save_url_file(
        study_id=study_id,
        study_name=meta.study_name,
        url=url,
        description=description,
        subject_index=subject_index,
        visit_index=visit_index,
        group_index=group_index,
        modalities=modalities,
        form_version=form_version,
        actor=_actor_identifier(user),
        actor_name=_display_name(user),
        user_id=user.id,
        audit_label=audit_label,
    )

@router.post("/shared/{token}/files", response_model=schemas.FileOut)
def shared_upload_file(
    token: str,
    uploaded_file: UploadFile = File(...),
    description: str = Form(""),
    modalities_json: Optional[str] = Form("[]"),
    audit_label: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    access = db.query(models.SharedFormAccess).filter_by(token=token).first()
    if not access:
        raise HTTPException(status_code=404, detail="Link not found")

    if access.expires_at < datetime.utcnow():
        raise HTTPException(status_code=403, detail="Link expired")

    if access.permission != "add":
        raise HTTPException(status_code=403, detail="Not allowed")

    meta = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == access.study_id).first()
    if not meta:
        raise HTTPException(status_code=404, detail="Study not found")

    # Locking disabled for now.
    # if bool(meta.is_locked):
    #     raise HTTPException(status_code=423, detail="Study is currently locked for editing")

    if (meta.status or "PUBLISHED").upper().strip() != "PUBLISHED":
        raise HTTPException(status_code=400, detail="Shared file upload is only allowed for published studies")

    cleanup_stale_shared_views(db)
    try:
        dataset_path = _ensure_local_study_dataset(db, meta)
    except Exception as e:
        _raise_storage_unavailable(e, context="shared_upload_file")

    submit_jti = f"shared-submit:{token}:{secrets.token_urlsafe(12)}"
    _record_shared_activity(
        db,
        meta=meta,
        dataset_path=dataset_path,
        token=token,
        session_jti=submit_jti,
        purpose="shared_link_file_upload",
    )
    expire_shared_view_for_token(db, token=token)

    modalities = _parse_modalities_json(modalities_json)
    latest_tv = _latest_template_or_500(db, access.study_id)
    form_version = int(latest_tv.version)

    tmp_path = None
    try:
        safe_suffix = f"_{os.path.basename(uploaded_file.filename or 'upload.bin')}"
        with tempfile.NamedTemporaryFile(
            delete=False,
            prefix=f"ecrf_shared_study{access.study_id}_",
            suffix=safe_suffix,
        ) as tmp:
            shutil.copyfileobj(uploaded_file.file, tmp)
            tmp_path = tmp.name

        return repo.save_uploaded_file(
            study_id=access.study_id,
            study_name=meta.study_name,
            filename=uploaded_file.filename or "upload.bin",
            source_path=tmp_path,
            description=description,
            subject_index=access.subject_index,
            visit_index=access.visit_index,
            group_index=access.group_index,
            modalities=modalities,
            form_version=form_version,
            actor="shared-link",
            actor_name="Shared link upload",
            user_id=None,
            audit_label=audit_label,
        )
    except Exception as e:
        _raise_storage_unavailable(e, context="shared_upload_file")
    finally:
        try:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass
        release_activity_by_session(
            db,
            session_jti=submit_jti,
            reason="shared_link_file_upload_complete",
            sync_after_release=True,
        )

@router.get("/studies/{study_id}/files/{file_id}/download")
def download_study_file(
    study_id: int,
    file_id: int,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    meta = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == study_id).first()
    if not meta:
        raise HTTPException(status_code=404, detail="Study not found")

    _assert_can_download_study_file(db, meta, user)

    try:
        dataset_path = _ensure_local_study_dataset(db, meta)
        _record_authenticated_activity(
            db,
            meta=meta,
            dataset_path=dataset_path,
            user=user,
            authorization=authorization,
            purpose="download_file",
        )
        file_info = repo.get_file_for_download(
            study_id=study_id,
            study_name=meta.study_name,
            file_id=file_id,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if file_info["storage_option"] == "url":
        # optional behavior: for URL-based files, redirect instead of file download
        return RedirectResponse(url=file_info["url"])

    return FileResponse(
        path=str(file_info["absolute_path"]),
        filename=file_info["file_name"],
        media_type="application/octet-stream",
    )

@router.post(
    "/studies/{study_id}/data",
    response_model=schemas.StudyDataEntryOut,
    responses={
        409: {
            "description": "Slot data changed after the form was opened",
            "model": schemas.StudyDataConflictDetail,
        }
    },
)
def save_study_data(
    study_id: int,
    payload: schemas.StudyDataEntryCreate = Body(...),
    version: Optional[int] = Query(None),
    expected_revision_token: str = Query(...),
    audit_label: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    meta = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == study_id).first()
    if not meta:
        raise HTTPException(status_code=404, detail="Study not found")

    _assert_has_study_permission(db, meta, current_user, required="add_data")
    _assert_not_locked_by_other(meta, current_user)
    try:
        dataset_path = _ensure_local_study_dataset(db, meta)
        _record_authenticated_activity(
            db,
            meta=meta,
            dataset_path=dataset_path,
            user=current_user,
            authorization=authorization,
            purpose="add_data",
        )
    except Exception as e:
        _raise_storage_unavailable(e, context="create_study_data_entry")

    if (meta.status or "PUBLISHED").upper().strip() != "PUBLISHED":
        raise HTTPException(status_code=400, detail="Data entry is only allowed for published studies")

    form_version = _resolve_form_version_or_400(db, study_id, version)

    try:
        repo.assert_slot_revision_unchanged(
            study_id=study_id,
            study_name=meta.study_name,
            subject_index=payload.subject_index,
            visit_index=payload.visit_index,
            group_index=payload.group_index,
            form_version=form_version,
            expected_revision_token=expected_revision_token,
        )
    except ValueError:
        latest_slot_state = repo.get_current_slot_state(
            study_id=study_id,
            study_name=meta.study_name,
            subject_index=payload.subject_index,
            visit_index=payload.visit_index,
            group_index=payload.group_index,
            form_version=form_version,
        )
        raise HTTPException(
            status_code=409,
            detail={
                "message": "This data was changed by another user after you opened it. Latest backend values are now different. Please reload/review and save again.",
                "conflict": True,
                "latest": latest_slot_state,
            },
        )

    content_row = _get_content_row_or_404(db, study_id)
    selected_models = ((content_row.study_data or {}).get("selectedModels") or [])
    progress_values = _entry_progress_values(payload)

    return repo.save_entry(
        study_id=study_id,
        study_name=meta.study_name,
        subject_index=payload.subject_index,
        visit_index=payload.visit_index,
        group_index=payload.group_index,
        form_version=form_version,
        data=payload.data,
        skipped_required_flags=_flags_dict_to_list(payload.skipped_required_flags, selected_models),
        actor=_actor_identifier(current_user),
        actor_name=_display_name(current_user),
        user_id=current_user.id,
        audit_label=audit_label,
        **progress_values,
    )


@router.put("/studies/{study_id}/data_entries/{entry_id}", response_model=schemas.StudyDataEntryOut)
def update_study_data_entry(
    study_id: int,
    entry_id: int,
    payload: schemas.StudyDataEntryCreate = Body(...),
    expected_revision_token: str = Query(...),
    audit_label: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    meta = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == study_id).first()
    if not meta:
        raise HTTPException(status_code=404, detail="Study not found")

    _assert_has_study_permission(db, meta, user, required="add_data")
    _assert_not_locked_by_other(meta, user)

    if (meta.status or "PUBLISHED").upper().strip() != "PUBLISHED":
        raise HTTPException(status_code=400, detail="Data entry is only allowed for published studies")

    try:
        dataset_path = _ensure_local_study_dataset(db, meta)
        _record_authenticated_activity(
            db,
            meta=meta,
            dataset_path=dataset_path,
            user=user,
            authorization=authorization,
            purpose="update_data_entry",
        )
    except Exception as e:
        _raise_storage_unavailable(e, context="update_study_data_entry")

    target_entry = None
    for e in repo.list_entries(study_id, meta.study_name):
        try:
            if int(e.get("id")) == int(entry_id):
                target_entry = e
                break
        except Exception:
            continue

    if not target_entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    form_version = int(target_entry.get("form_version") or 1)

    try:
        repo.assert_slot_revision_unchanged(
            study_id=study_id,
            study_name=meta.study_name,
            subject_index=payload.subject_index,
            visit_index=payload.visit_index,
            group_index=payload.group_index,
            form_version=form_version,
            expected_revision_token=expected_revision_token,
        )
    except ValueError:
        latest_slot_state = repo.get_current_slot_state(
            study_id=study_id,
            study_name=meta.study_name,
            subject_index=payload.subject_index,
            visit_index=payload.visit_index,
            group_index=payload.group_index,
            form_version=form_version,
        )
        raise HTTPException(
            status_code=409,
            detail={
                "message": "This data was changed by another user after you opened it. Latest backend values are now different. Please reload/review and save again.",
                "conflict": True,
                "latest": latest_slot_state,
            },
        )

    content_row = _get_content_row_or_404(db, study_id)
    selected_models = ((content_row.study_data or {}).get("selectedModels") or [])
    progress_values = _entry_progress_values(payload)

    return repo.update_entry(
        study_id=study_id,
        study_name=meta.study_name,
        entry_id=entry_id,
        payload={
            "subject_index": payload.subject_index,
            "visit_index": payload.visit_index,
            "group_index": payload.group_index,
            "data": payload.data,
            "skipped_required_flags": _flags_dict_to_list(payload.skipped_required_flags, selected_models),
            **progress_values,
        },
        actor=_actor_identifier(user),
        actor_name=_display_name(user),
        user_id=user.id,
        audit_label=audit_label,
    )


@router.get("/studies/{study_id}/data_entry_statuses", response_model=schemas.StudyDataEntryStatusListOut)
def list_study_data_entry_statuses(
    study_id: int,
    subject_indexes: Optional[str] = Query(None),
    visit_indexes: Optional[str] = Query(None),
    version: Optional[int] = Query(None),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    meta = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == study_id).first()
    if not meta:
        raise HTTPException(status_code=404, detail="Study not found")

    _assert_has_study_permission(db, meta, user, required="view")
    try:
        dataset_path = _ensure_local_study_dataset(db, meta)
        _record_authenticated_activity(
            db,
            meta=meta,
            dataset_path=dataset_path,
            user=user,
            authorization=authorization,
            purpose="list_data_entry_statuses",
        )
    except Exception as e:
        _raise_storage_unavailable(e, context="list_study_data_entry_statuses")

    entries = repo.list_entries(study_id, meta.study_name)
    if version is not None:
        target_version = int(version)
        entries = [e for e in entries if int(e.get("form_version") or 0) <= target_version]

    if subject_indexes:
        subj_idx_list = [int(s) for s in subject_indexes.split(",") if s.strip().isdigit()]
        if subj_idx_list:
            entries = [e for e in entries if int(e.get("subject_index", -1)) in subj_idx_list]

    if visit_indexes:
        visit_idx_list = [int(s) for s in visit_indexes.split(",") if s.strip().isdigit()]
        if visit_idx_list:
            entries = [e for e in entries if int(e.get("visit_index", -1)) in visit_idx_list]

    latest_by_slot: Dict[tuple, Dict[str, Any]] = {}
    for entry in entries:
        key = (
            int(entry.get("subject_index") or 0),
            int(entry.get("visit_index") or 0),
            int(entry.get("group_index") or 0),
        )
        current = latest_by_slot.get(key)
        if current is None:
            latest_by_slot[key] = entry
            continue
        entry_rank = (int(entry.get("form_version") or 0), int(entry.get("id") or 0))
        current_rank = (int(current.get("form_version") or 0), int(current.get("id") or 0))
        if entry_rank > current_rank:
            latest_by_slot[key] = entry

    statuses = []
    needs_backfill = False
    for entry in latest_by_slot.values():
        row_needs_backfill = entry.get("progress_status") is None or entry.get("progress_percentage") is None
        needs_backfill = needs_backfill or row_needs_backfill
        statuses.append({
            "id": int(entry.get("id") or 0),
            "study_id": int(entry.get("study_id") or study_id),
            "form_version": int(entry.get("form_version") or 1),
            "subject_index": int(entry.get("subject_index") or 0),
            "visit_index": int(entry.get("visit_index") or 0),
            "group_index": int(entry.get("group_index") or 0),
            "progress_status": entry.get("progress_status"),
            "progress_percentage": entry.get("progress_percentage"),
            "progress_completed": entry.get("progress_completed"),
            "progress_total": entry.get("progress_total"),
            "progress_skipped": entry.get("progress_skipped"),
            "needs_progress_backfill": row_needs_backfill,
        })

    return {
        "total": len(statuses),
        "statuses": statuses,
        "needs_progress_backfill": needs_backfill,
    }


@router.get("/studies/{study_id}/data_entries", response_model=schemas.PaginatedStudyDataEntries)
def list_study_data_entries(
    study_id: int,
    subject_indexes: Optional[str] = Query(None),
    visit_indexes: Optional[str] = Query(None),
    all: bool = Query(False),
    current_only: bool = Query(False),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    meta = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == study_id).first()
    if not meta:
        raise HTTPException(status_code=404, detail="Study not found")

    _assert_has_study_permission(db, meta, user, required="view")
    try:
        dataset_path = _ensure_local_study_dataset(db, meta)
        _record_authenticated_activity(
            db,
            meta=meta,
            dataset_path=dataset_path,
            user=user,
            authorization=authorization,
            purpose="list_data_entries",
        )
    except Exception as e:
        _raise_storage_unavailable(e, context="list_study_data_entries")

    entries = repo.list_latest_entries_by_slot(study_id, meta.study_name) if current_only else repo.list_entries(study_id, meta.study_name)

    if not all:
        if subject_indexes:
            subj_idx_list = [int(s) for s in subject_indexes.split(",") if s.strip().isdigit()]
            if subj_idx_list:
                entries = [e for e in entries if int(e.get("subject_index", -1)) in subj_idx_list]

        if visit_indexes:
            visit_idx_list = [int(s) for s in visit_indexes.split(",") if s.strip().isdigit()]
            if visit_idx_list:
                entries = [e for e in entries if int(e.get("visit_index", -1)) in visit_idx_list]

    return {"total": len(entries), "entries": entries}


@router.post("/studies/{study_id}/access", response_model=schemas.StudyAccessGrantOut, status_code=201)
def grant_study_access(
    study_id: int,
    payload: schemas.StudyAccessGrantCreate = Body(...),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    meta = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == study_id).first()
    if not meta:
        raise HTTPException(status_code=404, detail="Study not found")

    _assert_owner_or_admin(meta, user)
    _assert_not_locked_by_other(meta, user)
    try:
        dataset_path = _ensure_local_study_dataset(db, meta)
        _record_authenticated_activity(
            db,
            meta=meta,
            dataset_path=dataset_path,
            user=user,
            authorization=authorization,
            purpose="grant_study_access",
        )
    except Exception as e:
        _raise_storage_unavailable(e, context="grant_study_access")

    if payload.user_id == meta.created_by:
        raise HTTPException(status_code=400, detail="Owner already has full access")

    grantee = db.query(models.User).filter(models.User.id == payload.user_id).first()
    if not grantee:
        raise HTTPException(status_code=404, detail="User not found")

    perms = payload.permissions or {"view": True, "add_data": True, "edit_study": False}

    grant = db.query(models.StudyAccessGrant).filter_by(study_id=study_id, user_id=payload.user_id).first()
    if grant:
        grant.permissions = perms
    else:
        grant = models.StudyAccessGrant(
            study_id=study_id,
            user_id=payload.user_id,
            permissions=perms,
            created_by=user.id,
        )
        db.add(grant)

    db.commit()
    db.refresh(grant)
    repo.save_access_grant(
        study_id=study_id,
        study_name=meta.study_name,
        user_id=payload.user_id,
        permissions=grant.permissions or {"view": True, "add_data": True, "edit_study": False},
        created_by=user.id,
        actor=_actor_identifier(user),
        actor_name=_display_name(user),
    )

    return schemas.StudyAccessGrantOut(
        user_id=grantee.id,
        role=getattr(getattr(grantee, "profile", None), "role", None),
        email=grantee.email,
        username=grantee.username,
        display_name=_display_name(grantee),
        created_by=grant.created_by,
        created_by_display=_display_name(grant.granted_by) if grant.granted_by else None,
        created_at=grant.created_at,
        permissions=grant.permissions,
    )


@router.get("/studies/{study_id}/access", response_model=List[schemas.StudyAccessGrantOut])
def list_study_access(
    study_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    meta = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == study_id).first()
    if not meta:
        raise HTTPException(status_code=404, detail="Study not found")

    _assert_owner_or_admin(meta, current_user)

    grants = db.query(models.StudyAccessGrant).filter(models.StudyAccessGrant.study_id == study_id).all()
    out: List[schemas.StudyAccessGrantOut] = []
    for g in grants:
        grantee = g.user
        granter = g.granted_by
        out.append(
            schemas.StudyAccessGrantOut(
                user_id=grantee.id,
                role=getattr(getattr(grantee, "profile", None), "role", None),
                email=grantee.email,
                username=grantee.username,
                display_name=_display_name(grantee),
                created_by=g.created_by,
                created_by_display=_display_name(granter) if granter else None,
                created_at=g.created_at,
                permissions=g.permissions or {"view": True, "add_data": True, "edit_study": False},
            )
        )
    return out


@router.delete("/studies/{study_id}/access/{user_id}", status_code=204)
def revoke_study_access(
    study_id: int,
    user_id: int,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    meta = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == study_id).first()
    if not meta:
        raise HTTPException(status_code=404, detail="Study not found")

    _assert_owner_or_admin(meta, current_user)
    _assert_not_locked_by_other(meta, current_user)
    try:
        dataset_path = _ensure_local_study_dataset(db, meta)
        _record_authenticated_activity(
            db,
            meta=meta,
            dataset_path=dataset_path,
            user=current_user,
            authorization=authorization,
            purpose="revoke_study_access",
        )
    except Exception as e:
        _raise_storage_unavailable(e, context="revoke_study_access")

    if user_id == meta.created_by:
        raise HTTPException(status_code=400, detail="Cannot revoke owner access")

    grant = db.query(models.StudyAccessGrant).filter_by(study_id=study_id, user_id=user_id).first()
    if not grant:
        return

    db.delete(grant)
    db.commit()
    repo.revoke_access_grant(
        study_id=study_id,
        study_name=meta.study_name,
        user_id=user_id,
        actor=_actor_identifier(current_user),
        actor_name=_display_name(current_user),
        acting_user_id=current_user.id,
    )
    return

def _section_title_lookup(study_data: Dict[str, Any]) -> Dict[str, str]:
    out: Dict[str, str] = {}

    for idx, sec in enumerate((study_data or {}).get("selectedModels") or []):
        if not isinstance(sec, dict):
            continue

        sec_id = str(sec.get("_id") or sec.get("id") or sec.get("uuid") or "").strip()
        title = str(sec.get("title") or f"Section {idx + 1}").strip()

        if sec_id:
            out[sec_id] = title

    return out


def _shared_link_status(access: models.SharedFormAccess) -> str:
    now = datetime.utcnow()

    if access.expires_at and access.expires_at < now:
        return "Expired"

    if int(access.used_count or 0) >= int(access.max_uses or 0):
        return "Usage limit reached"

    return "Active"


def _frontend_base_from_request(request: Request) -> str:
    frontend_base = os.getenv("FRONTEND_BASE_URL", "").rstrip("/")
    if frontend_base:
        return frontend_base

    return f"{request.url.scheme}://{request.headers.get('host', request.url.netloc)}"


@router.get("/studies/{study_id}/share-links")
def list_share_links_for_study(
    study_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    meta = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == study_id).first()
    if not meta:
        raise HTTPException(status_code=404, detail="Study not found")

    _assert_has_study_permission(db, meta, current_user, required="add_data")

    content_row = _get_content_row_or_404(db, study_id)
    study_data = content_row.study_data or {}

    subjects = study_data.get("subjects") or []
    visits = study_data.get("visits") or []
    section_titles = _section_title_lookup(study_data)

    base = _frontend_base_from_request(request)

    rows = (
        db.query(models.SharedFormAccess)
        .filter(models.SharedFormAccess.study_id == study_id)
        .order_by(models.SharedFormAccess.created_at.desc())
        .all()
    )

    out = []

    for access in rows:
        subject = subjects[access.subject_index] if 0 <= int(access.subject_index) < len(subjects) else {}
        visit = visits[access.visit_index] if 0 <= int(access.visit_index) < len(visits) else {}

        allowed_section_ids = access.allowed_section_ids or []
        used_count = int(access.used_count or 0)
        max_uses = int(access.max_uses or 0)

        out.append({
            "token": access.token,
            "study_id": access.study_id,
            "study_name": meta.study_name,
            "subject_index": access.subject_index,
            "subject_id": subject.get("id") or subject.get("subject_id") or f"Subject {access.subject_index + 1}",
            "group_index": access.group_index,
            "group": subject.get("group") or "",
            "visit_index": access.visit_index,
            "visit_name": visit.get("name") or f"Visit {access.visit_index + 1}",
            "permission": access.permission,
            "max_uses": max_uses,
            "used_count": used_count,
            "remaining_uses": max(0, max_uses - used_count),
            "expires_at": access.expires_at.isoformat() if access.expires_at else None,
            "created_at": access.created_at.isoformat() if getattr(access, "created_at", None) else None,
            "allowed_section_ids": allowed_section_ids,
            "section_titles": [section_titles.get(sec_id, sec_id) for sec_id in allowed_section_ids],
            "status": _shared_link_status(access),
            "link": f"{base}/shared/{access.token}",
        })

    return out


@router.post("/studies/{study_id}/share-links/{token}/revoke")
def revoke_share_link(
    study_id: int,
    token: str,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    meta = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == study_id).first()
    if not meta:
        raise HTTPException(status_code=404, detail="Study not found")

    _assert_owner_or_admin(meta, current_user)
    _assert_not_locked_by_other(meta, current_user)
    try:
        dataset_path = _ensure_local_study_dataset(db, meta)
        _record_authenticated_activity(
            db,
            meta=meta,
            dataset_path=dataset_path,
            user=current_user,
            authorization=authorization,
            purpose="revoke_share_link",
        )
    except Exception as e:
        _raise_storage_unavailable(e, context="list_share_links")

    access = (
        db.query(models.SharedFormAccess)
        .filter(
            models.SharedFormAccess.study_id == study_id,
            models.SharedFormAccess.token == token,
        )
        .first()
    )

    if not access:
        raise HTTPException(status_code=404, detail="Shared link not found")

    try:
        # No schema migration needed: invalidating by forcing usage limit reached.
        access.max_uses = int(access.used_count or 0)
        repo.update_share_link(
            study_id=study_id,
            study_name=meta.study_name,
            token=token,
            row={
                "token": access.token,
                "study_id": access.study_id,
                "subject_index": access.subject_index,
                "visit_index": access.visit_index,
                "group_index": access.group_index,
                "permission": access.permission,
                "max_uses": access.max_uses,
                "used_count": access.used_count,
                "expires_at": access.expires_at.isoformat() if access.expires_at else None,
                "allowed_section_ids": access.allowed_section_ids or [],
                "created_at": access.created_at.isoformat() if getattr(access, "created_at", None) else None,
                "status": "Invalidated",
                "revoked_by": _actor_identifier(current_user),
                "revoked_at": datetime.utcnow().isoformat(),
            },
        )
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to write revoked shared link to study dataset")

    db.commit()

    return {"ok": True}

@router.post("/share-link/", status_code=201)
def create_share_link(
    payload: schemas.ShareLinkCreate,
    request: Request,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    meta = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == payload.study_id).first()
    if not meta:
        raise HTTPException(status_code=404, detail="Study not found")

    _assert_has_study_permission(db, meta, current_user, required="add_data")
    _assert_not_locked_by_other(meta, current_user)
    try:
        dataset_path = _ensure_local_study_dataset(db, meta)
    except Exception as e:
        _raise_storage_unavailable(e, context="create_share_link")

    content_row = _get_content_row_or_404(db, payload.study_id)
    study_data = content_row.study_data or {}

    selected_models = study_data.get("selectedModels") or []
    assignments = study_data.get("assignments") or []

    requested_allowed_ids = _normalize_allowed_section_ids(getattr(payload, "allowed_section_ids", []) or [])

    assigned_section_ids = set()
    v_idx = int(payload.visit_index)
    g_idx = int(payload.group_index)

    for m_idx, sec in enumerate(selected_models):
        if not isinstance(sec, dict):
            continue
        assigned = False
        if (
            isinstance(assignments, list)
            and m_idx < len(assignments)
            and isinstance(assignments[m_idx], list)
            and v_idx < len(assignments[m_idx])
            and isinstance(assignments[m_idx][v_idx], list)
            and g_idx < len(assignments[m_idx][v_idx])
        ):
            assigned = bool(assignments[m_idx][v_idx][g_idx])

        if assigned:
            sec_id = str(sec.get("_id") or sec.get("id") or "").strip()
            if sec_id:
                assigned_section_ids.add(sec_id)

    allowed_section_ids = requested_allowed_ids or sorted(assigned_section_ids)
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(days=payload.expires_in_days)

    access = models.SharedFormAccess(
        token=token,
        study_id=payload.study_id,
        subject_index=payload.subject_index,
        visit_index=payload.visit_index,
        group_index=payload.group_index,
        permission=payload.permission,
        max_uses=payload.max_uses,
        expires_at=expires_at,
        allowed_section_ids=allowed_section_ids,
    )
    db.add(access)
    try:
        repo.save_share_link(
            study_id=payload.study_id,
            study_name=meta.study_name,
            token=token,
            subject_index=payload.subject_index,
            visit_index=payload.visit_index,
            group_index=payload.group_index,
            permission=payload.permission,
            max_uses=payload.max_uses,
            expires_at=expires_at.isoformat(),
            allowed_section_ids=allowed_section_ids,
            actor=_actor_identifier(current_user),
            actor_name=_display_name(current_user),
            user_id=current_user.id,
        )
        db.commit()
        db.refresh(access)
        _record_authenticated_activity(
            db,
            meta=meta,
            dataset_path=dataset_path,
            user=current_user,
            authorization=authorization,
            purpose="create_share_link",
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create shared link in study dataset: {str(e)}")

    frontend_base = os.getenv("FRONTEND_BASE_URL", "").rstrip("/")
    if not frontend_base:
        frontend_base = f"{request.url.scheme}://{request.headers.get('host', request.url.netloc)}"

    return {"token": token, "link": f"{frontend_base}/shared/{token}"}


@router.get("/shared-api/{token}", response_model=schemas.SharedFormAccessOut)
def access_shared_form(
    token: str,
    db: Session = Depends(get_db),
):
    cleanup_stale_shared_views(db)

    access = db.query(models.SharedFormAccess).filter_by(token=token).first()
    if not access:
        raise HTTPException(404, "Link not found")
    if access.used_count >= access.max_uses:
        raise HTTPException(403, "Usage limit exceeded")
    if access.expires_at < datetime.utcnow():
        raise HTTPException(403, "Link expired")

    access.used_count += 1

    meta = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == access.study_id).first()
    if not meta:
        raise HTTPException(404, "Study not found")

    try:
        dataset_path = _ensure_local_study_dataset(db, meta)
        repo.update_share_link(
            study_id=access.study_id,
            study_name=meta.study_name,
            token=token,
            row={
                "token": access.token,
                "study_id": access.study_id,
                "subject_index": access.subject_index,
                "visit_index": access.visit_index,
                "group_index": access.group_index,
                "permission": access.permission,
                "max_uses": access.max_uses,
                "used_count": access.used_count,
                "expires_at": access.expires_at.isoformat() if access.expires_at else None,
                "allowed_section_ids": access.allowed_section_ids or [],
                "created_at": access.created_at.isoformat() if getattr(access, "created_at", None) else None,
            },
        )
        db.commit()
        _record_shared_activity(
            db,
            meta=meta,
            dataset_path=dataset_path,
            token=token,
            session_jti=f"shared-view:{token}",
            purpose="shared_link_view",
        )
    except Exception as e:
        db.rollback()
        _raise_storage_unavailable(e, context="access_shared_form")

    content_row = _get_content_row_or_404(db, access.study_id)
    filtered_study_data = _filter_shared_study_data_by_sections(
        content_row.study_data or {},
        access.allowed_section_ids,
    )

    return {
        "study_id": access.study_id,
        "subject_index": access.subject_index,
        "visit_index": access.visit_index,
        "group_index": access.group_index,
        "permission": access.permission,
        "allowed_section_ids": access.allowed_section_ids or [],
        "study": {
            "metadata": {
                "id": meta.id,
                "study_name": meta.study_name,
                "study_description": meta.study_description,
                "created_by": meta.created_by,
                "created_at": meta.created_at,
                "updated_at": meta.updated_at,
            },
            "content": {
                "study_data": filtered_study_data
            }
        }
    }


@router.post("/shared/{token}/data", response_model=schemas.StudyDataEntryOut)
def shared_upsert_data(
    token: str,
    payload: schemas.SharedStudyDataEntryCreate,
    version: Optional[int] = Query(None),
    audit_label: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    access = db.query(models.SharedFormAccess).filter_by(token=token).first()
    if not access:
        raise HTTPException(404, "Link not found")
    if access.expires_at < datetime.utcnow():
        raise HTTPException(403, "Link expired")
    if access.permission != "add":
        raise HTTPException(403, "Not allowed")

    meta = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == access.study_id).first()
    if not meta:
        raise HTTPException(404, "Study not found")
    # Locking disabled for now.
    # if bool(meta.is_locked):
    #     raise HTTPException(status_code=423, detail="Study is currently locked for editing")

    if (meta.status or "PUBLISHED").upper().strip() != "PUBLISHED":
        raise HTTPException(status_code=400, detail="Shared data entry is only allowed for published studies")

    cleanup_stale_shared_views(db)
    try:
        dataset_path = _ensure_local_study_dataset(db, meta)
    except Exception as e:
        _raise_storage_unavailable(e, context="shared_upsert_data")

    submit_jti = f"shared-submit:{token}:{secrets.token_urlsafe(12)}"
    _record_shared_activity(
        db,
        meta=meta,
        dataset_path=dataset_path,
        token=token,
        session_jti=submit_jti,
        purpose="shared_link_submit",
    )
    expire_shared_view_for_token(db, token=token)

    form_version = _resolve_form_version_or_400(db, access.study_id, version)

    content_row = _get_content_row_or_404(db, access.study_id)
    study_data = content_row.study_data or {}
    selected_models = study_data.get("selectedModels") or []

    _validate_shared_payload_sections(
        payload_data=payload.data or {},
        study_data=study_data,
        allowed_section_ids=access.allowed_section_ids or [],
    )
    progress_values = _entry_progress_values(payload)

    try:
        return repo.save_entry(
            study_id=meta.id,
            study_name=meta.study_name,
            subject_index=access.subject_index,
            visit_index=access.visit_index,
            group_index=access.group_index,
            form_version=form_version,
            data=payload.data,
            skipped_required_flags=_flags_dict_to_list(payload.skipped_required_flags, selected_models),
            actor="shared-link",
            actor_name="Shared link submit",
            user_id=None,
            audit_label=audit_label,
            **progress_values,
        )
    except Exception as e:
        _raise_storage_unavailable(e, context="shared_upsert_data")
    finally:
        release_activity_by_session(
            db,
            session_jti=submit_jti,
            reason="shared_link_submit_complete",
            sync_after_release=True,
        )


@router.delete("/studies/{study_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_study(
    study_id: int,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    meta = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == study_id).first()
    if not meta:
        raise HTTPException(status_code=404, detail="Study not found")

    _assert_owner_or_admin(meta, current_user)

    active_activity_count = (
        db.query(models.StudyActivity)
        .filter(
            models.StudyActivity.study_id == study_id,
            models.StudyActivity.state.in_(("active", "syncing")),
        )
        .count()
    )
    if active_activity_count:
        logger.info(
            "Deleting study_id=%s while %s study activity row(s) are active; "
            "owner/admin delete is authoritative.",
            study_id,
            active_activity_count,
        )

    _dataset_id, source_dataset_path = _latest_remote_reference(db, study_id)
    dataset_path = source_dataset_path or repo.study_dataset_path(study_id, meta.study_name)
    remote_url = repo.remote_delete_url_for_dataset(dataset_path)
    remote_delete_error = None

    if remote_url:
        try:
            repo.delete_remote_bare_repo_url(
                remote_url,
                expected_dataset_name=dataset_path.name,
            )
            repo.delete_remote_worktree_for_dataset(dataset_path)
        except Exception as e:
            if "Refusing to delete" in str(e):
                raise HTTPException(status_code=500, detail=f"Unsafe remote delete blocked: {str(e)}")
            remote_delete_error = e
            logger.warning(
                "Juseless delete failed for study_id=%s remote=%s; queueing retry and continuing local delete: %s",
                study_id,
                remote_url,
                e,
            )

    try:
        repo.delete_local_study(study_id, meta.study_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete local study dataset: {str(e)}")

    try:
        if remote_delete_error is not None and remote_url:
            enqueue_pending_remote_delete(
                db,
                study_id=study_id,
                study_name=meta.study_name,
                dataset_path=str(dataset_path),
                remote_url=remote_url,
                last_error=str(remote_delete_error),
            )
        db.query(models.StudyMetadata).filter(
            models.StudyMetadata.draft_of_study_id == study_id
        ).update({"draft_of_study_id": None}, synchronize_session=False)
        db.query(models.StudyActivity).filter(models.StudyActivity.study_id == study_id).delete(synchronize_session=False)
        db.query(models.SharedFormAccess).filter(models.SharedFormAccess.study_id == study_id).delete(synchronize_session=False)
        db.query(models.StudyAccessGrant).filter(models.StudyAccessGrant.study_id == study_id).delete(synchronize_session=False)
        db.query(models.StudyTemplateVersion).filter(models.StudyTemplateVersion.study_id == study_id).delete(synchronize_session=False)
        db.query(models.StudyEntryData).filter(models.StudyEntryData.study_id == study_id).delete(synchronize_session=False)
        db.query(models.File).filter(models.File.study_id == study_id).delete(synchronize_session=False)
        db.query(models.StudyContent).filter(models.StudyContent.study_id == study_id).delete(synchronize_session=False)
        db.query(models.StudyMetadata).filter(models.StudyMetadata.id == study_id).delete(synchronize_session=False)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return
