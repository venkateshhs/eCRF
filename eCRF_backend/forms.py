# eCRF_backend/forms.py
import os
import platform
import subprocess
import shutil
import tempfile
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse

from fastapi import Request
from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File, Form, Body, status
from pathlib import Path
import json
import yaml
from datetime import datetime, timedelta

from .datalad_hooks import snapshot_study_after_change
from .versions import VersionManager
from .database import get_db
from . import schemas, crud, models
from .bids_exporter import (
    upsert_bids_dataset,
    write_entry_to_bids,
    stage_file_for_modalities,
    audit_change_both,  # unified audit (DB + BIDS)
    audit_access_change_both,  # unified access audit
    log_dataset_change_to_changes,  # optional BIDS CHANGES mirror
    bump_bids_version, bulk_write_entries_to_bids, _dataset_path, _delete_bids_folder_safe,
)
from .logger import logger
from .models import User, StudyTemplateVersion
from .schemas import BulkPayload
from .users import get_current_user
from sqlalchemy.orm import Session
import secrets
from sqlalchemy import or_, text
from .utils import local_now
from sqlalchemy.sql import func
router = APIRouter(prefix="/forms", tags=["forms"])

TEMPLATE_DIR = Path(os.environ.get("ECRF_TEMPLATES_DIR", "")) if os.environ.get("ECRF_TEMPLATES_DIR") \
    else (Path(__file__).resolve().parent / "templates")

ALLOWED_STUDY_STATUS = {"DRAFT", "PUBLISHED", "ARCHIVED"}
_DEFAULT_GRANT_PERMS = {"view": True, "add_data": True, "edit_study": False}


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


def _filter_shared_study_data_by_sections(study_data: Dict[str, Any], allowed_section_ids: Optional[List[str]]) -> Dict[str, Any]:
    """
    Filter selectedModels + assignments so the shared-link user only sees allowed sections.
    If allowed_section_ids is empty, keep existing behavior (all sections visible).
    """
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
    """
    Returns {section_title: section_id} for sections allowed in this shared link.
    If no allowed_section_ids are stored, all sections are allowed.
    """
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


def _validate_shared_payload_sections(
    payload_data: Dict[str, Any],
    study_data: Dict[str, Any],
    allowed_section_ids: Optional[List[str]],
) -> None:
    """
    Backend enforcement:
    shared-link save payload may only contain allowed sections.
    Payload structure is dict keyed by section title.
    """
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

def _norm_audit_label(label: Optional[str]) -> Optional[str]:
    """
    Human readable audit label/description passed from frontend.
    Keep None if absent so you can detect missing frontend wiring.
    """
    if label is None:
        return None
    s = str(label).strip()
    return s if s else None

def _json_safe(x: Any) -> Any:
    try:
        json.dumps(x, ensure_ascii=False)
        return x
    except Exception:
        try:
            return str(x)
        except Exception:
            return None

def _compute_json_diff(old: Any, new: Any, path: str = "") -> List[Dict[str, Any]]:
    """
    Minimal, generic JSON diff.
    Output entries like:
      { "op": "replace"|"add"|"remove", "path": "...", "old": ..., "new": ... }
    """
    diffs: List[Dict[str, Any]] = []

    if old is new:
        return diffs

    if isinstance(old, (str, int, float, bool)) or old is None or \
       isinstance(new, (str, int, float, bool)) or new is None:
        if old != new:
            diffs.append({"op": "replace", "path": path or "/", "old": _json_safe(old), "new": _json_safe(new)})
        return diffs

    if isinstance(old, dict) and isinstance(new, dict):
        old_keys = set(old.keys())
        new_keys = set(new.keys())

        for k in sorted(old_keys - new_keys):
            p = f"{path}/{k}" if path else f"/{k}"
            diffs.append({"op": "remove", "path": p, "old": _json_safe(old.get(k)), "new": None})

        for k in sorted(new_keys - old_keys):
            p = f"{path}/{k}" if path else f"/{k}"
            diffs.append({"op": "add", "path": p, "old": None, "new": _json_safe(new.get(k))})

        for k in sorted(old_keys & new_keys):
            p = f"{path}/{k}" if path else f"/{k}"
            diffs.extend(_compute_json_diff(old.get(k), new.get(k), p))

        return diffs

    if isinstance(old, list) and isinstance(new, list):
        min_len = min(len(old), len(new))

        for i in range(min_len):
            p = f"{path}/{i}" if path else f"/{i}"
            diffs.extend(_compute_json_diff(old[i], new[i], p))

        for i in range(len(new), len(old)):
            p = f"{path}/{i}" if path else f"/{i}"
            diffs.append({"op": "remove", "path": p, "old": _json_safe(old[i]), "new": None})

        for i in range(len(old), len(new)):
            p = f"{path}/{i}" if path else f"/{i}"
            diffs.append({"op": "add", "path": p, "old": None, "new": _json_safe(new[i])})

        return diffs

    if old != new:
        diffs.append({"op": "replace", "path": path or "/", "old": _json_safe(old), "new": _json_safe(new)})
    return diffs

def _is_admin(user: models.User) -> bool:
    role = (getattr(getattr(user, "profile", None), "role", "") or "").strip()
    return role == "Administrator"

def _effective_study_permissions(db: Session, meta: models.StudyMetadata, user: models.User) -> Dict[str, bool]:
    """
    Effective permissions for (user, study).

    Rules (per your description):
    - Administrator: full access.
    - Study owner (created_by): full access.
    - Otherwise: use StudyAccessGrant.permissions (merged with defaults).
    """
    if _is_admin(user) or meta.created_by == user.id:
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

    # merge with defaults
    return {
        "view": bool(perms.get("view", _DEFAULT_GRANT_PERMS["view"])),
        "add_data": bool(perms.get("add_data", _DEFAULT_GRANT_PERMS["add_data"])),
        "edit_study": bool(perms.get("edit_study", _DEFAULT_GRANT_PERMS["edit_study"])),
    }


def _get_grant(db: Session, study_id: int, user_id: int):
    return (
        db.query(models.StudyAccessGrant)
          .filter_by(study_id=study_id, user_id=user_id)
          .first()
    )

def _assert_has_study_permission(db: Session, meta: models.StudyMetadata, user: models.User, required: str = "view"):
    role = (getattr(user.profile, "role", "") or "").strip()
    is_admin = role == "Administrator"
    is_owner = (meta.created_by == user.id)

    if is_admin or is_owner:
        return {"view": True, "add_data": True, "edit_study": True}

    grant = _get_grant(db, meta.id, user.id)
    perms = (grant.permissions or {}) if grant else {}

    # default to False if missing
    if not perms.get(required, False):
        raise HTTPException(status_code=403, detail="Not authorized")

    return perms

def _norm_status(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    s2 = str(s).strip().upper()
    return s2 if s2 in ALLOWED_STUDY_STATUS else None

def _get_meta_status(meta: models.StudyMetadata) -> str:
    # DB default should keep this non-null, but be defensive
    return (getattr(meta, "status", None) or "PUBLISHED").strip().upper()

def _is_publish_transition(old_status: str, new_status: str) -> bool:
    return old_status != "PUBLISHED" and new_status == "PUBLISHED"

def _flags_dict_to_list(flags, selected_models):
    # Already normalized
    if isinstance(flags, list):
        return flags
    # Accept nulls and odd types
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


def _deepcopy_json(obj):
    try:
        return json.loads(json.dumps(obj, ensure_ascii=False))
    except Exception:
        return {}

def _coerce_snapshot_schema(raw):
    """
    Create a *version snapshot* that preserves rich study metadata and models.
    Also normalizes groups/visits so diffs don't break if arrays are strings.
    Does NOT affect the saved StudyContent; only the StudyTemplateVersion schema.
    """
    snap = _deepcopy_json(raw if isinstance(raw, dict) else {})
    # ensure study subobject exists
    if "study" not in snap or not isinstance(snap.get("study"), dict):
        title = snap.get("title") if isinstance(snap.get("title"), str) else ""
        description = snap.get("description") if isinstance(snap.get("description"), str) else ""
        snap["study"] = {"title": title, "description": description}

    # normalize groups/visits into [{name}]
    def _norm_name_list(key):
        items = snap.get(key, [])
        if isinstance(items, list):
            norm = []
            for it in items:
                if isinstance(it, str):
                    norm.append({"name": it})
                elif isinstance(it, dict):
                    # keep dict; ensure it has name/title
                    if "name" in it and isinstance(it["name"], str):
                        norm.append(it)
                    elif "title" in it and isinstance(it["title"], str):
                        norm.append({"name": it["title"], **{k: v for k, v in it.items() if k != "title"}})
                    else:
                        norm.append({"name": str(it)})
                else:
                    norm.append({"name": str(it)})
            snap[key] = norm
    _norm_name_list("groups")
    _norm_name_list("visits")

    # ensure selectedModels present; if only legacy "models" names exist, lift them
    if "selectedModels" not in snap and isinstance(snap.get("models"), list):
        snap["selectedModels"] = [
            ({"title": m} if isinstance(m, str) else m) for m in snap["models"]
        ]

    return snap


def _assert_owner_or_admin(meta: models.StudyMetadata, user) -> None:
    if meta.created_by != user.id and getattr(user.profile, "role", None) != "Administrator":
        raise HTTPException(status_code=403, detail="Not authorized")

def _display_name(u: models.User) -> str:
    if not u:
        return ""
    first = getattr(getattr(u, "profile", None), "first_name", "") or ""
    last  = getattr(getattr(u, "profile", None), "last_name", "") or ""
    full  = (first + " " + last).strip()
    return full or u.username or u.email or f"User#{u.id}"

@router.get("/available-fields")
async def get_available_fields():
    """
    Return list of generic/custom field definitions from available-fields.json.
    If missing, return [] so the UI doesn't break.
    """
    path = TEMPLATE_DIR / "available-fields.json"
    if not path.exists():
        logger.warning("available-fields.json not found at %s — returning empty list", path)
        return []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, list) else []
    except Exception as e:
        logger.exception("Error loading available-fields.json: %s", e)
        raise HTTPException(status_code=500, detail="Error loading available fields.")


