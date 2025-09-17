# ecrf_backend/forms.py
import os
import shutil
import tempfile
from typing import List, Optional
from urllib.parse import urlparse

from fastapi import Request
from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File, Form, Body
from pathlib import Path
import json
import yaml
from datetime import datetime, timedelta

from .database import get_db
from . import schemas, crud, models
from .bids_exporter import upsert_bids_dataset, write_entry_to_bids, stage_file_for_modalities
from .logger import logger
from .models import User, StudyTemplateVersion
from .users import get_current_user
from sqlalchemy.orm import Session
import secrets

router = APIRouter(prefix="/forms", tags=["forms"])

TEMPLATE_DIR = Path(os.environ.get("ECRF_TEMPLATES_DIR", "")) if os.environ.get("ECRF_TEMPLATES_DIR") \
    else (Path(__file__).resolve().parent / "templates")


def _assert_owner_or_admin(meta: models.StudyMetadata, user) -> None:
    if meta.created_by != user.id and getattr(user.profile, "role", None) != "Administrator":
        raise HTTPException(status_code=403, detail="Not authorized")


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

    try:
        metadata, content = crud.create_study(db, study_metadata, study_content)
    except Exception as e:
        logger.error("Error creating study: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

    # BIDS: create dataset structure after DB commit
    if upsert_bids_dataset:
        try:
            dataset_path = upsert_bids_dataset(
                study_id=metadata.id,
                study_name=metadata.study_name,
                study_description=metadata.study_description,
                study_data=content.study_data,
            )
            # persist any label-map mutations
            db.query(models.StudyContent).filter(models.StudyContent.id == content.id).update(
                {"study_data": content.study_data}
            )
            db.commit()
            db.refresh(content)
            logger.info("BIDS dataset initialized at %s (study_id=%s)", dataset_path, metadata.id)
        except Exception as be:
            logger.error("BIDS export (create) failed for study %s: %s", metadata.id, be)

    return {"metadata": metadata, "content": content}


@router.get("/studies", response_model=List[schemas.StudyMetadataOut])
def list_studies(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.profile.role == "Administrator":
        studies = db.query(models.StudyMetadata).all()
    else:
        studies = (
            db.query(models.StudyMetadata)
            .filter(models.StudyMetadata.created_by == current_user.id)
            .all()
        )
    return studies


@router.get("/studies/{study_id}", response_model=schemas.StudyFull)
def read_study(
    study_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    result = crud.get_study_full(db, study_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Study not found")
    metadata, content = result
    if metadata.created_by != user.id and user.profile.role != "Administrator":
        raise HTTPException(status_code=403, detail="Not authorized to view this study")
    return {"metadata": metadata, "content": content}


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

    if not study_content.study_data.get("id"):
        study_content.study_data["id"] = study_id

    try:
        result = crud.update_study(db, study_id, study_metadata, study_content)
    except Exception as e:
        logger.error("Error updating study: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

    metadata, content = result

    # BIDS: update dataset structure
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
        except Exception as be:
            logger.error("BIDS export (update) failed for study %s: %s", metadata.id, be)

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
    storage_option: str = Form("local"),  # kept for compat; we override to "bids" below
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

    # Save to a temporary file just for the exporter to ingest; then delete.
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, prefix=f"ecrf_study{study_id}_", suffix=f"_{uploaded_file.filename}") as tmp:
            shutil.copyfileobj(uploaded_file.file, tmp)
            tmp_path = tmp.name
        logger.info("Staged temp upload: %s", tmp_path)

        # Mirror into BIDS structure (authoritative storage)
        content = db.query(models.StudyContent).filter(models.StudyContent.study_id == study_id).first()
        study_data = content.study_data if content else {}
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
        )

        # DB record: mark storage as 'bids' and store the filename (path is managed by BIDS layout)
        file_data = schemas.FileCreate(
            study_id=study_id,
            file_name=uploaded_file.filename,
            file_path=uploaded_file.filename,   # logical reference; actual path is within BIDS dataset
            description=description,
            storage_option="bids"
        )
        db_file = crud.create_file(db, file_data)

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

    # Create DB record (URL)
    try:
        parsed = urlparse(url)
        base = os.path.basename(parsed.path) or "link"
        file_data = schemas.FileCreate(
            study_id=study_id,
            file_name=base,
            file_path=url,           # store URL itself
            description=description,
            storage_option=storage_option or "url"
        )
        db_file = crud.create_file(db, file_data)
    except Exception as e:
        logger.error("Error creating URL file record: %s", e)
        raise HTTPException(status_code=500, detail="Error creating file record")

    # Mirror into BIDS (delegated; writes .txt with URL)
    try:
        content = db.query(models.StudyContent).filter(models.StudyContent.study_id == study_id).first()
        study_data = content.study_data if content else {}
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
        )
    except Exception as be:
        logger.error("BIDS mirror (URL) failed for study %s: %s", study_id, be)

    return db_file


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

    # Prefer explicit config, then Origin, then Referer, then X-Forwarded, then Host
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

    # Build SPA route (NOT the API endpoint)
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


def get_current_form_version(db: Session, study_id: int) -> int:
    latest_version = (
        db.query(StudyTemplateVersion)
        .filter(StudyTemplateVersion.study_id == study_id)
        .order_by(StudyTemplateVersion.version.desc())
        .first()
    )
    if not latest_version:
        raise ValueError(f"No template version found for study_id={study_id}")
    return latest_version.version


@router.post("/studies/{study_id}/data", response_model=schemas.StudyDataEntryOut)
def save_study_data(study_id: int, payload: schemas.StudyDataEntryCreate, db: Session = Depends(get_db)):
    study = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == study_id).first()
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")

    try:
        form_version = get_current_form_version(db, study_id)
    except ValueError:
        form_version = 1

    entry = models.StudyEntryData(
        study_id=study_id,
        subject_index=payload.subject_index,
        visit_index=payload.visit_index,
        group_index=payload.group_index,
        data=payload.data,
        skipped_required_flags=payload.skipped_required_flags,
        form_version=form_version
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    # BIDS: structure + write eCRF row
    content = db.query(models.StudyContent).filter(models.StudyContent.study_id == study_id).first()
    if upsert_bids_dataset and content:
        try:
            upsert_bids_dataset(
                study_id=study.id,
                study_name=study.study_name,
                study_description=study.study_description,
                study_data=content.study_data,
            )
            # persist label-map mutations
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
                    }
                )
                logger.info(
                    "BIDS eCRF updated for study=%s sub_idx=%s visit_idx=%s entry_id=%s",
                    study.id, entry.subject_index, entry.visit_index, entry.id
                )
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
        entry.skipped_required_flags = payload.skipped_required_flags

    db.commit()
    db.refresh(entry)

    # BIDS: structure + upsert eCRF row
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
                    }
                )
                logger.info(
                    "BIDS eCRF upserted for study=%s sub_idx=%s visit_idx=%s entry_id=%s",
                    study.id, entry.subject_index, entry.visit_index, entry.id
                )
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
        )
        file_data = schemas.FileCreate(
            study_id=study.id,
            file_name=uploaded_file.filename,
            file_path=uploaded_file.filename,
            description=description,
            storage_option="bids",
        )
        db_file = crud.create_file(db, file_data)
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
        base = os.path.basename(parsed.path) or "link"
        file_data = schemas.FileCreate(
            study_id=study.id,
            file_name=base,
            file_path=url,
            description=description,
            storage_option="url",
        )
        db_file = crud.create_file(db, file_data)
    except Exception as e:
        logger.error("Shared URL file record error: %s", e)
        raise HTTPException(status_code=500, detail="Error creating file record")

    try:
        content = db.query(models.StudyContent).filter(models.StudyContent.study_id == study.id).first()
        study_data = content.study_data if content else {}
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
        )
    except Exception as be:
        logger.error("Shared BIDS mirror (URL) failed for study %s: %s", study.id, be)

    return db_file


