# eCRF_backend/forms.py
import os
import platform
import subprocess
import shutil
import tempfile
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse
import json
import yaml
import secrets
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import Request
from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File, Form, Body, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, text
from sqlalchemy.sql import func

from eCRF_backend.dts.crud_dts import (
    upsert_study_to_dts,
    upsert_study_entry_to_dts,
    list_study_entries_from_dts,
    get_study_entry_from_dts,
    upsert_study_file_to_dts,
    upsert_template_snapshot_to_dts,
    list_studies_from_dts,
    get_study_from_dts,
)
from eCRF_backend.dts.dts_client import DTSClient
from eCRF_backend.dts.dts_settings import DTS_COLLECTION
from eCRF_backend.dts.dts_mapping import study_pid

from .versions import VersionManager
from .database import get_db
from . import schemas, crud, models
from .bids_exporter import (
    upsert_bids_dataset,
    write_entry_to_bids,
    stage_file_for_modalities,
    audit_change_both,
    audit_access_change_both,
    log_dataset_change_to_changes,
    bump_bids_version,
    bulk_write_entries_to_bids,
    _dataset_path,
    _delete_bids_folder_safe,
)
from .logger import logger
from .models import User, StudyTemplateVersion
from .schemas import BulkPayload
from .users import get_current_user
from .utils import local_now

router = APIRouter(prefix="/forms", tags=["forms"])

TEMPLATE_DIR = Path(os.environ.get("ECRF_TEMPLATES_DIR", "")) if os.environ.get("ECRF_TEMPLATES_DIR") \
    else (Path(__file__).resolve().parent / "templates")

ALLOWED_STUDY_STATUS = {"DRAFT", "PUBLISHED", "ARCHIVED"}
_DEFAULT_GRANT_PERMS = {"view": True, "add_data": True, "edit_study": False}


# -------------------------------------------------------------------
# DTS sync helpers (always-on in this file)
# -------------------------------------------------------------------

def _sync_template_snapshot_to_dts_safe(
    study_id: int,
    version_row: models.StudyTemplateVersion,
    context: str = "",
) -> None:
    try:
        upsert_template_snapshot_to_dts(study_id=study_id, version_row=version_row)
        logger.info(
            "DTS template snapshot sync successful study_id=%s version=%s context=%s",
            study_id,
            getattr(version_row, "version", None),
            context,
        )
    except Exception as e:
        logger.error(
            "DTS template snapshot sync failed study_id=%s version=%s context=%s err=%s",
            study_id,
            getattr(version_row, "version", None),
            context,
            e,
        )
        raise


def _sync_study_file_to_dts_safe(
    study: models.StudyMetadata,
    content: models.StudyContent,
    db_file: models.File,
    context: str = "",
) -> None:
    try:
        upsert_study_file_to_dts(study=study, content=content, db_file=db_file)
        logger.info(
            "DTS study file sync successful study_id=%s file_id=%s context=%s",
            study.id,
            getattr(db_file, "id", None),
            context,
        )
    except Exception as e:
        logger.error(
            "DTS study file sync failed study_id=%s file_id=%s context=%s err=%s",
            getattr(study, "id", None),
            getattr(db_file, "id", None),
            context,
            e,
        )
        raise


def _sync_study_entry_to_dts_safe(
    study: models.StudyMetadata,
    content: models.StudyContent,
    entry: models.StudyEntryData,
    actor_id: Optional[int] = None,
    actor_name: Optional[str] = None,
    context: str = "",
) -> None:
    try:
        upsert_study_entry_to_dts(
            study=study,
            content=content,
            entry=entry,
            actor_id=actor_id,
            actor_name=actor_name,
        )
        logger.info(
            "DTS study entry sync successful study_id=%s entry_id=%s context=%s",
            study.id,
            getattr(entry, "id", None),
            context,
        )
    except Exception as e:
        logger.error(
            "DTS study entry sync failed study_id=%s entry_id=%s context=%s err=%s",
            getattr(study, "id", None),
            getattr(entry, "id", None),
            context,
            e,
        )
        raise