@router.get("/specialized-fields")
async def get_specialized_fields():
    try:
        available_fields_file = TEMPLATE_DIR / "specialized-fields.json"
        if not available_fields_file.exists():
            raise HTTPException(status_code=404, detail="Available fields file not found.")
        with open(available_fields_file, "r") as file:
            data = json.load(file)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading available fields: {str(e)}")


def load_yaml_file(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return yaml.safe_load(file)
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None


@router.post("/studies/", response_model=schemas.StudyFull)
def create_study(
    study_metadata: schemas.StudyMetadataCreate,
    study_content: schemas.StudyContentCreate,
    create_bids: bool = Query(True, description="If false, skip BIDS dataset folder creation for this request"),

    # allow draft creation without new endpoints
    status: Optional[str] = Query(None, description="Optional: DRAFT|PUBLISHED|ARCHIVED (defaults to PUBLISHED)"),
    draft_of_study_id: Optional[int] = Query(None, description="Optional: published study id if creating an edit-draft"),
    last_completed_step: Optional[int] = Query(None, description="Optional: resume helper"),
    audit_label: Optional[str] = Query(None, description="Optional: human-readable audit label from frontend"),
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    if study_metadata.created_by != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to create study for this user")

    desired_status = _norm_status(status) or "PUBLISHED"
    if desired_status == "DRAFT":
        # Drafts should not create BIDS folders by default (prevents clutter)
        create_bids = False

    # If this is an edit-draft, validate the referenced published study exists + permissions
    if draft_of_study_id is not None:
        base = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == draft_of_study_id).first()
        if not base:
            raise HTTPException(status_code=404, detail="draft_of_study_id study not found")
        if base.created_by != user.id and getattr(user.profile, "role", None) != "Administrator":
            raise HTTPException(status_code=403, detail="Not authorized to draft-edit this study")
        desired_status = "DRAFT"  # force

    # Keep a *pre-BIDS* snapshot (so labels/IDs aren’t rewritten) for versioning
    incoming_snapshot = _deepcopy_json(study_content.study_data or {})

    try:
        metadata, content = crud.create_study(db, study_metadata, study_content)
    except Exception as e:
        logger.error("Error creating study: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

    # persist workflow fields on metadata (keeps crud unchanged)
    try:
        metadata.status = desired_status
        metadata.draft_of_study_id = draft_of_study_id
        if last_completed_step is not None:
            metadata.last_completed_step = int(last_completed_step)
        db.commit()
        db.refresh(metadata)
        snapshot_study_after_change(
            db=db,
            study_id=study_metadata.id,
            action="create_study",
        )
    except Exception as e:
        db.rollback()
        logger.error("Error updating draft workflow fields: %s", e)
        raise HTTPException(status_code=500, detail="Error creating draft workflow fields")

    # Initialize BIDS dataset (OPTIONAL) — skip for drafts by default
    if create_bids and upsert_bids_dataset and _get_meta_status(metadata) != "DRAFT":
        try:
            dataset_path = upsert_bids_dataset(
                study_id=metadata.id,
                study_name=metadata.study_name,
                study_description=metadata.study_description,
                study_data=content.study_data,
            )
            # persist any label-map mutations made by upsert
            db.query(models.StudyContent).filter(models.StudyContent.id == content.id).update(
                {"study_data": content.study_data}
            )
            db.commit()
            db.refresh(content)
            logger.info("BIDS dataset initialized at %s (study_id=%s)", dataset_path, metadata.id)
            log_dataset_change_to_changes(metadata.id, metadata.study_name, action="dataset_initialized",
                                          actor_id=user.id, actor_name=_display_name(user),
                                          detail="Initial BIDS dataset creation")
            try:
                # NO DIFF for new study creation
                audit_change_both(
                    scope="study",
                    action="study_created",
                    actor=_display_name(user),
                    extra={
                        "study_name": metadata.study_name,
                        "ui_label": _norm_audit_label(audit_label),
                        "has_diff": False,
                        "diff_payload": None,
                    },
                    study_id=metadata.id,
                    study_name=metadata.study_name,
                    db=db,
                    actor_id=user.id
                )
            except Exception:
                pass
        except Exception as be:
            logger.error("BIDS export (create) failed for study %s: %s", metadata.id, be)

    # Ensure/initialize v1 template snapshot (structural)
    try:
        VersionManager.ensure_initial_version(db, metadata.id, incoming_snapshot)
    except Exception as ve:
        logger.error("Failed to init template version for study %s: %s", metadata.id, ve)

    return {"metadata": metadata, "content": content}

@router.get("/studies", response_model=List[schemas.StudyMetadataOut])
def list_studies(
    status: Optional[str] = Query(None, description="Optional: DRAFT|PUBLISHED|ARCHIVED"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    role = (getattr(getattr(current_user, "profile", None), "role", "") or "").strip()
    status_norm = _norm_status(status)

    q = db.query(models.StudyMetadata)

    # ----------------------------
    # Visibility filter
    # ----------------------------
    if role != "Administrator":
        # SQLite JSON filtering:
        # Include a study if user is owner OR there is a grant row that gives *any* access.
        # "any access" = view OR add_data OR edit_study
        # Defaults if key missing/null:
        #   view: True, add_data: True, edit_study: False
        view_expr = func.coalesce(func.json_extract(models.StudyAccessGrant.permissions, "$.view"), 1)
        add_expr  = func.coalesce(func.json_extract(models.StudyAccessGrant.permissions, "$.add_data"), 1)
        edit_expr = func.coalesce(func.json_extract(models.StudyAccessGrant.permissions, "$.edit_study"), 0)

        grant_subq = (
            db.query(models.StudyAccessGrant.study_id)
              .filter(models.StudyAccessGrant.user_id == current_user.id)
              .filter(
                  (view_expr == 1) | (add_expr == 1) | (edit_expr == 1)
              )
              .subquery()
        )

        q = q.filter(
            or_(
                models.StudyMetadata.created_by == current_user.id,
                models.StudyMetadata.id.in_(grant_subq),
            )
        )

    # Optional status filter
    if status_norm:
        q = q.filter(models.StudyMetadata.status == status_norm)

    studies = q.all()

    # ----------------------------
    # Attach per-study effective permissions for current user
    # (serialized as `permissions` via schema)
    # ----------------------------
    for m in studies:
        m.permissions = _effective_study_permissions(db, m, current_user)

    return studies




@router.get("/studies/{study_id}", response_model=schemas.StudyFull)
def read_study(
    study_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    result = crud.get_study_full(db, study_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Study not found")

    metadata, content = result

    #  canonical auth + returns effective perms
    perms = _assert_has_study_permission(db, metadata, user, required="view")

    # Convert ORM -> schema dict, then attach perms
    try:
        meta_out = schemas.StudyMetadataOut.model_validate(metadata).model_dump()
    except Exception:
        # fallback if you're not on pydantic v2 in this path
        meta_out = {
            "id": metadata.id,
            "study_name": metadata.study_name,
            "study_description": metadata.study_description,
            "status": metadata.status,
            "draft_of_study_id": metadata.draft_of_study_id,
            "last_completed_step": metadata.last_completed_step,
            "created_by": metadata.created_by,
            "created_at": metadata.created_at,
            "updated_at": metadata.updated_at,
        }

    #  this is what StudyView/StudyDataDashboard need
    meta_out["permissions"] = {
        "view": bool(perms.get("view", False)),
        "add_data": bool(perms.get("add_data", False)),
        "edit_study": bool(perms.get("edit_study", False)),
    }

    return {"metadata": meta_out, "content": content}

@router.get("/studies/{study_id}/versions")
def list_study_versions(
    study_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    meta = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == study_id).first()
    if not meta:
        raise HTTPException(status_code=404, detail="Study not found")
    role = (getattr(user.profile, "role", "") or "").strip()
    is_admin = role == "Administrator"
    is_owner = (meta.created_by == user.id)
    if not (is_admin or is_owner):
        grant = (
            db.query(models.StudyAccessGrant)
              .filter_by(study_id=study_id, user_id=user.id)
              .first()
        )
        if not grant or not (grant.permissions or {}).get("view", True):
            raise HTTPException(status_code=403, detail="Not authorized")

    versions = (
        db.query(StudyTemplateVersion)
          .filter(StudyTemplateVersion.study_id == study_id)
          .order_by(StudyTemplateVersion.version.asc())
          .all()
    )
    return [
        {"version": v.version, "created_at": v.created_at}
        for v in versions
    ]


@router.get("/studies/{study_id}/template")
def get_template_version(
    study_id: int,
    version: Optional[int] = Query(None, description="If omitted, returns latest template schema"),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    meta = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == study_id).first()
    if not meta:
        raise HTTPException(status_code=404, detail="Study not found")

    # allow any user who can view this study (or add/edit)
    _assert_has_study_permission(db, meta, user, required="view")

    q = db.query(StudyTemplateVersion).filter(StudyTemplateVersion.study_id == study_id)
    if version is not None:
        v = q.filter(StudyTemplateVersion.version == version).first()
        if not v:
            raise HTTPException(status_code=404, detail=f"Version {version} not found")
        return {"study_id": study_id, "version": v.version, "schema": v.schema, "created_at": v.created_at}

    latest = q.order_by(StudyTemplateVersion.version.desc()).first()
    if not latest:
        raise HTTPException(status_code=404, detail="No versions found")
    return {"study_id": study_id, "version": latest.version, "schema": latest.schema, "created_at": latest.created_at}

@router.post("/studies/{study_id}/versioning/preview")
def preview_versioning_decision(
    study_id: int,
    study_content: schemas.StudyContentUpdate = Body(..., embed=True),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    meta = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == study_id).first()
    if not meta:
        raise HTTPException(status_code=404, detail="Study not found")
    _assert_owner_or_admin(meta, user)

    content = db.query(models.StudyContent).filter(models.StudyContent.study_id == study_id).first()
    old_sd = (content.study_data if content else {}) or {}
    new_sd = (study_content.study_data or {}) or {}

    decision = VersionManager.preview_decision(db, study_id, old_sd, new_sd)
    return decision


@router.put("/studies/{study_id}", response_model=schemas.StudyFull)
def update_study(
    study_id: int,
    study_metadata: schemas.StudyMetadataUpdate = Body(..., embed=True),
    study_content: schemas.StudyContentUpdate = Body(..., embed=True),
    audit_label: Optional[str] = Query(None, description="Optional: human-readable audit label from frontend"),
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    existing = crud.get_study_full(db, study_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Study not found")
    metadata, content = existing
    if metadata.created_by != user.id and user.profile.role != "Administrator":
        raise HTTPException(status_code=403, detail="Not authorized to update this study")

    # normalize payload
    if not study_content.study_data:
        study_content.study_data = {}

    # Ensure id present in study_data
    if not study_content.study_data.get("id"):
        study_content.study_data["id"] = study_id

    old_status = _get_meta_status(metadata)

    incoming_status = _norm_status(getattr(study_metadata, "status", None))
    if not incoming_status:
        incoming_status = old_status  # no change

    # Track last_completed_step if provided in schema; ignore if schema doesn't include it
    if hasattr(study_metadata, "last_completed_step") and getattr(study_metadata, "last_completed_step", None) is not None:
        try:
            metadata.last_completed_step = int(getattr(study_metadata, "last_completed_step"))
            db.commit()
            snapshot_study_after_change(
                db=db,
                study_id=study_id,
                action="update_study",
            )
            db.refresh(metadata)
        except Exception:
            db.rollback()

    is_edit_draft = (getattr(metadata, "draft_of_study_id", None) is not None)
    publish_edit_draft = is_edit_draft and _is_publish_transition(old_status, incoming_status)
    ui_label = _norm_audit_label(audit_label)

    # --------------------------
    # Case A: publishing an edit-draft
    # --------------------------
    if publish_edit_draft:
        published_id = int(metadata.draft_of_study_id)

        # 1) First, persist the last changes into the draft row itself (no BIDS/versioning for drafts)
        try:
            crud.update_study(db, study_id, study_metadata, study_content)
        except Exception as e:
            logger.error("Error updating draft before publish: %s", e)
            raise HTTPException(status_code=500, detail=str(e))

        # Reload draft after update
        draft_meta, draft_content = crud.get_study_full(db, study_id)

        # 2) Load published target and authorize
        published_full = crud.get_study_full(db, published_id)
        if not published_full:
            raise HTTPException(status_code=404, detail="Published study not found for draft_of_study_id")

        pub_meta, pub_content = published_full
        if pub_meta.created_by != user.id and user.profile.role != "Administrator":
            raise HTTPException(status_code=403, detail="Not authorized to publish changes to this study")

        # Capture previous latest template version for published
        prev_v_row = (
            db.query(StudyTemplateVersion)
              .filter(StudyTemplateVersion.study_id == published_id)
              .order_by(StudyTemplateVersion.version.desc())
              .first()
        )
        prev_latest_v = int(prev_v_row.version) if prev_v_row else 1

        old_sd_published = _deepcopy_json(pub_content.study_data or {})
        new_sd_from_draft = _deepcopy_json(draft_content.study_data or {})
        new_sd_from_draft["id"] = published_id  # critical: keep canonical id stable

        # 3) Apply draft -> published in a transaction
        try:
            pub_meta.study_name = draft_meta.study_name
            pub_meta.study_description = draft_meta.study_description
            pub_meta.status = "PUBLISHED"
            pub_content.study_data = new_sd_from_draft
            db.commit()
            db.refresh(pub_meta)
            db.refresh(pub_content)
        except Exception as e:
            db.rollback()
            logger.error("Error applying draft to published: %s", e)
            raise HTTPException(status_code=500, detail="Failed to publish draft changes")

        # 4) BIDS update for published (now that it's updated)
        if upsert_bids_dataset:
            try:
                dataset_path = upsert_bids_dataset(
                    study_id=pub_meta.id,
                    study_name=pub_meta.study_name,
                    study_description=pub_meta.study_description,
                    study_data=pub_content.study_data,
                )
                db.query(models.StudyContent).filter(models.StudyContent.id == pub_content.id).update(
                    {"study_data": pub_content.study_data}
                )
                db.commit()
                db.refresh(pub_content)
                logger.info("BIDS dataset updated at %s (study_id=%s)", dataset_path, pub_meta.id)

                log_dataset_change_to_changes(
                    pub_meta.id,
                    pub_meta.study_name,
                    action="dataset_structure_updated",
                    actor_id=user.id,
                    actor_name=_display_name(user),
                    detail="Published changes from draft",
                )

                # CHANGE => diff payload for study template
                diffs = _compute_json_diff(old_sd_published, _deepcopy_json(pub_content.study_data or {}))

                try:
                    audit_change_both(
                        scope="study",
                        action="study_edited",
                        actor=_display_name(user),
                        extra={
                            "study_name": pub_meta.study_name,
                            "published_from_draft": study_id,
                            "ui_label": ui_label,
                            "has_diff": bool(diffs),
                            "diff_payload": diffs if diffs else None,
                            "diff_kind": "study_template",
                        },
                        study_id=pub_meta.id,
                        study_name=pub_meta.study_name,
                        db=db,
                        actor_id=user.id,
                    )
                except Exception:
                    pass
            except Exception as be:
                logger.error("BIDS export (publish draft) failed for study %s: %s", pub_meta.id, be)

        # 5) Versioning on published (diff old published vs new published)
        def _audit(action: str, extra: Dict[str, Any]):
            if action in {"version_snapshot_refreshed"}:
                return
            try:
                audit_change_both(
                    scope="study",
                    action=action,
                    actor=_display_name(user),
                    extra={
                        **(extra or {}),
                        "ui_label": ui_label,
                        "has_diff": False,
                        "diff_payload": None,
                    },
                    study_id=pub_meta.id,
                    study_name=pub_meta.study_name,
                    db=db,
                    actor_id=user.id,
                )
            except Exception:
                pass

        try:
            VersionManager.apply_on_update(
                db,
                published_id,
                old_sd_published,
                _deepcopy_json(pub_content.study_data or {}),
                audit_callback=_audit,
            )
        except Exception as ve:
            logger.error("Versioning apply_on_update failed for published study %s: %s", published_id, ve)

        # Detect template version bump and copy BIDS tree non-destructively
        new_v_row = (
            db.query(StudyTemplateVersion)
              .filter(StudyTemplateVersion.study_id == published_id)
              .order_by(StudyTemplateVersion.version.desc())
              .first()
        )
        new_latest_v = int(new_v_row.version) if new_v_row else prev_latest_v
        if new_latest_v > prev_latest_v:
            try:
                bump_bids_version(pub_meta.id, pub_meta.study_name, prev_latest_v, new_latest_v)
            except Exception as be:
                logger.error("BIDS version bump copy failed for study %s: %s", published_id, be)

        # 6) Archive the draft row so it no longer appears as unfinished
        try:
            draft_meta.status = "ARCHIVED"
            db.commit()
        except Exception:
            db.rollback()

        return {"metadata": pub_meta, "content": pub_content}

    # --------------------------
    # Case B: normal update (draft save step OR published edit in-place)
    # --------------------------

    # snapshots for versioning (only for non-drafts)
    old_sd = _deepcopy_json(content.study_data or {})

    # capture previous latest template version (only meaningful for non-drafts)
    prev_v_row = (
        db.query(StudyTemplateVersion)
          .filter(StudyTemplateVersion.study_id == study_id)
          .order_by(StudyTemplateVersion.version.desc())
          .first()
    )
    prev_latest_v = int(prev_v_row.version) if prev_v_row else 1

    try:
        result = crud.update_study(db, study_id, study_metadata, study_content)
    except Exception as e:
        logger.error("Error updating study: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

    metadata, content = result

    # Apply status change (schema might not include it; keep safe)
    try:
        if incoming_status:
            metadata.status = incoming_status
        db.commit()
        db.refresh(metadata)
    except Exception:
        db.rollback()

    # If this is a draft update: do NOT touch BIDS/versioning (prevents clutter + avoids noisy versions)
    if _get_meta_status(metadata) == "DRAFT":
        return {"metadata": metadata, "content": content}

    # ---- existing behavior for published updates stays as-is ----

    # Update BIDS structure (and persist any label updates)
    if upsert_bids_dataset:
        try:
            dataset_path = upsert_bids_dataset(
                study_id=metadata.id,
                study_name=metadata.study_name,
                study_description=metadata.study_description,
                study_data=content.study_data,
            )
            db.query(models.StudyContent).filter(models.StudyContent.id == content.id).update(
                {"study_data": content.study_data}
            )
            db.commit()
            db.refresh(content)
            logger.info("BIDS dataset updated at %s (study_id=%s)", dataset_path, metadata.id)

            log_dataset_change_to_changes(
                metadata.id,
                metadata.study_name,
                action="dataset_structure_updated",
                actor_id=user.id,
                actor_name=_display_name(user),
                detail="Study metadata/content updated"
            )

            new_sd = _deepcopy_json(content.study_data or {})
            diffs = _compute_json_diff(old_sd, new_sd)

            try:
                audit_change_both(
                    scope="study",
                    action="study_edited",
                    actor=_display_name(user),
                    extra={
                        "study_name": metadata.study_name,
                        "ui_label": ui_label,
                        "has_diff": bool(diffs),
                        "diff_payload": diffs if diffs else None,
                        "diff_kind": "study_template",
                    },
                    study_id=metadata.id,
                    study_name=metadata.study_name,
                    db=db,
                    actor_id=user.id
                )
            except Exception:
                pass
        except Exception as be:
            logger.error("BIDS export (update) failed for study %s: %s", metadata.id, be)

    # Versioning: bump only if latest has data; otherwise overwrite; clone rows on bump
    def _audit(action: str, extra: Dict[str, Any]):
        if action in {"version_snapshot_refreshed"}:
            return
        try:
            audit_change_both(
                scope="study",
                action=action,
                actor=_display_name(user),
                extra={
                    **(extra or {}),
                    "ui_label": ui_label,
                    "has_diff": False,
                    "diff_payload": None,
                },
                study_id=metadata.id,
                study_name=metadata.study_name,
                db=db,
                actor_id=user.id,
            )
        except Exception:
            pass

    try:
        VersionManager.apply_on_update(db, study_id, old_sd, _deepcopy_json(content.study_data or {}), audit_callback=_audit)
    except Exception as ve:
        logger.error("Versioning apply_on_update failed for study %s: %s", study_id, ve)

    new_v_row = (
        db.query(StudyTemplateVersion)
          .filter(StudyTemplateVersion.study_id == study_id)
          .order_by(StudyTemplateVersion.version.desc())
          .first()
    )
    new_latest_v = int(new_v_row.version) if new_v_row else prev_latest_v
    if new_latest_v > prev_latest_v:
        try:
            bump_bids_version(metadata.id, metadata.study_name, prev_latest_v, new_latest_v)
        except Exception as be:
            logger.error("BIDS version bump copy failed for study %s: %s", study_id, be)

    return {"metadata": metadata, "content": content}

@router.get("/studies/{study_id}/files", response_model=List[schemas.FileOut])
def read_files_for_study(
    study_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    meta = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == study_id).first()
    if not meta:
        raise HTTPException(status_code=404, detail="Study not found")

    _assert_has_study_permission(db, meta, user, required="view")

    files = crud.get_files_for_study(db, study_id)
    return files


@router.post("/studies/{study_id}/files", response_model=schemas.FileOut)
def upload_file(
    study_id: int,
    uploaded_file: UploadFile = File(...),
    description: str = Form(""),
    storage_option: str = Form("local"),
    subject_index: Optional[int] = Form(None),
    visit_index: Optional[int] = Form(None),
    group_index: Optional[int] = Form(None),
    modalities_json: Optional[str] = Form("[]"),
    audit_label: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    study = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == study_id).first()
    if not study or study.created_by != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to upload file for this study")

    try:
        modalities = json.loads(modalities_json or "[]")
        if not isinstance(modalities, list):
            modalities = []
    except Exception:
        modalities = []

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, prefix=f"ecrf_study{study_id}_", suffix=f"_{uploaded_file.filename}") as tmp:
            shutil.copyfileobj(uploaded_file.file, tmp)
            tmp_path = tmp.name
        logger.info("Staged temp upload: %s", tmp_path)

        content = db.query(models.StudyContent).filter(models.StudyContent.study_id == study_id).first()
        study_data = content.study_data if content else {}

        current_form_version = VersionManager.latest_writable_version(db, study_id)

        stage_file_for_modalities(
            study_id=study.id,
            study_name=study.study_name,
            study_description=study.study_description,
            study_data=study_data,
            subject_index=subject_index,
            visit_index=visit_index,
            modalities=modalities,
            source_path=tmp_path,
            url=None,
            filename=uploaded_file.filename,
            actor=_display_name(user),
            db=db,
            actor_id=user.id,
            actor_name=_display_name(user),
            form_version=current_form_version,
        )

        file_data = schemas.FileCreate(
            study_id=study_id,
            file_name=uploaded_file.filename,
            file_path=uploaded_file.filename,
            description=description,
            storage_option="bids",
            subject_index=subject_index,
            visit_index=visit_index,
            group_index=group_index,
        )
        db_file = crud.create_file(db, file_data)
        snapshot_study_after_change(
            db=db,
            study_id=file_data.study_id,
            action="upload_file",
        )
        try:
            audit_change_both(
                scope="study",
                action="file_added",
                actor=_display_name(user),
                extra={
                    "file_name": uploaded_file.filename,
                    "modalities": modalities,
                    "subject_index": subject_index,
                    "visit_index": visit_index,
                    "ui_label": _norm_audit_label(audit_label),
                    "has_diff": False,
                    "diff_payload": None,
                },
                study_id=study_id,
                study_name=study.study_name,
                db=db,
                actor_id=user.id,
            )
        except Exception:
            pass

        return db_file

    except HTTPException:
        raise
    except Exception as e:
        logger.error("File upload/BIDS staging error: %s", e)
        raise HTTPException(status_code=500, detail="Error staging file to BIDS")
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
    storage_option: str = Form("url"),
    subject_index: Optional[int] = Form(None),
    visit_index: Optional[int] = Form(None),
    group_index: Optional[int] = Form(None),
    modalities_json: Optional[str] = Form("[]"),
    audit_label: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    study = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == study_id).first()
    if not study or study.created_by != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to create file for this study")

    try:
        modalities = json.loads(modalities_json or "[]")
        if not isinstance(modalities, list):
            modalities = []
    except Exception:
        modalities = []

    try:
        parsed = urlparse(url)
        base = os.path.basename(parsed.path) or "link"
        file_data = schemas.FileCreate(
            study_id=study_id,
            file_name=base,
            file_path=url,
            description=description,
            storage_option=storage_option or "url",
            subject_index=subject_index,
            visit_index=visit_index,
            group_index=group_index,
        )
        db_file = crud.create_file(db, file_data)
    except Exception as e:
        logger.error("Error creating URL file record: %s", e)
        raise HTTPException(status_code=500, detail="Error creating file record")

    try:
        content = db.query(models.StudyContent).filter(models.StudyContent.study_id == study_id).first()
        study_data = content.study_data if content else {}

        current_form_version = VersionManager.latest_writable_version(db, study_id)

        stage_file_for_modalities(
            study_id=study.id,
            study_name=study.study_name,
            study_description=study.study_description,
            study_data=study_data,
            subject_index=subject_index,
            visit_index=visit_index,
            modalities=modalities,
            source_path=None,
            url=url,
            filename=base,
            actor=_display_name(user),
            db=db,
            actor_id=user.id,
            actor_name=_display_name(user),
            form_version=current_form_version,
        )
    except Exception as be:
        logger.error("BIDS mirror (URL) failed for study %s: %s", study_id, be)

    try:
        audit_change_both(
            scope="study",
            action="file_added",
            actor=_display_name(user),
            extra={
                "file_name": base,
                "url": url,
                "modalities": modalities,
                "subject_index": subject_index,
                "visit_index": visit_index,
                "ui_label": _norm_audit_label(audit_label),
                "has_diff": False,
                "diff_payload": None,
            },
            study_id=study_id,
            study_name=study.study_name,
            db=db,
            actor_id=user.id,
        )
    except Exception:
        pass

    return db_file


# -------------------- Share Links --------------------

def generate_token():
    return secrets.token_urlsafe(32)

@router.post("/share-link/", status_code=201)
def create_share_link(
    payload: schemas.ShareLinkCreate,
    request: Request,
    audit_label: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.profile.role not in ["Investigator", "Administrator", "Principal Investigator"]:
        raise HTTPException(status_code=403, detail="Not allowed")

    study = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == payload.study_id).first()
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")

    content = db.query(models.StudyContent).filter(models.StudyContent.study_id == payload.study_id).first()
    study_data = (content.study_data or {}) if content else {}
    selected_models = study_data.get("selectedModels") or []
    assignments = study_data.get("assignments") or []

    # Validate requested section ids
    requested_allowed_ids = _normalize_allowed_section_ids(getattr(payload, "allowed_section_ids", []) or [])

    # Build set of section ids that are actually assigned for this visit/group
    assigned_section_ids = set()
    v_idx = int(payload.visit_index)
    g_idx = int(payload.group_index)

    for m_idx, sec in enumerate(selected_models):
        if not isinstance(sec, dict):
            continue
        if bool(assignments[m_idx][v_idx][g_idx]) if (
            isinstance(assignments, list)
            and m_idx < len(assignments)
            and isinstance(assignments[m_idx], list)
            and v_idx < len(assignments[m_idx])
            and isinstance(assignments[m_idx][v_idx], list)
            and g_idx < len(assignments[m_idx][v_idx])
        ) else False:
            sec_id = str(sec.get("_id") or sec.get("id") or "").strip()
            if sec_id:
                assigned_section_ids.add(sec_id)

    # If frontend sent explicit list, enforce it is a subset of assigned sections.
    # If frontend sends nothing, default to all assigned sections.
    if requested_allowed_ids:
        invalid_ids = [sid for sid in requested_allowed_ids if sid not in assigned_section_ids]
        if invalid_ids:
            raise HTTPException(
                status_code=400,
                detail=f"Some selected sections are not assigned for this subject/visit/group: {', '.join(invalid_ids)}"
            )
        allowed_section_ids = requested_allowed_ids
    else:
        allowed_section_ids = sorted(assigned_section_ids)

    token = generate_token()
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

    try:
        audit_change_both(
            scope="study",
            action="share_link_created",
            actor=_display_name(current_user),
            extra={
                "permission": payload.permission,
                "max_uses": payload.max_uses,
                "expires_in_days": payload.expires_in_days,
                "allowed_section_ids": allowed_section_ids,
                "ui_label": _norm_audit_label(audit_label),
                "has_diff": False,
                "diff_payload": None,
            },
            study_id=payload.study_id,
            study_name=None,
            db=db,
            actor_id=current_user.id,
        )
    except Exception:
        pass

    frontend_base = os.getenv("FRONTEND_BASE_URL", "").rstrip("/")
    if not frontend_base:
        origin = (request.headers.get("origin") or "").rstrip("/")
        if origin:
            frontend_base = origin
    if not frontend_base:
        referer = request.headers.get("referer")
        if referer:
            p = urlparse(referer)
            frontend_base = f"{p.scheme}://{p.netloc}"
    if not frontend_base:
        scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
        host   = request.headers.get("x-forwarded-host", request.headers.get("host", request.url.netloc))
        frontend_base = f"{scheme}://{host}"

    link = f"{frontend_base}/shared/{token}"
    return {"token": token, "link": link}


@router.get("/shared-api/{token}", response_model=schemas.SharedFormAccessOut)
def access_shared_form(
    token: str,
    db: Session = Depends(get_db),
):
    access = (
        db.query(models.SharedFormAccess)
          .filter_by(token=token)
          .first()
    )
    if not access:
        raise HTTPException(404, "Link not found")
    if access.used_count >= access.max_uses:
        raise HTTPException(403, "Usage limit exceeded")
    if access.expires_at < datetime.utcnow():
        raise HTTPException(403, "Link expired")

    access.used_count += 1
    db.commit()

    content = (
        db.query(models.StudyContent)
        .filter_by(study_id=access.study_id)
        .first()
    )
    if not content:
        raise HTTPException(500, "Study content missing")

    metadata = (
        db.query(models.StudyMetadata)
        .filter_by(id=access.study_id)
        .first()
    )
    if not metadata:
        raise HTTPException(500, "Study metadata missing")

    if not content.study_data or not isinstance(content.study_data.get("assignments"), list):
        raise HTTPException(500, "Study assignments data is missing or invalid")

    filtered_study_data = _filter_shared_study_data_by_sections(
        content.study_data,
        access.allowed_section_ids,
    )

    return {
        "study_id":      access.study_id,
        "subject_index": access.subject_index,
        "visit_index":   access.visit_index,
        "group_index":   access.group_index,
        "permission":    access.permission,
        "allowed_section_ids": access.allowed_section_ids or [],
        "study": {
            "metadata": {
                "id": metadata.id,
                "study_name": metadata.study_name,
                "study_description": metadata.study_description,
                "created_by": metadata.created_by,
                "created_at": metadata.created_at,
                "updated_at": metadata.updated_at
            },
            "content": {
                "study_data": filtered_study_data
            }
        }
    }
# -------------------- Data Entry --------------------
def get_current_form_version(db: Session, study_id: int) -> int:
    return VersionManager.latest_writable_version(db, study_id)

@router.post("/studies/{study_id}/data", response_model=schemas.StudyDataEntryOut)
def save_study_data(
    study_id: int,
    payload: schemas.StudyDataEntryCreate,
    version: Optional[int] = Query(None, description="Ignored; data always saved to latest template version"),
    audit_label: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    study = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == study_id).first()
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")

    is_admin = getattr(getattr(current_user, "profile", None), "role", "") == "Administrator"
    is_owner = study.created_by == current_user.id
    if not (is_admin or is_owner):
        grant = db.query(models.StudyAccessGrant).filter_by(study_id=study_id, user_id=current_user.id).first()
        if not grant or not (grant.permissions or {}).get("add_data", False):
            raise HTTPException(status_code=403, detail="Not allowed to add data for this study")

    try:
        form_version = VersionManager.assert_latest_is_used(db, study_id, version)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

    # If same subject/visit/group already has data in THIS version, compute diff (else: no diff)
    prev_entry = (
        db.query(models.StudyEntryData)
          .filter_by(
              study_id=study_id,
              subject_index=payload.subject_index,
              visit_index=payload.visit_index,
              group_index=payload.group_index,
              form_version=form_version,
          )
          .order_by(models.StudyEntryData.id.desc())
          .first()
    )
    entry_diffs: List[Dict[str, Any]] = []
    if prev_entry is not None:
        try:
            entry_diffs = _compute_json_diff(_deepcopy_json(prev_entry.data or {}), _deepcopy_json(payload.data or {}))
        except Exception:
            entry_diffs = []

    content = db.query(models.StudyContent).filter(models.StudyContent.study_id == study_id).first()
    selected_models = ((content.study_data or {}).get("selectedModels") if content and isinstance(content.study_data, dict) else []) or []

    entry = models.StudyEntryData(
        study_id=study_id,
        subject_index=payload.subject_index,
        visit_index=payload.visit_index,
        group_index=payload.group_index,
        data=payload.data,
        skipped_required_flags=_flags_dict_to_list(payload.skipped_required_flags, selected_models),
        form_version=form_version
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    snapshot_study_after_change(
        db=db,
        study_id=entry.study_id,
        action="add_entry",
        entry_id=entry.id,
    )
    content = db.query(models.StudyContent).filter(models.StudyContent.study_id == study_id).first()
    if upsert_bids_dataset and content:
        try:
            upsert_bids_dataset(study_id=study.id, study_name=study.study_name,
                                study_description=study.study_description, study_data=content.study_data)
            db.query(models.StudyContent).filter(models.StudyContent.id == content.id).update({"study_data": content.study_data})
            db.commit()
            if write_entry_to_bids:
                write_entry_to_bids(
                    study_id=study.id,
                    study_name=study.study_name,
                    study_description=study.study_description,
                    study_data=content.study_data,
                    entry={
                        "id": entry.id,
                        "subject_index": entry.subject_index,
                        "visit_index": entry.visit_index,
                        "group_index": entry.group_index,
                        "form_version": entry.form_version,
                        "data": entry.data or {}
                    },
                    actor=_display_name(current_user),
                    db=db,
                    actor_id=current_user.id,
                    actor_name=_display_name(current_user),
                )

            # Diff only if prev_entry existed (and diffs exist). For first-time subject data -> no diff.
            try:
                audit_change_both(
                    scope="study",
                    action="entry_upserted",
                    actor=_display_name(current_user),
                    extra={
                        "entry_id": entry.id,
                        "subject_index": entry.subject_index,
                        "visit_index": entry.visit_index,
                        "group_index": entry.group_index,
                        "form_version": entry.form_version,
                        "ui_label": _norm_audit_label(audit_label),
                        "has_diff": bool(entry_diffs),
                        "diff_payload": entry_diffs if entry_diffs else None,
                        "diff_kind": "entry_data",
                        "diff_basis": "previous_entry" if prev_entry is not None else "none",
                        "previous_entry_id": prev_entry.id if prev_entry is not None else None,
                    },
                    study_id=study.id,
                    study_name=study.study_name,
                    db=db,
                    actor_id=current_user.id
                )
            except Exception:
                pass

        except Exception as be:
            logger.error("BIDS export (data save) failed for study %s: %s", study_id, be)

    return entry


@router.put("/studies/{study_id}/data_entries/{entry_id}", response_model=schemas.StudyDataEntryOut)
def update_study_data_entry(
    study_id: int,
    entry_id: int,
    payload: schemas.StudyDataEntryCreate,
    audit_label: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    entry = (
        db.query(models.StudyEntryData)
          .filter_by(id=entry_id, study_id=study_id)
          .first()
    )
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    # Compute diff vs existing entry row
    entry_diffs: List[Dict[str, Any]] = []
    try:
        entry_diffs = _compute_json_diff(_deepcopy_json(entry.data or {}), _deepcopy_json(payload.data or {}))
    except Exception:
        entry_diffs = []

    entry.subject_index = payload.subject_index
    entry.visit_index   = payload.visit_index
    entry.group_index   = payload.group_index
    entry.data          = payload.data
    if payload.skipped_required_flags is not None:
        content = db.query(models.StudyContent).filter(models.StudyContent.study_id == study_id).first()
        selected_models = ((content.study_data or {}).get("selectedModels") if content and isinstance(content.study_data, dict) else []) or []
        entry.skipped_required_flags = _flags_dict_to_list(payload.skipped_required_flags, selected_models)
    db.commit()
    db.refresh(entry)
    snapshot_study_after_change(
        db=db,
        study_id=entry.study_id,
        action="upsert_entry",
        entry_id=entry.id,
    )
    study = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == study_id).first()
    content = db.query(models.StudyContent).filter(models.StudyContent.study_id == study_id).first()
    if upsert_bids_dataset and study and content:
        try:
            upsert_bids_dataset(
                study_id=study.id,
                study_name=study.study_name,
                study_description=study.study_description,
                study_data=content.study_data,
            )
            db.query(models.StudyContent).filter(models.StudyContent.id == content.id).update({"study_data": content.study_data})
            db.commit()

            if write_entry_to_bids:
                write_entry_to_bids(
                    study_id=study.id,
                    study_name=study.study_name,
                    study_description=study.study_description,
                    study_data=content.study_data,
                    entry={
                        "id": entry.id,
                        "subject_index": entry.subject_index,
                        "visit_index": entry.visit_index,
                        "group_index": entry.group_index,
                        "form_version": entry.form_version,
                        "data": entry.data or {}
                    },
                    actor=_display_name(user),
                    db=db,
                    actor_id=user.id,
                    actor_name=_display_name(user),
                )
                logger.info(
                    "BIDS eCRF upserted for study=%s sub_idx=%s visit_idx=%s entry_id=%s",
                    study.id, entry.subject_index, entry.visit_index, entry.id
                )
            # AUDIT: user edits data
            try:
                audit_change_both(
                    scope="study",
                    action="entry_upserted",
                    actor=_display_name(user),
                    extra={
                        "entry_id": entry.id,
                        "subject_index": entry.subject_index,
                        "visit_index": entry.visit_index,
                        "group_index": entry.group_index,
                        "form_version": entry.form_version,
                        "ui_label": _norm_audit_label(audit_label),
                        "has_diff": bool(entry_diffs),
                        "diff_payload": entry_diffs if entry_diffs else None,
                        "diff_kind": "entry_data",
                        "diff_basis": "same_entry_row",
                        "previous_entry_id": entry_id,
                    },
                    study_id=study.id,
                    study_name=study.study_name,
                    db=db,
                    actor_id=user.id,
                )
            except Exception:
                pass
        except Exception as be:
            logger.error("BIDS export (data update) failed for study %s: %s", study_id, be)

    return entry


@router.get("/studies/{study_id}/data_entries", response_model=schemas.PaginatedStudyDataEntries)
def list_study_data_entries(
    study_id: int,
    subject_indexes: Optional[str] = Query(None, description="Comma-separated subject indexes for current page"),
    visit_indexes: Optional[str] = Query(None, description="Comma-separated visit indexes for current page"),
    all: bool = Query(False, description="Return all entries for the study"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    exists = db.query(models.StudyMetadata).filter_by(id=study_id).first()
    if not exists:
        raise HTTPException(404, "Study not found")

    q = (
        db.query(models.StudyEntryData)
          .filter_by(study_id=study_id)
          .order_by(
              models.StudyEntryData.subject_index.asc(),
              models.StudyEntryData.visit_index.asc(),
              models.StudyEntryData.group_index.asc(),
              models.StudyEntryData.id.asc()
          )
    )

    total = q.count()

    if not all:
        if subject_indexes:
            subj_idx_list = [int(s) for s in subject_indexes.split(",") if s.strip().isdigit()]
            if subj_idx_list:
                q = q.filter(models.StudyEntryData.subject_index.in_(subj_idx_list))

        if visit_indexes:
            visit_idx_list = [int(s) for s in visit_indexes.split(",") if s.strip().isdigit()]
            if visit_idx_list:
                q = q.filter(models.StudyEntryData.visit_index.in_(visit_idx_list))

    entries = q.all()
    entries_out = [schemas.StudyDataEntryOut.from_orm(e) for e in entries]
    return {"total": total, "entries": entries_out}


@router.get("/shared-api/{token}/", response_model=schemas.SharedFormAccessOut)
def access_shared_form_slash(token: str, db: Session = Depends(get_db)):
    return access_shared_form(token, db)

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
        raise HTTPException(404, "Link not found")
    if access.used_count >= access.max_uses:
        raise HTTPException(403, "Usage limit exceeded")
    if access.expires_at < datetime.utcnow():
        raise HTTPException(403, "Link expired")
    if access.permission != "add":
        raise HTTPException(403, "Not allowed")

    study = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == access.study_id).first()
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")

    try:
        modalities = json.loads(modalities_json or "[]")
        if not isinstance(modalities, list):
            modalities = []
    except Exception:
        modalities = []

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, prefix=f"ecrf_study{study.id}_", suffix=f"_{uploaded_file.filename}") as tmp:
            shutil.copyfileobj(uploaded_file.file, tmp)
            tmp_path = tmp.name

        content = db.query(models.StudyContent).filter(models.StudyContent.study_id == study.id).first()
        study_data = content.study_data if content else {}

        current_form_version = VersionManager.latest_writable_version(db, study.id)

        stage_file_for_modalities(
            study_id=study.id,
            study_name=study.study_name,
            study_description=study.study_description,
            study_data=study_data,
            subject_index=access.subject_index,
            visit_index=access.visit_index,
            modalities=modalities,
            source_path=tmp_path,
            url=None,
            filename=uploaded_file.filename,
            actor="Shared link upload",
            db=db,
            actor_id=None,
            actor_name=None,
            form_version=current_form_version,
        )

        file_data = schemas.FileCreate(
            study_id=study.id,
            file_name=uploaded_file.filename,
            file_path=uploaded_file.filename,
            description=description,
            storage_option="bids",
            subject_index=access.subject_index,
            visit_index=access.visit_index,
            group_index=access.group_index,
        )
        db_file = crud.create_file(db, file_data)

        # AUDIT: share link file addition
        try:
            audit_change_both(
                scope="study",
                action="share_file_added",
                actor="",
                extra={
                    "file_name": uploaded_file.filename,
                    "modalities": modalities,
                    "subject_index": access.subject_index,
                    "visit_index": access.visit_index,
                    "ui_label": _norm_audit_label(audit_label),
                    "has_diff": False,
                    "diff_payload": None,
                },
                study_id=study.id,
                study_name=study.study_name,
                db=db,
                actor_id=None,
            )
        except Exception:
            pass

        return db_file
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Shared upload error: %s", e)
        raise HTTPException(status_code=500, detail="Error staging file to BIDS")
    finally:
        try:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass


@router.post("/shared/{token}/files/url", response_model=schemas.FileOut)
def shared_create_url_file(
    token: str,
    url: str = Form(...),
    description: str = Form(""),
    modalities_json: Optional[str] = Form("[]"),
    audit_label: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    access = (
        db.query(models.SharedFormAccess)
        .filter_by(token=token)
        .first()
    )
    if not access:
        raise HTTPException(404, "Link not found")
    if access.used_count >= access.max_uses:
        raise HTTPException(403, "Usage limit exceeded")
    if access.expires_at < datetime.utcnow():
        raise HTTPException(403, "Link expired")
    if access.permission != "add":
        raise HTTPException(403, "Not allowed")

    study = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == access.study_id).first()
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")

    try:
        modalities = json.loads(modalities_json or "[]")
        if not isinstance(modalities, list):
            modalities = []
    except Exception:
        modalities = []

    try:
        parsed = urlparse(url)
        base = os.path.splitext(os.path.basename(parsed.path) or "link")[0]
        file_data = schemas.FileCreate(
            study_id=study.id,
            file_name=base,
            file_path=url,
            description=description,
            storage_option="url",
            subject_index=access.subject_index,
            visit_index=access.visit_index,
            group_index=access.group_index,
        )
        db_file = crud.create_file(db, file_data)
    except Exception as e:
        logger.error("Shared URL file record error: %s", e)
        raise HTTPException(status_code=500, detail="Error creating file record")

    try:
        content = db.query(models.StudyContent).filter(models.StudyContent.study_id == study.id).first()
        study_data = content.study_data if content else {}

        current_form_version = VersionManager.latest_writable_version(db, study.id)

        stage_file_for_modalities(
            study_id=study.id,
            study_name=study.study_name,
            study_description=study.study_description,
            study_data=study_data,
            subject_index=access.subject_index,
            visit_index=access.visit_index,
            modalities=modalities,
            source_path=None,
            url=url,
            filename=base,
            actor="Shared link URL",
            db=db,
            actor_id=None,
            actor_name=None,
            form_version=current_form_version,
        )
    except Exception as be:
        logger.error("Shared BIDS mirror (URL) failed for study %s: %s", study.id, be)

    try:
        audit_change_both(
            scope="study",
            action="share_file_added",
            actor="",
            extra={
                "file_name": base,
                "url": url,
                "modalities": modalities,
                "subject_index": access.subject_index,
                "visit_index": access.visit_index,
                "ui_label": _norm_audit_label(audit_label),
                "has_diff": False,
                "diff_payload": None,
            },
            study_id=study.id,
            study_name=study.study_name,
            db=db,
            actor_id=None,
        )
    except Exception:
        pass

    return db_file


@router.post("/shared/{token}/data", response_model=schemas.StudyDataEntryOut)
def shared_upsert_data(
    token: str,
    payload: schemas.SharedStudyDataEntryCreate,
    version: Optional[int] = Query(None, description="Ignored; data always saved to latest template version"),
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

    study_id = access.study_id
    s, v, g = access.subject_index, access.visit_index, access.group_index

    try:
        form_version = VersionManager.assert_latest_is_used(db, study_id, version)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

    content = db.query(models.StudyContent).filter(models.StudyContent.study_id == study_id).first()
    selected_models = ((content.study_data or {}).get("selectedModels") if content and isinstance(content.study_data, dict) else []) or []

    # Enforce allowed sections for shared link
    _validate_shared_payload_sections(
        payload_data=payload.data or {},
        study_data=content.study_data if content else {},
        allowed_section_ids=access.allowed_section_ids or [],
    )

    # Idempotent within latest only: update if a row for this (s,v,g,latest) exists, else insert
    entry = (
        db.query(models.StudyEntryData)
          .filter_by(study_id=study_id, subject_index=s, visit_index=v, group_index=g, form_version=form_version)
          .order_by(models.StudyEntryData.id.desc())
          .first()
    )

    entry_diffs: List[Dict[str, Any]] = []
    if entry:
        try:
            entry_diffs = _compute_json_diff(_deepcopy_json(entry.data or {}), _deepcopy_json(payload.data or {}))
        except Exception:
            entry_diffs = []

    if entry:
        entry.data = payload.data
        entry.skipped_required_flags = _flags_dict_to_list(payload.skipped_required_flags, selected_models)
        db.commit()
        db.refresh(entry)
        prev_entry_id = entry.id
        basis = "previous_entry"
    else:
        entry = models.StudyEntryData(
            study_id=study_id,
            subject_index=s,
            visit_index=v,
            group_index=g,
            data=payload.data,
            skipped_required_flags=_flags_dict_to_list(payload.skipped_required_flags, selected_models),
            form_version=form_version
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        prev_entry_id = None
        basis = "none"
        entry_diffs = []

    study = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == study_id).first()
    content = db.query(models.StudyContent).filter(models.StudyContent.study_id == study_id).first()
    if upsert_bids_dataset and study and content:
        try:
            upsert_bids_dataset(study_id=study.id, study_name=study.study_name,
                                study_description=study.study_description, study_data=content.study_data)
            db.query(models.StudyContent).filter(models.StudyContent.id == content.id).update({"study_data": content.study_data})
            db.commit()
            if write_entry_to_bids:
                write_entry_to_bids(
                    study_id=study.id, study_name=study.study_name, study_description=study.study_description,
                    study_data=content.study_data,
                    entry={
                        "id": entry.id,
                        "subject_index": entry.subject_index,
                        "visit_index": entry.visit_index,
                        "group_index": entry.group_index,
                        "form_version": entry.form_version,
                        "data": entry.data or {}
                    },
                    actor="Shared link submit", db=db, actor_id=None, actor_name=None,
                )
            try:
                audit_change_both(
                    scope="study",
                    action="share_entry_upserted",
                    actor="",
                    extra={
                        "entry_id": entry.id,
                        "subject_index": entry.subject_index,
                        "visit_index": entry.visit_index,
                        "group_index": entry.group_index,
                        "form_version": entry.form_version,
                        "allowed_section_ids": access.allowed_section_ids or [],
                        "ui_label": _norm_audit_label(audit_label),
                        "has_diff": bool(entry_diffs),
                        "diff_payload": entry_diffs if entry_diffs else None,
                        "diff_kind": "entry_data",
                        "diff_basis": basis,
                        "previous_entry_id": prev_entry_id,
                    },
                    study_id=study.id,
                    study_name=study.study_name,
                    db=db,
                    actor_id=None
                )
            except Exception:
                pass
        except Exception as be:
            logger.error("BIDS export (shared data) failed for study %s: %s", study_id, be)

    return entry
# -------------------- Study Access Management --------------------

@router.get("/studies/{study_id}/access", response_model=List[schemas.StudyAccessGrantOut])
def list_study_access(
    study_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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


@router.post("/studies/{study_id}/access", response_model=schemas.StudyAccessGrantOut, status_code=201)
def grant_study_access(
    study_id: int,
    payload: schemas.StudyAccessGrantCreate,
    audit_label: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    meta = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == study_id).first()
    if not meta:
        raise HTTPException(status_code=404, detail="Study not found")
    _assert_owner_or_admin(meta, current_user)

    if payload.user_id == meta.created_by:
        raise HTTPException(status_code=400, detail="Owner already has full access")

    grantee = db.query(models.User).filter(models.User.id == payload.user_id).first()
    if not grantee:
        raise HTTPException(status_code=404, detail="User not found")

    perms = payload.permissions or {"view": True, "add_data": True, "edit_study": False}

    grant = db.query(models.StudyAccessGrant).filter_by(study_id=study_id, user_id=payload.user_id).first()
    if grant:
        grant.permissions = perms
        action = "access_updated"
    else:
        grant = models.StudyAccessGrant(
            study_id=study_id,
            user_id=payload.user_id,
            permissions=perms,
            created_by=current_user.id,
        )
        db.add(grant)
        action = "access_granted"
    db.commit()
    db.refresh(grant)

    try:
        audit_access_change_both(
            study_id=meta.id,
            study_name=meta.study_name,
            action=action,
            actor_id=current_user.id,
            actor_name=_display_name(current_user),
            target_user_id=grantee.id,
            target_user_email=grantee.email or "",
            target_user_display=_display_name(grantee),
            permissions=grant.permissions,
        )
    except Exception:
        pass

    granter = grant.granted_by
    return schemas.StudyAccessGrantOut(
        user_id=grantee.id,
        role=getattr(getattr(grantee, "profile", None), "role", None),
        email=grantee.email,
        username=grantee.username,
        display_name=_display_name(grantee),
        created_by=grant.created_by,
        created_by_display=_display_name(granter) if granter else None,
        created_at=grant.created_at,
        permissions=grant.permissions,
    )


@router.delete("/studies/{study_id}/access/{user_id}", status_code=204)
def revoke_study_access(
    study_id: int,
    user_id: int,
    audit_label: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    meta = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == study_id).first()
    if not meta:
        raise HTTPException(status_code=404, detail="Study not found")
    _assert_owner_or_admin(meta, current_user)

    if user_id == meta.created_by:
        raise HTTPException(status_code=400, detail="Cannot revoke owner access")

    grant = db.query(models.StudyAccessGrant).filter_by(study_id=study_id, user_id=user_id).first()
    if not grant:
        return

    perms_snapshot = grant.permissions or {}
    grantee = db.query(models.User).filter(models.User.id == user_id).first()

    db.delete(grant)
    db.commit()

    try:
        audit_access_change_both(
            study_id=meta.id,
            study_name=meta.study_name,
            action="access_revoked",
            actor_id=current_user.id,
            actor_name=_display_name(current_user),
            target_user_id=user_id,
            target_user_email=(grantee.email if grantee else "") or "",
            target_user_display=_display_name(grantee) if grantee else f"User#{user_id}",
            permissions=perms_snapshot,
        )
    except Exception:
        pass


@router.post("/studies/{study_id}/data/bulk")
def bulk_insert_data(
    study_id: int,
    payload: BulkPayload,
    version: Optional[int] = Query(None, description="Ignored; bulk inserts always use the latest template version"),
    create_bids: bool = Query(True, description="If false, skip BIDS folder creation/mirroring for this request"),
    audit_label: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    if not payload.entries:
        return {"inserted": 0, "failed": 0, "errors": []}

    try:
        form_version = VersionManager.assert_latest_is_used(db, study_id, version)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

    now = local_now()
    rows = []
    for e in payload.entries:
        rows.append({
            "study_id": study_id,
            "form_version": form_version,
            "subject_index": int(e.subject_index),
            "visit_index": int(e.visit_index),
            "group_index": int(e.group_index),
            "data": json.dumps(e.data, ensure_ascii=False),
            "created_at": now,
            "skipped_required_flags": json.dumps(e.skipped_required_flags or [], ensure_ascii=False),
        })

    sql = text("""
        INSERT INTO study_entry_data
          (study_id, form_version, subject_index, visit_index, group_index, data, created_at, skipped_required_flags)
        VALUES (:study_id, :form_version, :subject_index, :visit_index, :group_index, :data, :created_at, :skipped_required_flags)
    """)

    try:
        db.execute(sql, rows)
        db.commit()
    except Exception as ex:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Bulk insert failed: {ex}")

    inserted_count = len(rows)

    # allow skipping BIDS mirroring for performance (Windows) ----
    if not create_bids:
        return {"inserted": inserted_count, "failed": 0, "errors": []}

    # Load study context for BIDS
    study = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == study_id).first()
    content = db.query(models.StudyContent).filter(models.StudyContent.study_id == study_id).first()
    if not study or not content:
        return {"inserted": inserted_count, "failed": 0, "errors": []}

    # Re-select just-inserted rows for this request, then one batched BIDS write
    just_inserted = (
        db.query(models.StudyEntryData)
          .filter(models.StudyEntryData.study_id == study_id, models.StudyEntryData.form_version == form_version)
          .order_by(models.StudyEntryData.id.asc())
          .all()
    )

    def _json_or_passthrough(x):
        if isinstance(x, (dict, list)):
            return x
        try:
            return json.loads(x)
        except Exception:
            return x

    entries_for_bids = []
    for r in just_inserted:
        entries_for_bids.append({
            "id": r.id,
            "subject_index": int(r.subject_index),
            "visit_index": int(r.visit_index),
            "group_index": int(r.group_index),
            "form_version": int(r.form_version),
            "data": _json_or_passthrough(r.data) or {},
            "skipped_required_flags": _json_or_passthrough(r.skipped_required_flags) or [],
        })

    try:
        upsert_bids_dataset(
            study_id=study.id,
            study_name=study.study_name,
            study_description=study.study_description,
            study_data=content.study_data or {},
        )
    except Exception:
        pass

    try:
        bulk_write_entries_to_bids(
            study_id=study.id,
            study_name=study.study_name,
            study_description=study.study_description,
            study_data=content.study_data or {},
            entries=entries_for_bids,
            form_version=form_version,
            db=db,
            actor="Bulk import",
        )

        try:
            audit_change_both(
                scope="study",
                action="bulk_entry_upserted",
                actor="Bulk import",
                extra={
                    "inserted": inserted_count,
                    "form_version": form_version,
                    "ui_label": _norm_audit_label(audit_label),
                    "has_diff": False,
                    "diff_payload": None,
                },
                study_id=study.id,
                study_name=study.study_name,
                db=db,
                actor_id=None
            )
        except Exception:
            pass

    except Exception as be:
        return {"inserted": inserted_count, "failed": inserted_count, "errors": [f"BIDS mirror failed: {be}"]}

    return {"inserted": inserted_count, "failed": 0, "errors": []}

def _ensure_can_see_bids(current_user: models.User, study: models.StudyMetadata) -> None:
    """
    Only study owner or admins can see/open the BIDS dataset.
    Adjust this to your own role logic if needed.
    """
    role = (getattr(getattr(current_user, "profile", None), "role", "") or "").strip().lower()
    is_admin = role == "administrator"
    is_owner = current_user.id == study.created_by

    if not (is_admin or is_owner):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view the BIDS dataset for this study.",
        )


@router.get("/studies/{study_id}/bids_path")
def get_study_bids_path(
    study_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Return the absolute BIDS dataset path for this study.
    Only visible to study owner and admins.
    """
    # was: study = crud.get_study_by_id(db, study_id)
    study = (
        db.query(models.StudyMetadata)
        .filter(models.StudyMetadata.id == study_id)
        .first()
    )

    if not study:
        raise HTTPException(status_code=404, detail="Study not found")

    _ensure_can_see_bids(current_user, study)

    dataset_path = _dataset_path(study.id, study.study_name or "")
    return {"dataset_path": dataset_path, "exists": os.path.isdir(dataset_path)}

@router.post("/studies/{study_id}/bids_open", status_code=204)
def open_study_bids_folder(
    study_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Opens the BIDS dataset folder for this study in the OS file explorer.
    Only allowed for study owner and admins.
    """
    # was: study = crud.get_study_by_id(db, study_id)
    study = (
        db.query(models.StudyMetadata)
        .filter(models.StudyMetadata.id == study_id)
        .first()
    )

    if not study:
        raise HTTPException(status_code=404, detail="Study not found")

    _ensure_can_see_bids(current_user, study)

    dataset_path = _dataset_path(study.id, study.study_name or "")
    if not os.path.isdir(dataset_path):
        raise HTTPException(status_code=404, detail="BIDS dataset directory does not exist yet")

    system = platform.system()
    if system == "Darwin":
        cmd = ["open", dataset_path]
    elif system == "Windows":
        cmd = ["explorer", dataset_path]
    else:
        cmd = ["xdg-open", dataset_path]

    try:
        subprocess.Popen(cmd)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to open BIDS folder: {e}")

    return


@router.delete("/studies/{study_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_study(
    study_id: int,
    include_drafts: bool = Query(True, description="If true, also delete any drafts (DRAFT/ARCHIVED) whose draft_of_study_id == this study_id"),
    delete_bids: bool = Query(True, description="If true, also delete the BIDS dataset folder from disk (best-effort)."),
    audit_label: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    meta = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == study_id).first()
    if not meta:
        raise HTTPException(status_code=404, detail="Study not found")

    _assert_owner_or_admin(meta, current_user)

    ids_to_delete = [int(study_id)]

    if include_drafts:
        draft_rows = db.query(models.StudyMetadata.id).filter(models.StudyMetadata.draft_of_study_id == study_id).all()
        for (did,) in draft_rows:
            did_int = int(did)
            if did_int not in ids_to_delete:
                ids_to_delete.append(did_int)

    bids_targets = []
    if delete_bids:
        metas = db.query(models.StudyMetadata.id, models.StudyMetadata.study_name).filter(models.StudyMetadata.id.in_(ids_to_delete)).all()
        bids_targets = [(int(i), (n or "")) for (i, n) in metas]

    FileModel = getattr(models, "File", None)
    SharedModel = getattr(models, "SharedFormAccess", None)

    try:
        db.query(models.StudyEntryData).filter(models.StudyEntryData.study_id.in_(ids_to_delete)).delete(synchronize_session=False)

        if FileModel is not None:
            db.query(FileModel).filter(FileModel.study_id.in_(ids_to_delete)).delete(synchronize_session=False)

        db.query(StudyTemplateVersion).filter(StudyTemplateVersion.study_id.in_(ids_to_delete)).delete(synchronize_session=False)
        db.query(models.StudyAccessGrant).filter(models.StudyAccessGrant.study_id.in_(ids_to_delete)).delete(synchronize_session=False)

        if SharedModel is not None:
            db.query(SharedModel).filter(SharedModel.study_id.in_(ids_to_delete)).delete(synchronize_session=False)

        db.query(models.StudyContent).filter(models.StudyContent.study_id.in_(ids_to_delete)).delete(synchronize_session=False)
        db.query(models.StudyMetadata).filter(models.StudyMetadata.id.in_(ids_to_delete)).delete(synchronize_session=False)

        db.commit()
    except Exception as e:
        db.rollback()
        logger.exception("Failed deleting study ids=%s: %s", ids_to_delete, e)
        raise HTTPException(status_code=500, detail="Failed to delete study")

    if delete_bids:
        for sid, sname in bids_targets:
            _delete_bids_folder_safe(sid, sname)

    try:
        audit_change_both(
            scope="study",
            action="study_deleted",
            actor=_display_name(current_user),
            extra={
                "study_id": study_id,
                "deleted_ids": ids_to_delete,
                "delete_bids": bool(delete_bids),
                "ui_label": _norm_audit_label(audit_label),
                "has_diff": False,
                "diff_payload": None,
            },
            study_id=study_id,
            study_name=None,
            db=db,
            actor_id=current_user.id,
        )
    except Exception:
        pass

    return