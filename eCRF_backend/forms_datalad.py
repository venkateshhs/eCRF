# eCRF_backend/forms_datalad.py
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

from . import schemas
from .bids_exporter_datalad import assert_latest_is_used
from .datalad_repo import DataladStudyRepo, _deepcopy_json
from .users import get_current_user

router = APIRouter(prefix="/forms", tags=["forms"])
repo = DataladStudyRepo()

TEMPLATE_DIR = Path(os.environ.get("ECRF_TEMPLATES_DIR", "")) if os.environ.get("ECRF_TEMPLATES_DIR") \
    else (Path(__file__).resolve().parent / "templates")

ALLOWED_STUDY_STATUS = {"DRAFT", "PUBLISHED", "ARCHIVED"}


def _resolve_study_name_or_404(study_id: int) -> str:
    try:
        return repo.get_study_name_by_id(study_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Study not found")


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


def _is_admin(user) -> bool:
    role = (getattr(getattr(user, "profile", None), "role", "") or "").strip()
    return role == "Administrator"


def _assert_owner_or_admin(meta: Dict[str, Any], user) -> None:
    if int(meta.get("created_by")) != int(user.id) and not _is_admin(user):
        raise HTTPException(status_code=403, detail="Not authorized")


def _effective_study_permissions(meta: Dict[str, Any], user) -> Dict[str, bool]:
    if _is_admin(user) or int(meta.get("created_by")) == int(user.id):
        return {"view": True, "add_data": True, "edit_study": True}

    grants = repo.list_access(meta["id"], meta["study_name"])
    for g in grants:
        if int(g.get("user_id")) == int(user.id):
            perms = g.get("permissions") or {}
            return {
                "view": bool(perms.get("view", True)),
                "add_data": bool(perms.get("add_data", True)),
                "edit_study": bool(perms.get("edit_study", False)),
            }
    return {"view": False, "add_data": False, "edit_study": False}


def _assert_has_study_permission(meta: Dict[str, Any], user, required: str = "view") -> Dict[str, bool]:
    perms = _effective_study_permissions(meta, user)
    if not perms.get(required, False):
        raise HTTPException(status_code=403, detail="Not authorized")
    return perms


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
    user=Depends(get_current_user),
):
    if study_metadata.created_by != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to create study for this user")

    desired_status = _norm_status(status) or "PUBLISHED"
    study_id = repo.next_study_id()

    result = repo.create_study(
        study_id=study_id,
        created_by=study_metadata.created_by,
        study_name=study_metadata.study_name,
        study_description=study_metadata.study_description,
        study_data=study_content.study_data or {},
        status=desired_status,
        draft_of_study_id=draft_of_study_id,
        last_completed_step=last_completed_step,
    )
    return result


@router.get("/studies", response_model=List[schemas.StudyMetadataOut])
def list_studies(
    status: Optional[str] = Query(None),
    current_user=Depends(get_current_user),
):
    status_norm = _norm_status(status)
    studies = repo.list_studies()
    out = []

    for meta in studies:
        perms = _effective_study_permissions(meta, current_user)
        if not perms["view"] and not perms["add_data"] and not perms["edit_study"]:
            continue
        if status_norm and meta.get("status") != status_norm:
            continue
        row = dict(meta)
        row["permissions"] = perms
        out.append(row)

    return out


@router.get("/studies/{study_id}", response_model=schemas.StudyFull)
def read_study(
    study_id: int,
    user=Depends(get_current_user),
):
    study_name = _resolve_study_name_or_404(study_id)
    result = repo.read_study(study_id, study_name)
    perms = _assert_has_study_permission(result["metadata"], user, required="view")

    meta = dict(result["metadata"])
    meta["permissions"] = perms
    return {"metadata": meta, "content": result["content"]}


@router.get("/studies/{study_id}/versions")
def list_study_versions(
    study_id: int,
    user=Depends(get_current_user),
):
    study_name = _resolve_study_name_or_404(study_id)
    result = repo.read_study(study_id, study_name)
    _assert_has_study_permission(result["metadata"], user, required="view")
    return repo.list_versions(study_id, study_name)


@router.get("/studies/{study_id}/template")
def get_template_version(
    study_id: int,
    version: Optional[int] = Query(None),
    user=Depends(get_current_user),
):
    study_name = _resolve_study_name_or_404(study_id)
    result = repo.read_study(study_id, study_name)
    _assert_has_study_permission(result["metadata"], user, required="view")
    try:
        return repo.get_template(study_id, study_name, version)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Template version not found")