def _latest_template_snapshot_info(db: Session, study_id: int) -> tuple[Optional[int], Optional[datetime]]:
    row = (
        db.query(models.StudyTemplateVersion)
        .filter(models.StudyTemplateVersion.study_id == study_id)
        .order_by(models.StudyTemplateVersion.version.desc())
        .first()
    )
    if not row:
        return None, None
    return int(row.version), row.created_at


def _sync_study_to_dts_safe(
    db: Session,
    metadata: models.StudyMetadata,
    content: models.StudyContent,
    context: str = "",
) -> None:
    try:
        current_template_version, template_snapshot_created_at = _latest_template_snapshot_info(db, metadata.id)
        upsert_study_to_dts(
            metadata,
            content,
            current_template_version=current_template_version,
            template_snapshot_created_at=template_snapshot_created_at,
        )
        logger.info(
            "DTS study sync successful study_id=%s context=%s version=%s",
            metadata.id,
            context,
            current_template_version,
        )
    except Exception as e:
        logger.error(
            "DTS study sync failed study_id=%s context=%s err=%s",
            getattr(metadata, "id", None),
            context,
            e,
        )
        raise


# -------------------------------------------------------------------
# General helpers
# -------------------------------------------------------------------

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


def _deepcopy_json(obj):
    try:
        return json.loads(json.dumps(obj, ensure_ascii=False))
    except Exception:
        return {}


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


def _validate_shared_payload_sections(
    payload_data: Dict[str, Any],
    study_data: Dict[str, Any],
    allowed_section_ids: Optional[List[str]],
) -> None:
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


def _effective_study_permissions(db: Session, meta: Any, user: models.User) -> Dict[str, bool]:
    if _is_admin(user) or getattr(meta, "created_by", None) == user.id:
        return {"view": True, "add_data": True, "edit_study": True}

    grant = (
        db.query(models.StudyAccessGrant)
          .filter(
              models.StudyAccessGrant.study_id == getattr(meta, "id", None),
              models.StudyAccessGrant.user_id == user.id,
          )
          .first()
    )
    if not grant:
        return {"view": False, "add_data": False, "edit_study": False}

    perms = grant.permissions or {}
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


def _assert_has_study_permission(db: Session, meta: Any, user: models.User, required: str = "view"):
    role = (getattr(getattr(user, "profile", None), "role", "") or "").strip()
    is_admin = role == "Administrator"
    is_owner = (getattr(meta, "created_by", None) == user.id)

    if is_admin or is_owner:
        return {"view": True, "add_data": True, "edit_study": True}

    grant = _get_grant(db, getattr(meta, "id", None), user.id)
    perms = (grant.permissions or {}) if grant else {}

    if not perms.get(required, False):
        raise HTTPException(status_code=403, detail="Not authorized")

    return perms


