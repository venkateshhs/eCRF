from __future__ import annotations

import json
import os
import secrets
import shutil
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File, Form, Body, Request, status
from fastapi.responses import FileResponse, RedirectResponse

from sqlalchemy.orm import Session

from .database import get_db
from . import schemas, models
from .users import get_current_user
from .datalad_repo import DataladStudyRepo, _deepcopy_json, local_now
from .versions import VersionManager
from .settings import get_settings

router = APIRouter(prefix="/forms", tags=["forms"])
repo = DataladStudyRepo()

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


def _get_latest_template_version_row(db: Session, study_id: int) -> Optional[models.StudyTemplateVersion]:
    return (
        db.query(models.StudyTemplateVersion)
        .filter(models.StudyTemplateVersion.study_id == study_id)
        .order_by(models.StudyTemplateVersion.version.desc())
        .first()
    )


def _ensure_initial_version_if_missing(db: Session, study_id: int, study_data: Dict[str, Any]) -> models.StudyTemplateVersion:
    VersionManager.ensure_initial_version(db, study_id, study_data or {})
    row = _get_latest_template_version_row(db, study_id)
    if row is None:
        raise HTTPException(status_code=500, detail="Failed to initialize template version")
    return row


def _latest_template_or_500(db: Session, study_id: int) -> models.StudyTemplateVersion:
    row = _get_latest_template_version_row(db, study_id)
    if row is None:
        raise HTTPException(status_code=500, detail="Template version not found")
    return row


def _resolve_form_version_or_400(db: Session, study_id: int, version: Optional[int]) -> int:
    try:
        return VersionManager.assert_latest_is_used(db, study_id, version)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


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

    if desired_status == "PUBLISHED":
        _write_published_snapshot_to_datalad(
            meta=meta,
            study_data=content_row.study_data or {},
            template_version=tv.version,
            template_schema=tv.schema or {},
            actor=_actor_identifier(user),
            actor_name=_display_name(user),
            user_id=user.id,
            audit_label=audit_label,
        )

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
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    meta = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == study_id).first()
    if not meta:
        raise HTTPException(status_code=404, detail="Study not found")

    perms = _assert_has_study_permission(db, meta, user, required="view")
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
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    meta = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == study_id).first()
    if not meta:
        raise HTTPException(status_code=404, detail="Study not found")

    _assert_has_study_permission(db, meta, user, required="view")

    if (meta.status or "PUBLISHED").upper().strip() != "PUBLISHED":
        raise HTTPException(status_code=400, detail="Data entry is only available for published studies")

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
        _write_published_snapshot_to_datalad(
            meta=meta,
            study_data=content_row.study_data or {},
            template_version=latest_tv.version,
            template_schema=latest_tv.schema or {},
            actor=_actor_identifier(user),
            actor_name=_display_name(user),
            user_id=user.id,
            audit_label=audit_label,
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

    meta.status = "PUBLISHED"
    db.commit()
    db.refresh(meta)

    _write_published_snapshot_to_datalad(
        meta=meta,
        study_data=content_row.study_data or {},
        template_version=latest_tv.version,
        template_schema=latest_tv.schema or {},
        actor=_actor_identifier(user),
        actor_name=_display_name(user),
        user_id=user.id,
        audit_label=audit_label,
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
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    meta = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == study_id).first()
    if not meta:
        raise HTTPException(status_code=404, detail="Study not found")

    _assert_has_study_permission(db, meta, user, required="view")
    return repo.list_files(study_id, meta.study_name)

@router.get("/studies/{study_id}/download")
def download_full_study(
    study_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    meta = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == study_id).first()
    if not meta:
        raise HTTPException(status_code=404, detail="Study not found")
    # Only owner or admin can download study
    _assert_owner_or_admin(meta, user)

    try:
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
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    meta = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == study_id).first()
    if not meta:
        raise HTTPException(status_code=404, detail="Study not found")

    _assert_has_study_permission(db, meta, user, required="add_data")
    _assert_not_locked_by_other(meta, user)

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, prefix=f"ecrf_study{study_id}_", suffix=f"_{uploaded_file.filename}") as tmp:
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
    audit_label: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    meta = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == study_id).first()
    if not meta:
        raise HTTPException(status_code=404, detail="Study not found")

    _assert_has_study_permission(db, meta, user, required="add_data")
    _assert_not_locked_by_other(meta, user)

    return repo.save_url_file(
        study_id=study_id,
        study_name=meta.study_name,
        url=url,
        description=description,
        subject_index=subject_index,
        visit_index=visit_index,
        group_index=group_index,
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
            actor="shared-link",
            actor_name="Shared link upload",
            user_id=None,
            audit_label=audit_label,
        )
    finally:
        try:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass

@router.get("/studies/{study_id}/files/{file_id}/download")
def download_study_file(
    study_id: int,
    file_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    meta = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == study_id).first()
    if not meta:
        raise HTTPException(status_code=404, detail="Study not found")

    _assert_can_download_study_file(db, meta, user)

    try:
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
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    meta = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == study_id).first()
    if not meta:
        raise HTTPException(status_code=404, detail="Study not found")

    _assert_has_study_permission(db, meta, current_user, required="add_data")
    _assert_not_locked_by_other(meta, current_user)

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
    )


@router.put("/studies/{study_id}/data_entries/{entry_id}", response_model=schemas.StudyDataEntryOut)
def update_study_data_entry(
    study_id: int,
    entry_id: int,
    payload: schemas.StudyDataEntryCreate = Body(...),
    expected_revision_token: str = Query(...),
    audit_label: Optional[str] = Query(None),
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
        },
        actor=_actor_identifier(user),
        actor_name=_display_name(user),
        user_id=user.id,
        audit_label=audit_label,
    )


@router.get("/studies/{study_id}/data_entries", response_model=schemas.PaginatedStudyDataEntries)
def list_study_data_entries(
    study_id: int,
    subject_indexes: Optional[str] = Query(None),
    visit_indexes: Optional[str] = Query(None),
    all: bool = Query(False),
    current_only: bool = Query(False),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    meta = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == study_id).first()
    if not meta:
        raise HTTPException(status_code=404, detail="Study not found")

    _assert_has_study_permission(db, meta, user, required="view")

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
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    meta = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == study_id).first()
    if not meta:
        raise HTTPException(status_code=404, detail="Study not found")

    _assert_owner_or_admin(meta, user)
    _assert_not_locked_by_other(meta, user)

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
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    meta = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == study_id).first()
    if not meta:
        raise HTTPException(status_code=404, detail="Study not found")

    _assert_owner_or_admin(meta, current_user)
    _assert_not_locked_by_other(meta, current_user)

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


@router.post("/share-link/", status_code=201)
def create_share_link(
    payload: schemas.ShareLinkCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    meta = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == payload.study_id).first()
    if not meta:
        raise HTTPException(status_code=404, detail="Study not found")

    _assert_owner_or_admin(meta, current_user)
    _assert_not_locked_by_other(meta, current_user)

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
    db.commit()
    db.refresh(access)
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

    frontend_base = os.getenv("FRONTEND_BASE_URL", "").rstrip("/")
    if not frontend_base:
        frontend_base = f"{request.url.scheme}://{request.headers.get('host', request.url.netloc)}"

    return {"token": token, "link": f"{frontend_base}/shared/{token}"}


@router.get("/shared-api/{token}", response_model=schemas.SharedFormAccessOut)
def access_shared_form(
    token: str,
    db: Session = Depends(get_db),
):
    access = db.query(models.SharedFormAccess).filter_by(token=token).first()
    if not access:
        raise HTTPException(404, "Link not found")
    if access.used_count >= access.max_uses:
        raise HTTPException(403, "Usage limit exceeded")
    if access.expires_at < datetime.utcnow():
        raise HTTPException(403, "Link expired")

    access.used_count += 1
    db.commit()

    meta = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == access.study_id).first()
    if not meta:
        raise HTTPException(404, "Study not found")
    try:
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
    except Exception:
        pass
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

    form_version = _resolve_form_version_or_400(db, access.study_id, version)

    content_row = _get_content_row_or_404(db, access.study_id)
    study_data = content_row.study_data or {}
    selected_models = study_data.get("selectedModels") or []

    _validate_shared_payload_sections(
        payload_data=payload.data or {},
        study_data=study_data,
        allowed_section_ids=access.allowed_section_ids or [],
    )

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
    )


@router.delete("/studies/{study_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_study(
    study_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    meta = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == study_id).first()
    if not meta:
        raise HTTPException(status_code=404, detail="Study not found")

    _assert_owner_or_admin(meta, current_user)

    try:
        repo.delete_study(study_id, meta.study_name)
    except Exception:
        pass

    db.query(models.SharedFormAccess).filter(models.SharedFormAccess.study_id == study_id).delete()
    db.query(models.StudyAccessGrant).filter(models.StudyAccessGrant.study_id == study_id).delete()
    db.query(models.StudyTemplateVersion).filter(models.StudyTemplateVersion.study_id == study_id).delete()
    db.query(models.StudyContent).filter(models.StudyContent.study_id == study_id).delete()
    db.query(models.StudyMetadata).filter(models.StudyMetadata.id == study_id).delete()
    db.commit()

    return