@router.put("/studies/{study_id}", response_model=schemas.StudyFull)
def update_study(
    study_id: int,
    study_metadata: schemas.StudyMetadataUpdate = Body(..., embed=True),
    study_content: schemas.StudyContentUpdate = Body(..., embed=True),
    audit_label: Optional[str] = Query(None),
    user=Depends(get_current_user),
):
    study_name = _resolve_study_name_or_404(study_id)
    current = repo.read_study(study_id, study_name)
    _assert_owner_or_admin(current["metadata"], user)

    result = repo.update_study(
        study_id=study_id,
        current_study_name=study_name,
        study_name=getattr(study_metadata, "study_name", None),
        study_description=getattr(study_metadata, "study_description", None),
        study_data=study_content.study_data or {},
        status=getattr(study_metadata, "status", None),
        last_completed_step=getattr(study_metadata, "last_completed_step", None) if hasattr(study_metadata, "last_completed_step") else None,
        audit_label=audit_label,
    )
    return result


@router.get("/studies/{study_id}/files", response_model=List[schemas.FileOut])
def read_files_for_study(
    study_id: int,
    user=Depends(get_current_user),
):
    study_name = _resolve_study_name_or_404(study_id)
    current = repo.read_study(study_id, study_name)
    _assert_has_study_permission(current["metadata"], user, required="view")
    return repo.list_files(study_id, study_name)


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
    user=Depends(get_current_user),
):
    study_name = _resolve_study_name_or_404(study_id)
    current = repo.read_study(study_id, study_name)
    _assert_owner_or_admin(current["metadata"], user)

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, prefix=f"ecrf_study{study_id}_", suffix=f"_{uploaded_file.filename}") as tmp:
            shutil.copyfileobj(uploaded_file.file, tmp)
            tmp_path = tmp.name

        return repo.save_uploaded_file(
            study_id=study_id,
            study_name=study_name,
            filename=uploaded_file.filename,
            source_path=tmp_path,
            description=description,
            subject_index=subject_index,
            visit_index=visit_index,
            group_index=group_index,
            actor=_display_name(user),
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
    user=Depends(get_current_user),
):
    study_name = _resolve_study_name_or_404(study_id)
    current = repo.read_study(study_id, study_name)
    _assert_owner_or_admin(current["metadata"], user)

    return repo.save_url_file(
        study_id=study_id,
        study_name=study_name,
        url=url,
        description=description,
        subject_index=subject_index,
        visit_index=visit_index,
        group_index=group_index,
        actor=_display_name(user),
        audit_label=audit_label,
    )


@router.post("/studies/{study_id}/data", response_model=schemas.StudyDataEntryOut)
def save_study_data(
    study_id: int,
    payload: schemas.StudyDataEntryCreate = Body(...),
    version: Optional[int] = Query(None),
    audit_label: Optional[str] = Query(None),
    current_user=Depends(get_current_user),
):
    study_name = _resolve_study_name_or_404(study_id)
    current = repo.read_study(study_id, study_name)
    _assert_has_study_permission(current["metadata"], current_user, required="add_data")

    try:
        form_version = assert_latest_is_used(study_id, study_name, version)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

    selected_models = ((current["content"]["study_data"] or {}).get("selectedModels") or [])

    return repo.save_entry(
        study_id=study_id,
        study_name=study_name,
        subject_index=payload.subject_index,
        visit_index=payload.visit_index,
        group_index=payload.group_index,
        form_version=form_version,
        data=payload.data,
        skipped_required_flags=_flags_dict_to_list(payload.skipped_required_flags, selected_models),
        actor=_display_name(current_user),
        audit_label=audit_label,
    )


@router.put("/studies/{study_id}/data_entries/{entry_id}", response_model=schemas.StudyDataEntryOut)
def update_study_data_entry(
    study_id: int,
    entry_id: int,
    payload: schemas.StudyDataEntryCreate = Body(...),
    audit_label: Optional[str] = Query(None),
    user=Depends(get_current_user),
):
    study_name = _resolve_study_name_or_404(study_id)
    current = repo.read_study(study_id, study_name)
    _assert_has_study_permission(current["metadata"], user, required="add_data")

    selected_models = ((current["content"]["study_data"] or {}).get("selectedModels") or [])

    return repo.update_entry(
        study_id=study_id,
        study_name=study_name,
        entry_id=entry_id,
        payload={
            "subject_index": payload.subject_index,
            "visit_index": payload.visit_index,
            "group_index": payload.group_index,
            "data": payload.data,
            "skipped_required_flags": _flags_dict_to_list(payload.skipped_required_flags, selected_models),
        },
        actor=_display_name(user),
        audit_label=audit_label,
    )