def _norm_status(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    s2 = str(s).strip().upper()
    return s2 if s2 in ALLOWED_STUDY_STATUS else None


def _get_meta_status(meta: Any) -> str:
    return (getattr(meta, "status", None) or "PUBLISHED").strip().upper()


def _is_publish_transition(old_status: str, new_status: str) -> bool:
    return old_status != "PUBLISHED" and new_status == "PUBLISHED"


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


def _coerce_snapshot_schema(raw):
    snap = _deepcopy_json(raw if isinstance(raw, dict) else {})
    if "study" not in snap or not isinstance(snap.get("study"), dict):
        title = snap.get("title") if isinstance(snap.get("title"), str) else ""
        description = snap.get("description") if isinstance(snap.get("description"), str) else ""
        snap["study"] = {"title": title, "description": description}

    def _norm_name_list(key):
        items = snap.get(key, [])
        if isinstance(items, list):
            norm = []
            for it in items:
                if isinstance(it, str):
                    norm.append({"name": it})
                elif isinstance(it, dict):
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

    if "selectedModels" not in snap and isinstance(snap.get("models"), list):
        snap["selectedModels"] = [
            ({"title": m} if isinstance(m, str) else m) for m in snap["models"]
        ]

    return snap


def _assert_owner_or_admin(meta: Any, user) -> None:
    if getattr(meta, "created_by", None) != user.id and getattr(getattr(user, "profile", None), "role", None) != "Administrator":
        raise HTTPException(status_code=403, detail="Not authorized")


def _display_name(u: models.User) -> str:
    if not u:
        return ""
    first = getattr(getattr(u, "profile", None), "first_name", "") or ""
    last = getattr(getattr(u, "profile", None), "last_name", "") or ""
    full = (first + " " + last).strip()
    return full or u.username or u.email or f"User#{u.id}"


def _dts_study_full_response(study_id: int, db: Session, user: models.User) -> Dict[str, Any]:
    metadata, content = get_study_from_dts(study_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="Study not found")

    perms = _assert_has_study_permission(db, metadata, user, required="view")

    meta_out = {
        "id": int(metadata.id),
        "study_name": metadata.study_name,
        "study_description": metadata.study_description,
        "status": metadata.status,
        "draft_of_study_id": metadata.draft_of_study_id,
        "last_completed_step": metadata.last_completed_step,
        "created_by": metadata.created_by,
        "created_at": metadata.created_at,
        "updated_at": metadata.updated_at,
        "permissions": {
            "view": bool(perms.get("view", False)),
            "add_data": bool(perms.get("add_data", False)),
            "edit_study": bool(perms.get("edit_study", False)),
        },
    }

    content_out = {
        "id": int(metadata.id),  # avoids response validation failure on DTS shim content.id=None
        "study_id": int(metadata.id),
        "study_data": (content.study_data or {}) if content else {},
    }

    return {"metadata": meta_out, "content": content_out}


def _dts_entry_or_sql_fallback(study_id: int, entry_id: int, entry_obj: models.StudyEntryData) -> Dict[str, Any]:
    try:
        dts_entry = get_study_entry_from_dts(study_id, entry_id)
        if dts_entry:
            return dts_entry
    except Exception as e:
        logger.warning("DTS entry readback failed study_id=%s entry_id=%s: %s", study_id, entry_id, e)

    return {
        "id": entry_obj.id,
        "study_id": entry_obj.study_id,
        "form_version": entry_obj.form_version,
        "subject_index": entry_obj.subject_index,
        "visit_index": entry_obj.visit_index,
        "group_index": entry_obj.group_index,
        "data": entry_obj.data or {},
        "skipped_required_flags": entry_obj.skipped_required_flags,
        "created_at": entry_obj.created_at,
    }


# -------------------------------------------------------------------
# Available fields
# -------------------------------------------------------------------

@router.get("/available-fields")
async def get_available_fields():
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


# -------------------------------------------------------------------
# Study CRUD
# -------------------------------------------------------------------

@router.post("/studies/", response_model=schemas.StudyFull)
def create_study(
    study_metadata: schemas.StudyMetadataCreate,
    study_content: schemas.StudyContentCreate,
    create_bids: bool = Query(True, description="If false, skip BIDS dataset folder creation for this request"),
    status: Optional[str] = Query(None, description="Optional: DRAFT|PUBLISHED|ARCHIVED (defaults to PUBLISHED)"),
    draft_of_study_id: Optional[int] = Query(None, description="Optional: published study id if creating an edit-draft"),
    last_completed_step: Optional[int] = Query(None, description="Optional: resume helper"),
    audit_label: Optional[str] = Query(None, description="Optional: human-readable audit label from frontend"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    if study_metadata.created_by != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to create study for this user")

    desired_status = _norm_status(status) or "PUBLISHED"
    if desired_status == "DRAFT":
        create_bids = False

    if draft_of_study_id is not None:
        try:
            base_meta, _ = get_study_from_dts(draft_of_study_id)
        except Exception:
            base_meta = None

        if not base_meta:
            raise HTTPException(status_code=404, detail="draft_of_study_id study not found")

        if getattr(base_meta, "created_by", None) != user.id and getattr(user.profile, "role", None) != "Administrator":
            raise HTTPException(status_code=403, detail="Not authorized to draft-edit this study")

        desired_status = "DRAFT"

    incoming_snapshot = _deepcopy_json(study_content.study_data or {})

    try:
        metadata, content = crud.create_study(db, study_metadata, study_content)
    except Exception as e:
        logger.error("Error creating study: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

    try:
        metadata.status = desired_status
        metadata.draft_of_study_id = draft_of_study_id
        if last_completed_step is not None:
            metadata.last_completed_step = int(last_completed_step)
        db.commit()
        db.refresh(metadata)
        db.refresh(content)
    except Exception as e:
        db.rollback()
        logger.error("Error updating draft workflow fields: %s", e)
        raise HTTPException(status_code=500, detail="Error creating draft workflow fields")

    if create_bids and upsert_bids_dataset and _get_meta_status(metadata) != "DRAFT":
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
            logger.info("BIDS dataset initialized at %s (study_id=%s)", dataset_path, metadata.id)

            log_dataset_change_to_changes(
                metadata.id,
                metadata.study_name,
                action="dataset_initialized",
                actor_id=user.id,
                actor_name=_display_name(user),
                detail="Initial BIDS dataset creation"
            )

            try:
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

    try:
        VersionManager.ensure_initial_version(db, metadata.id, incoming_snapshot)
        latest_v_row = (
            db.query(models.StudyTemplateVersion)
            .filter(models.StudyTemplateVersion.study_id == metadata.id)
            .order_by(models.StudyTemplateVersion.version.desc())
            .first()
        )
        if latest_v_row:
            _sync_template_snapshot_to_dts_safe(
                study_id=metadata.id,
                version_row=latest_v_row,
                context="create_study:init_template_snapshot",
            )
    except Exception as ve:
        logger.error("Failed to init template version for study %s: %s", metadata.id, ve)
        raise HTTPException(status_code=500, detail="Failed to initialize template snapshot")

    try:
        _sync_study_to_dts_safe(
            db=db,
            metadata=metadata,
            content=content,
            context="create_study",
        )
    except Exception as de:
        raise HTTPException(status_code=500, detail=f"DTS sync failed during study creation: {de}")

    return _dts_study_full_response(metadata.id, db, user)


@router.get("/studies", response_model=List[schemas.StudyMetadataOut])
def list_studies(
    status: Optional[str] = Query(None, description="Optional: DRAFT|PUBLISHED|ARCHIVED"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    role = (getattr(getattr(current_user, "profile", None), "role", "") or "").strip()
    status_norm = _norm_status(status)

    try:
        dts_studies = list_studies_from_dts()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DTS list studies failed: {e}")

    out: List[schemas.StudyMetadataOut] = []

    for row in dts_studies:
        row_status = (row.get("status") or "PUBLISHED").strip().upper()
        if status_norm and row_status != status_norm:
            continue

        row_obj = type("DTSStudyMeta", (), row)()
        perms = _effective_study_permissions(db, row_obj, current_user)

        if role != "Administrator" and not perms.get("view", False):
            continue

        row["permissions"] = perms
        out.append(schemas.StudyMetadataOut(**row))

    return out


@router.get("/studies/{study_id}", response_model=schemas.StudyFull)
def read_study(
    study_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    try:
        return _dts_study_full_response(study_id, db, user)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DTS read failed: {e}")


@router.get("/studies/{study_id}/versions")
def list_study_versions(
    study_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    try:
        meta, _ = get_study_from_dts(study_id)
    except Exception:
        meta = None

    if not meta:
        raise HTTPException(status_code=404, detail="Study not found")

    perms = _effective_study_permissions(db, meta, user)
    if not perms.get("view", False):
        raise HTTPException(status_code=403, detail="Not authorized")

    versions = (
        db.query(StudyTemplateVersion)
          .filter(StudyTemplateVersion.study_id == study_id)
          .order_by(StudyTemplateVersion.version.asc())
          .all()
    )
    return [{"version": v.version, "created_at": v.created_at} for v in versions]


@router.get("/studies/{study_id}/template")
def get_template_version(
    study_id: int,
    version: Optional[int] = Query(None, description="If omitted, returns latest template schema"),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    try:
        meta, _ = get_study_from_dts(study_id)
    except Exception:
        meta = None

    if not meta:
        raise HTTPException(status_code=404, detail="Study not found")

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
    try:
        meta, content = get_study_from_dts(study_id)
    except Exception:
        meta, content = None, None

    if not meta:
        raise HTTPException(status_code=404, detail="Study not found")

    _assert_owner_or_admin(meta, user)

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
    user=Depends(get_current_user)
):
    # SQL row is still needed for versioning/audit/BIDS/shared access subsystems
    existing = crud.get_study_full(db, study_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Study not found")

    metadata, content = existing
    if metadata.created_by != user.id and user.profile.role != "Administrator":
        raise HTTPException(status_code=403, detail="Not authorized to update this study")

    if not study_content.study_data:
        study_content.study_data = {}

    if not study_content.study_data.get("id"):
        study_content.study_data["id"] = study_id

    old_status = _get_meta_status(metadata)
    incoming_status = _norm_status(getattr(study_metadata, "status", None)) or old_status

    if hasattr(study_metadata, "last_completed_step") and getattr(study_metadata, "last_completed_step", None) is not None:
        try:
            metadata.last_completed_step = int(getattr(study_metadata, "last_completed_step"))
            db.commit()
            db.refresh(metadata)
        except Exception:
            db.rollback()

    is_edit_draft = (getattr(metadata, "draft_of_study_id", None) is not None)
    publish_edit_draft = is_edit_draft and _is_publish_transition(old_status, incoming_status)
    ui_label = _norm_audit_label(audit_label)

    if publish_edit_draft:
        published_id = int(metadata.draft_of_study_id)

        try:
            crud.update_study(db, study_id, study_metadata, study_content)
        except Exception as e:
            logger.error("Error updating draft before publish: %s", e)
            raise HTTPException(status_code=500, detail=str(e))

        draft_meta, draft_content = crud.get_study_full(db, study_id)

        published_full = crud.get_study_full(db, published_id)
        if not published_full:
            raise HTTPException(status_code=404, detail="Published study not found for draft_of_study_id")

        pub_meta, pub_content = published_full
        if pub_meta.created_by != user.id and user.profile.role != "Administrator":
            raise HTTPException(status_code=403, detail="Not authorized to publish changes to this study")

        prev_v_row = (
            db.query(StudyTemplateVersion)
              .filter(StudyTemplateVersion.study_id == published_id)
              .order_by(StudyTemplateVersion.version.desc())
              .first()
        )
        prev_latest_v = int(prev_v_row.version) if prev_v_row else 1

        old_sd_published = _deepcopy_json(pub_content.study_data or {})
        new_sd_from_draft = _deepcopy_json(draft_content.study_data or {})
        new_sd_from_draft["id"] = published_id

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
            raise HTTPException(status_code=500, detail="Versioning failed during draft publish")

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

        if new_v_row:
            _sync_template_snapshot_to_dts_safe(
                study_id=published_id,
                version_row=new_v_row,
                context="update_study:latest_template_snapshot",
            )

        try:
            draft_meta.status = "ARCHIVED"
            db.commit()
            db.refresh(draft_meta)
        except Exception:
            db.rollback()

        try:
            _sync_study_to_dts_safe(
                db=db,
                metadata=pub_meta,
                content=pub_content,
                context="publish_edit_draft:published",
            )
        except Exception as de:
            raise HTTPException(status_code=500, detail=f"DTS sync failed during draft publish: {de}")

        try:
            draft_content_latest = db.query(models.StudyContent).filter(
                models.StudyContent.study_id == draft_meta.id
            ).first()
            if draft_content_latest:
                _sync_study_to_dts_safe(
                    db=db,
                    metadata=draft_meta,
                    content=draft_content_latest,
                    context="publish_edit_draft:archived_draft",
                )
        except Exception as de:
            raise HTTPException(status_code=500, detail=f"DTS sync failed while archiving draft: {de}")

        return _dts_study_full_response(pub_meta.id, db, user)

    old_sd = _deepcopy_json(content.study_data or {})

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

    try:
        if incoming_status:
            metadata.status = incoming_status
        db.commit()
        db.refresh(metadata)
        db.refresh(content)
    except Exception:
        db.rollback()

    if _get_meta_status(metadata) == "DRAFT":
        try:
            _sync_study_to_dts_safe(
                db=db,
                metadata=metadata,
                content=content,
                context="update_study:draft",
            )
        except Exception as de:
            raise HTTPException(status_code=500, detail=f"DTS sync failed during draft update: {de}")

        return _dts_study_full_response(metadata.id, db, user)

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
        VersionManager.apply_on_update(
            db,
            study_id,
            old_sd,
            _deepcopy_json(content.study_data or {}),
            audit_callback=_audit
        )
    except Exception as ve:
        logger.error("Versioning apply_on_update failed for study %s: %s", study_id, ve)
        raise HTTPException(status_code=500, detail="Versioning failed during study update")

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

    if new_v_row:
        _sync_template_snapshot_to_dts_safe(
            study_id=study_id,
            version_row=new_v_row,
            context="update_study:latest_template_snapshot",
        )

    try:
        _sync_study_to_dts_safe(
            db=db,
            metadata=metadata,
            content=content,
            context="update_study",
        )
    except Exception as de:
        raise HTTPException(status_code=500, detail=f"DTS sync failed during study update: {de}")

    return _dts_study_full_response(metadata.id, db, user)


# -------------------------------------------------------------------
# Files
# -------------------------------------------------------------------

@router.get("/studies/{study_id}/files", response_model=List[schemas.FileOut])
def read_files_for_study(
    study_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    try:
        meta, _ = get_study_from_dts(study_id)
    except Exception:
        meta = None

    if not meta:
        raise HTTPException(status_code=404, detail="Study not found")

    _assert_has_study_permission(db, meta, user, required="view")

    # still SQL-backed because no DTS list-file helper was provided
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

        if study and content and db_file:
            _sync_study_file_to_dts_safe(
                study=study,
                content=content,
                db_file=db_file,
                context="upload_file",
            )
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

    content = db.query(models.StudyContent).filter(models.StudyContent.study_id == study_id).first()
    if study and content and db_file:
        _sync_study_file_to_dts_safe(
            study=study,
            content=content,
            db_file=db_file,
            context="create_url_file",
        )
    return db_file


# -------------------------------------------------------------------
# Share links
# -------------------------------------------------------------------

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

    try:
        study_meta, study_content_shim = get_study_from_dts(payload.study_id)
    except Exception:
        study_meta, study_content_shim = None, None

    if not study_meta:
        raise HTTPException(status_code=404, detail="Study not found")

    study_data = (study_content_shim.study_data or {}) if study_content_shim else {}
    selected_models = study_data.get("selectedModels") or []
    assignments = study_data.get("assignments") or []

    requested_allowed_ids = _normalize_allowed_section_ids(getattr(payload, "allowed_section_ids", []) or [])

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
            study_name=getattr(study_meta, "study_name", None),
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
        host = request.headers.get("x-forwarded-host", request.headers.get("host", request.url.netloc))
        frontend_base = f"{scheme}://{host}"

    link = f"{frontend_base}/shared/{token}"
    return {"token": token, "link": link}


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

    try:
        metadata, content = get_study_from_dts(access.study_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DTS study read failed: {e}")

    if not metadata or not content:
        raise HTTPException(500, "Study data missing")

    filtered_study_data = _filter_shared_study_data_by_sections(
        content.study_data,
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
                "id": metadata.id,
                "study_name": metadata.study_name,
                "study_description": metadata.study_description,
                "created_by": metadata.created_by,
                "created_at": metadata.created_at,
                "updated_at": metadata.updated_at,
            },
            "content": {
                "study_data": filtered_study_data
            }
        }
    }


@router.get("/shared-api/{token}/", response_model=schemas.SharedFormAccessOut)
def access_shared_form_slash(token: str, db: Session = Depends(get_db)):
    return access_shared_form(token, db)


# -------------------------------------------------------------------
# Data entry
# -------------------------------------------------------------------

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
    try:
        study_meta, content_shim = get_study_from_dts(study_id)
    except Exception:
        study_meta, content_shim = None, None

    if not study_meta:
        raise HTTPException(status_code=404, detail="Study not found")

    perms = _effective_study_permissions(db, study_meta, current_user)
    if not perms.get("add_data", False):
        raise HTTPException(status_code=403, detail="Not allowed to add data for this study")

    try:
        form_version = VersionManager.assert_latest_is_used(db, study_id, version)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

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
    selected_models = ((content.study_data or {}).get("selectedModels") if content and isinstance(content.study_data, dict) else []) or \
                      ((content_shim.study_data or {}).get("selectedModels") if content_shim and isinstance(content_shim.study_data, dict) else []) or []

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

    if upsert_bids_dataset and content:
        try:
            upsert_bids_dataset(
                study_id=study_meta.id,
                study_name=study_meta.study_name,
                study_description=study_meta.study_description,
                study_data=content.study_data,
            )
            db.query(models.StudyContent).filter(models.StudyContent.id == content.id).update({"study_data": content.study_data})
            db.commit()

            if write_entry_to_bids:
                write_entry_to_bids(
                    study_id=study_meta.id,
                    study_name=study_meta.study_name,
                    study_description=study_meta.study_description,
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
                    study_id=study_meta.id,
                    study_name=study_meta.study_name,
                    db=db,
                    actor_id=current_user.id
                )
            except Exception:
                pass

        except Exception as be:
            logger.error("BIDS export (data save) failed for study %s: %s", study_id, be)

    if content is not None:
        try:
            _sync_study_entry_to_dts_safe(
                study=type("StudyObj", (), {"id": study_meta.id, "study_name": study_meta.study_name, "study_description": study_meta.study_description})(),
                content=content,
                entry=entry,
                actor_id=current_user.id,
                actor_name=_display_name(current_user),
                context="save_study_data",
            )
        except Exception as de:
            raise HTTPException(status_code=500, detail=f"DTS sync failed during save study data: {de}")

    return _dts_entry_or_sql_fallback(study_id, entry.id, entry)


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

    study_meta, _ = get_study_from_dts(study_id)
    perms = _effective_study_permissions(db, study_meta, user)
    if not perms.get("add_data", False):
        raise HTTPException(status_code=403, detail="Not allowed to update data for this study")

    entry_diffs: List[Dict[str, Any]] = []
    try:
        entry_diffs = _compute_json_diff(_deepcopy_json(entry.data or {}), _deepcopy_json(payload.data or {}))
    except Exception:
        entry_diffs = []

    entry.subject_index = payload.subject_index
    entry.visit_index = payload.visit_index
    entry.group_index = payload.group_index
    entry.data = payload.data

    if payload.skipped_required_flags is not None:
        content = db.query(models.StudyContent).filter(models.StudyContent.study_id == study_id).first()
        selected_models = ((content.study_data or {}).get("selectedModels") if content and isinstance(content.study_data, dict) else []) or []
        entry.skipped_required_flags = _flags_dict_to_list(payload.skipped_required_flags, selected_models)

    db.commit()
    db.refresh(entry)

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

    if study and content and entry:
        try:
            _sync_study_entry_to_dts_safe(
                study=study,
                content=content,
                entry=entry,
                actor_id=user.id,
                actor_name=_display_name(user),
                context="update_study_data_entry",
            )
        except Exception as de:
            raise HTTPException(status_code=500, detail=f"DTS sync failed during update study data entry: {de}")

    return _dts_entry_or_sql_fallback(study_id, entry.id, entry)


@router.get("/studies/{study_id}/data_entries", response_model=schemas.PaginatedStudyDataEntries)
def list_study_data_entries(
    study_id: int,
    subject_indexes: Optional[str] = Query(None, description="Comma-separated subject indexes for current page"),
    visit_indexes: Optional[str] = Query(None, description="Comma-separated visit indexes for current page"),
    all: bool = Query(False, description="Return all entries for the study"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        study_meta, _ = get_study_from_dts(study_id)
    except Exception:
        study_meta = None

    if not study_meta:
        raise HTTPException(404, "Study not found")

    perms = _effective_study_permissions(db, study_meta, user)
    if not perms.get("view", False):
        raise HTTPException(status_code=403, detail="Not authorized")

    try:
        entries = list_study_entries_from_dts(study_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DTS read failed: {e}")

    if not all:
        if subject_indexes:
            subj_idx_list = [int(s) for s in subject_indexes.split(",") if s.strip().isdigit()]
            if subj_idx_list:
                entries = [e for e in entries if e["subject_index"] in subj_idx_list]

        if visit_indexes:
            visit_idx_list = [int(s) for s in visit_indexes.split(",") if s.strip().isdigit()]
            if visit_idx_list:
                entries = [e for e in entries if e["visit_index"] in visit_idx_list]

    return {"total": len(entries), "entries": entries}


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

    try:
        _, dts_content = get_study_from_dts(study_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DTS study read failed: {e}")

    content = db.query(models.StudyContent).filter(models.StudyContent.study_id == study_id).first()
    selected_models = ((content.study_data or {}).get("selectedModels") if content and isinstance(content.study_data, dict) else []) or \
                      ((dts_content.study_data or {}).get("selectedModels") if dts_content and isinstance(dts_content.study_data, dict) else []) or []

    _validate_shared_payload_sections(
        payload_data=payload.data or {},
        study_data=(dts_content.study_data if dts_content else {}),
        allowed_section_ids=access.allowed_section_ids or [],
    )

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
                    actor="Shared link submit",
                    db=db,
                    actor_id=None,
                    actor_name=None,
                )

            if study and content and entry:
                _sync_study_entry_to_dts_safe(
                    study=study,
                    content=content,
                    entry=entry,
                    actor_id=None,
                    actor_name="Shared link submit",
                    context="shared_upsert_data",
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

    return _dts_entry_or_sql_fallback(study_id, entry.id, entry)


# -------------------------------------------------------------------
# Study access management
# -------------------------------------------------------------------

@router.get("/studies/{study_id}/access", response_model=List[schemas.StudyAccessGrantOut])
def list_study_access(
    study_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        meta, _ = get_study_from_dts(study_id)
    except Exception:
        meta = None

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
    try:
        meta, _ = get_study_from_dts(study_id)
    except Exception:
        meta = None

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
    try:
        meta, _ = get_study_from_dts(study_id)
    except Exception:
        meta = None

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


# -------------------------------------------------------------------
# Bulk data
# -------------------------------------------------------------------

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

    if not create_bids:
        return {"inserted": inserted_count, "failed": 0, "errors": []}

    study = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == study_id).first()
    content = db.query(models.StudyContent).filter(models.StudyContent.study_id == study_id).first()
    if not study or not content:
        return {"inserted": inserted_count, "failed": 0, "errors": []}

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

        for r in just_inserted:
            _sync_study_entry_to_dts_safe(
                study=study,
                content=content,
                entry=r,
                actor_id=None,
                actor_name="Bulk import",
                context="bulk_insert_data",
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
        return {"inserted": inserted_count, "failed": inserted_count, "errors": [f"BIDS/DTS mirror failed: {be}"]}

    return {"inserted": inserted_count, "failed": 0, "errors": []}


# -------------------------------------------------------------------
# BIDS helpers
# -------------------------------------------------------------------

def _ensure_can_see_bids(current_user: models.User, study: Any) -> None:
    role = (getattr(getattr(current_user, "profile", None), "role", "") or "").strip().lower()
    is_admin = role == "administrator"
    is_owner = current_user.id == getattr(study, "created_by", None)

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
    try:
        study, _ = get_study_from_dts(study_id)
    except Exception:
        study = None

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
    try:
        study, _ = get_study_from_dts(study_id)
    except Exception:
        study = None

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


# -------------------------------------------------------------------
# Delete
# -------------------------------------------------------------------

@router.delete("/studies/{study_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_study(
    study_id: int,
    include_drafts: bool = Query(True, description="If true, also delete any drafts (DRAFT/ARCHIVED) whose draft_of_study_id == this study_id"),
    delete_bids: bool = Query(True, description="If true, also delete the BIDS dataset folder from disk (best-effort)."),
    audit_label: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        meta, _ = get_study_from_dts(study_id)
    except Exception:
        meta = None

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


# -------------------------------------------------------------------
# DTS shadow debug
# -------------------------------------------------------------------

@router.get("/studies/{study_id}/dts-shadow")
def read_study_dts_shadow(study_id: int):
    client = DTSClient()
    pid = study_pid(study_id)
    record = client.get_record(DTS_COLLECTION, pid)
    return record