@router.post("/shared/{token}/data", response_model=schemas.StudyDataEntryOut)
def shared_upsert_data(token: str, payload: schemas.StudyDataEntryCreate, db: Session = Depends(get_db)):
    access = db.query(models.SharedFormAccess).filter_by(token=token).first()
    if not access: raise HTTPException(404, "Link not found")
    if access.expires_at < datetime.utcnow(): raise HTTPException(403, "Link expired")
    if access.permission != "add": raise HTTPException(403, "Not allowed")

    # lock to token’s indices
    s, v, g = access.subject_index, access.visit_index, access.group_index
    study_id = access.study_id

    entry = (db.query(models.StudyEntryData)
               .filter_by(study_id=study_id, subject_index=s, visit_index=v, group_index=g)
               .order_by(models.StudyEntryData.id.desc())
               .first())

    if entry:
        entry.data = payload.data
        entry.skipped_required_flags = payload.skipped_required_flags
        db.commit(); db.refresh(entry)
        return entry
    else:
        # reuse your existing create flow/versioning
        try:
            form_version = get_current_form_version(db, study_id)
        except ValueError:
            form_version = 1
        entry = models.StudyEntryData(
            study_id=study_id, subject_index=s, visit_index=v, group_index=g,
            data=payload.data, skipped_required_flags=payload.skipped_required_flags,
            form_version=form_version
        )
        db.add(entry); db.commit(); db.refresh(entry)
        return entry
