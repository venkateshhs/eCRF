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
    bump_bids_version, bulk_write_entries_to_bids, _dataset_path,
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
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    if study_metadata.created_by != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to create study for this user")

    # Keep a *pre-BIDS* snapshot (so labels/IDs aren’t rewritten) for versioning
    incoming_snapshot = _deepcopy_json(study_content.study_data or {})

    try:
        metadata, content = crud.create_study(db, study_metadata, study_content)
    except Exception as e:
        logger.error("Error creating study: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

    # Initialize BIDS dataset
    if upsert_bids_dataset:
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
                audit_change_both(scope="study", action="study_created", actor=_display_name(user),
                                  extra={"study_name": metadata.study_name},
                                  study_id=metadata.id, study_name=metadata.study_name,
                                  db=db, actor_id=user.id)
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    role = (current_user.profile.role or "").strip()

    # Admin sees everything
    if role == "Administrator":
        return db.query(models.StudyMetadata).all()

    # Everyone else: include (a) studies they own, plus (b) studies they were granted access to
    grant_subq = (
        db.query(models.StudyAccessGrant.study_id)
          .filter(models.StudyAccessGrant.user_id == current_user.id)
          .subquery()
    )

    studies = (
        db.query(models.StudyMetadata)
          .filter(
              or_(
                  models.StudyMetadata.created_by == current_user.id,
                  models.StudyMetadata.id.in_(grant_subq)
              )
          )
          .all()
    )
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

    # authorize: admin OR owner OR explicit access grant
    role = (getattr(user.profile, "role", "") or "").strip()
    is_admin = role == "Administrator"
    is_owner = (metadata.created_by == user.id)

    has_grant = (
        db.query(models.StudyAccessGrant)
          .filter(
              models.StudyAccessGrant.study_id == study_id,
              models.StudyAccessGrant.user_id == user.id,
          )
          .first()
        is not None
    )

    if not (is_admin or is_owner or has_grant):
        raise HTTPException(status_code=403, detail="Not authorized to view this study")

    return {"metadata": metadata, "content": content}


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
    _assert_owner_or_admin(meta, user)

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
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    existing = crud.get_study_full(db, study_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Study not found")
    metadata, content = existing
    if metadata.created_by != user.id and user.profile.role != "Administrator":
        raise HTTPException(status_code=403, detail="Not authorized to update this study")

    # Ensure id present
    if not study_content.study_data.get("id"):
        study_content.study_data["id"] = study_id

    old_sd = _deepcopy_json(content.study_data or {})
    new_sd_incoming = _deepcopy_json(study_content.study_data or {})

    # capture previous latest template version
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

            # Optional CHANGES mirror
            log_dataset_change_to_changes(metadata.id, metadata.study_name,
                                          action="dataset_structure_updated",
                                          actor_id=user.id, actor_name=_display_name(user),
                detail="Study metadata/content updated"
            )

            # AUDIT: study edited
            try:
                audit_change_both(scope="study", action="study_edited", actor=_display_name(user),
                                  extra={"study_name": metadata.study_name},
                                  study_id=metadata.id, study_name=metadata.study_name,
                                  db=db, actor_id=user.id)
            except Exception:
                pass
        except Exception as be:
            logger.error("BIDS export (update) failed for study %s: %s", metadata.id, be)

    # Versioning: bump only if latest has data; otherwise overwrite; clone rows on bump
    def _audit(action: str, extra: Dict[str, Any]):
        try:
            audit_change_both(
                scope="study",
                action=action,
                actor=_display_name(user),
                extra=extra or {},
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

    # Detect template version bump and copy BIDS tree non-destructively
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
    study = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == study_id).first()
    if not study or study.created_by != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access files for this study")
    files = crud.get_files_for_study(db, study_id)
    return files


@router.post("/studies/{study_id}/files", response_model=schemas.FileOut)
def upload_file(
    study_id: int,
    uploaded_file: UploadFile = File(...),
    description: str = Form(""),
    storage_option: str = Form("local"),  # ignored; we force to "bids"
    subject_index: Optional[int] = Form(None),
    visit_index: Optional[int] = Form(None),
    group_index: Optional[int] = Form(None),
    modalities_json: Optional[str] = Form("[]"),
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

        # Mirror into BIDS
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

        # DB record
        file_data = schemas.FileCreate(
            study_id=study_id,
            file_name=uploaded_file.filename,
            file_path=uploaded_file.filename,   # logical ref; actual path is inside BIDS dataset
            description=description,
            storage_option="bids",
            subject_index=subject_index,
            visit_index=visit_index,
            group_index=group_index,
        )
        db_file = crud.create_file(db, file_data)

        # AUDIT: file added to study
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

    # DB record (URL)
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

    # Mirror into BIDS as .txt pointer
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

    # AUDIT: file added to study (URL)
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.profile.role not in ["Investigator", "Administrator", "Principal Investigator"]:
        raise HTTPException(status_code=403, detail="Not allowed")

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
    )
    db.add(access)
    db.commit()
    db.refresh(access)

    # AUDIT: share link created
    try:
        audit_change_both(
            scope="study",
            action="share_link_created",
            actor=_display_name(current_user),
            extra={
                "permission": payload.permission,
                "max_uses": payload.max_uses,
                "expires_in_days": payload.expires_in_days,
            },
            study_id=payload.study_id,
            study_name=None,
            db=db,
            actor_id=current_user.id,
        )
    except Exception:
        pass

    # Build SPA route
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

    return {
        "study_id":      access.study_id,
        "subject_index": access.subject_index,
        "visit_index":   access.visit_index,
        "group_index":   access.group_index,
        "permission":    access.permission,
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
                "study_data": content.study_data
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    study = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == study_id).first()
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")

    # Permission: Admin/Owner or explicit grant with add_data=True
    is_admin = getattr(getattr(current_user, "profile", None), "role", "") == "Administrator"
    is_owner = study.created_by == current_user.id
    if not (is_admin or is_owner):
        grant = db.query(models.StudyAccessGrant).filter_by(study_id=study_id, user_id=current_user.id).first()
        if not grant or not (grant.permissions or {}).get("add_data", False):
            raise HTTPException(status_code=403, detail="Not allowed to add data for this study")

    # Only latest version is writable
    try:
        form_version = VersionManager.assert_latest_is_used(db, study_id, version)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

    # Always insert a new row (no cross-version overwrite)
    content = db.query(models.StudyContent).filter(models.StudyContent.study_id == study_id).first()
    selected_models = ((content.study_data or {}).get("selectedModels") if content and isinstance(content.study_data,
                                                                                                  dict) else []) or []
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

    # BIDS: upsert eCRF row
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
            try:
                audit_change_both(scope="study", action="entry_upserted", actor=_display_name(current_user),
                                  extra={"entry_id": entry.id, "subject_index": entry.subject_index, "visit_index": entry.visit_index},
                                  study_id=study.id, study_name=study.study_name, db=db, actor_id=current_user.id)
            except Exception:
                pass
        except Exception as be:
            logger.error("BIDS export (data save) failed for study %s: %s", study_id, be)

    return entry


@router.put("/studies/{study_id}/data_entries/{entry_id}", response_model=schemas.StudyDataEntryOut)
def update_study_data_entry(
    study_id: int,
    entry_id: int,
    payload: schemas.StudyDataEntryCreate,  # contains skipped_required_flags
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

    entry.subject_index = payload.subject_index
    entry.visit_index   = payload.visit_index
    entry.group_index   = payload.group_index
    entry.data          = payload.data
    if payload.skipped_required_flags is not None:
        content = db.query(models.StudyContent).filter(models.StudyContent.study_id == study_id).first()
        selected_models = ((content.study_data or {}).get("selectedModels") if content and isinstance(
            content.study_data, dict) else []) or []
        entry.skipped_required_flags = _flags_dict_to_list(payload.skipped_required_flags, selected_models)
    db.commit()
    db.refresh(entry)

    # BIDS: upsert eCRF row
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
            db.query(models.StudyContent).filter(models.StudyContent.id == content.id).update(
                {"study_data": content.study_data}
            )
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

    # AUDIT: share link file addition (URL)
    try:
        audit_change_both(
            scope="study",
            action="share_file_added",
            actor="",
            extra={"file_name": base, "url": url, "modalities": modalities,
                   "subject_index": access.subject_index, "visit_index": access.visit_index},
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

    # Idempotent within latest only: update if a row for this (s,v,g,latest) exists, else insert
    entry = (
        db.query(models.StudyEntryData)
          .filter_by(study_id=study_id, subject_index=s, visit_index=v, group_index=g, form_version=form_version)
          .order_by(models.StudyEntryData.id.desc())
          .first()
    )
    content = db.query(models.StudyContent).filter(models.StudyContent.study_id == study_id).first()
    selected_models = ((content.study_data or {}).get("selectedModels") if content and isinstance(content.study_data,
                                                                                                  dict) else []) or []
    if entry:
        entry.data = payload.data
        entry.skipped_required_flags =  _flags_dict_to_list(payload.skipped_required_flags, selected_models)
        db.commit()
        db.refresh(entry)
    else:

        entry = models.StudyEntryData(
            study_id=study_id,
            subject_index=s, visit_index=v, group_index=g,
            data=payload.data,
            skipped_required_flags= _flags_dict_to_list(payload.skipped_required_flags, selected_models),
            form_version=form_version
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)

    # BIDS mirror (same as authenticated path)
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
                audit_change_both(scope="study", action="share_entry_upserted", actor="",
                                  extra={"entry_id": entry.id, "subject_index": entry.subject_index, "visit_index": entry.visit_index},
                                  study_id=study.id, study_name=study.study_name, db=db, actor_id=None)
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

    grants = (
        db.query(models.StudyAccessGrant)
          .filter(models.StudyAccessGrant.study_id == study_id)
          .all()
    )

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

    # upsert
    grant = (
        db.query(models.StudyAccessGrant)
          .filter_by(study_id=study_id, user_id=payload.user_id)
          .first()
    )
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

    # AUDIT: access granted/updated
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

    # AUDIT: access revoked
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
    db: Session = Depends(get_db)
):
    if not payload.entries:
        return {"inserted": 0, "failed": 0, "errors": []}

    # Enforce latest-only
    try:
        form_version = VersionManager.assert_latest_is_used(db, study_id, version)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

    # Prepare rows for one executemany insert
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
        db.execute(sql, rows)   # executemany
        db.commit()
    except Exception as ex:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Bulk insert failed: {ex}")

    inserted_count = len(rows)

    # Load study context for BIDS
    study = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == study_id).first()
    content = db.query(models.StudyContent).filter(models.StudyContent.study_id == study_id).first()
    if not study or not content:
        # unlikely, but keep safe
        return {"inserted": inserted_count, "failed": 0, "errors": []}

    # Re-select just-inserted rows for this request, then one batched BIDS write
    just_inserted = (
        db.query(models.StudyEntryData)
          .filter(
              models.StudyEntryData.study_id == study_id,
              models.StudyEntryData.form_version == form_version,
              models.StudyEntryData.created_at == now,
          )
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

    # Ensure dataset structure once (cheap if existing)
    try:
        upsert_bids_dataset(
            study_id=study.id,
            study_name=study.study_name,
            study_description=study.study_description,
            study_data=content.study_data or {},
        )
    except Exception:
        # Non-fatal; bulk BIDS write will attempt again as needed
        pass

    # One fast BIDS write
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
    except Exception as be:
        # Do not roll back DB; report error but keep inserted count
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
    return {
        "dataset_path": dataset_path,
        "exists": os.path.isdir(dataset_path),
    }
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
        raise HTTPException(
            status_code=500,
            detail=f"Failed to open BIDS folder: {e}",
        )

    # 204 No Content
    return