@router.get("/studies/{study_id}/data_entries", response_model=schemas.PaginatedStudyDataEntries)
def list_study_data_entries(
    study_id: int,
    subject_indexes: Optional[str] = Query(None),
    visit_indexes: Optional[str] = Query(None),
    all: bool = Query(False),
    user=Depends(get_current_user),
):
    study_name = _resolve_study_name_or_404(study_id)
    current = repo.read_study(study_id, study_name)
    _assert_has_study_permission(current["metadata"], user, required="view")

    entries = repo.list_entries(study_id, study_name)
    total = len(entries)

    if not all:
        if subject_indexes:
            subj_idx_list = [int(s) for s in subject_indexes.split(",") if s.strip().isdigit()]
            if subj_idx_list:
                entries = [e for e in entries if int(e.get("subject_index", -1)) in subj_idx_list]

        if visit_indexes:
            visit_idx_list = [int(s) for s in visit_indexes.split(",") if s.strip().isdigit()]
            if visit_idx_list:
                entries = [e for e in entries if int(e.get("visit_index", -1)) in visit_idx_list]

    return {"total": total, "entries": entries}


@router.post("/studies/{study_id}/access", status_code=201)
def grant_study_access(
    study_id: int,
    payload: schemas.StudyAccessGrantCreate = Body(...),
    user=Depends(get_current_user),
):
    study_name = _resolve_study_name_or_404(study_id)
    current = repo.read_study(study_id, study_name)
    _assert_owner_or_admin(current["metadata"], user)

    return repo.save_access_grant(
        study_id=study_id,
        study_name=study_name,
        user_id=payload.user_id,
        permissions=payload.permissions or {"view": True, "add_data": True, "edit_study": False},
        created_by=user.id,
    )


@router.get("/studies/{study_id}/access")
def list_study_access(
    study_id: int,
    current_user=Depends(get_current_user),
):
    study_name = _resolve_study_name_or_404(study_id)
    current = repo.read_study(study_id, study_name)
    _assert_owner_or_admin(current["metadata"], current_user)
    return repo.list_access(study_id, study_name)


@router.delete("/studies/{study_id}/access/{user_id}", status_code=204)
def revoke_study_access(
    study_id: int,
    user_id: int,
    current_user=Depends(get_current_user),
):
    study_name = _resolve_study_name_or_404(study_id)
    current = repo.read_study(study_id, study_name)
    _assert_owner_or_admin(current["metadata"], current_user)
    repo.revoke_access_grant(study_id=study_id, study_name=study_name, user_id=user_id)
    return


@router.post("/share-link/", status_code=201)
def create_share_link(
    payload: schemas.ShareLinkCreate,
    request: Request,
    current_user=Depends(get_current_user),
):
    studies = repo.list_studies()
    match = next((m for m in studies if int(m["id"]) == int(payload.study_id)), None)
    if not match:
        raise HTTPException(status_code=404, detail="Study not found")

    _assert_owner_or_admin(match, current_user)

    current = repo.read_study(payload.study_id, match["study_name"])
    study_data = (current["content"].get("study_data") or {})
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

    allowed_section_ids = requested_allowed_ids or sorted(assigned_section_ids)
    token = secrets.token_urlsafe(32)
    expires_at = (datetime.utcnow() + timedelta(days=payload.expires_in_days)).isoformat()

    repo.save_share_link(
        study_id=payload.study_id,
        study_name=match["study_name"],
        token=token,
        subject_index=payload.subject_index,
        visit_index=payload.visit_index,
        group_index=payload.group_index,
        permission=payload.permission,
        max_uses=payload.max_uses,
        expires_at=expires_at,
        allowed_section_ids=allowed_section_ids,
    )

    frontend_base = os.getenv("FRONTEND_BASE_URL", "").rstrip("/")
    if not frontend_base:
        frontend_base = f"{request.url.scheme}://{request.headers.get('host', request.url.netloc)}"

    return {"token": token, "link": f"{frontend_base}/shared/{token}"}


@router.delete("/studies/{study_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_study(
    study_id: int,
    current_user=Depends(get_current_user),
):
    study_name = _resolve_study_name_or_404(study_id)
    current = repo.read_study(study_id, study_name)
    _assert_owner_or_admin(current["metadata"], current_user)
    repo.delete_study(study_id, study_name)
    return