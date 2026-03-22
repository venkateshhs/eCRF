from __future__ import annotations

from typing import Optional, List, Dict, Any
from datetime import datetime
from eCRF_backend.dts.dts_client import DTSClient
from eCRF_backend.dts.dts_settings import DTS_COLLECTION, DTS_CLASS
from .dts_mapping import (
    study_pid,
    study_to_dts_record,
    study_entry_to_dts_record,
    DTSMetadataShim,
    DTSContentShim,
    parse_entry_pid_components, dts_entry_record_to_out, study_file_to_dts_record, study_template_snapshot_to_dts_record
)

DTS_ENTRY_CLASS = "CaseeStudyEntry"
DTS_FILE_CLASS = "CaseeStudyFile"
DTS_TEMPLATE_SNAPSHOT_CLASS = "CaseeStudyTemplateSnapshot"
def upsert_template_snapshot_to_dts(study_id: int, version_row):
    client = DTSClient()
    payload = study_template_snapshot_to_dts_record(study_id=study_id, version_row=version_row)
    return client.post_record(DTS_COLLECTION, DTS_TEMPLATE_SNAPSHOT_CLASS, payload)
def upsert_study_file_to_dts(study, content, db_file):
    client = DTSClient()
    payload = study_file_to_dts_record(study=study, content=content, db_file=db_file)
    return client.post_record(DTS_COLLECTION, DTS_FILE_CLASS, payload)
def list_study_entries_from_dts(study_id: int):
    client = DTSClient()
    records = client.list_records(DTS_COLLECTION, DTS_ENTRY_CLASS)

    out = []
    for r in records or []:
        if r.get("study_id") == study_id:
            out.append(dts_entry_record_to_out(r))

    out.sort(key=lambda x: (
        x.get("subject_index", 0),
        x.get("visit_index", 0),
        x.get("group_index", 0),
        x.get("id") or 0,
    ))
    return out

def get_study_entry_from_dts(study_id: int, entry_id: int):
    client = DTSClient()
    records = client.list_records(DTS_COLLECTION, DTS_ENTRY_CLASS)

    for r in records or []:
        if r.get("study_id") == study_id and r.get("entry_id") == entry_id:
            return dts_entry_record_to_out(r)
    return None
def upsert_study_entry_to_dts(
    study,
    content,
    entry,
    actor_id: Optional[int] = None,
    actor_name: Optional[str] = None,
):
    client = DTSClient()
    payload = study_entry_to_dts_record(
        study=study,
        content=content,
        entry=entry,
        actor_id=actor_id,
        actor_name=actor_name,
    )
    return client.post_record(DTS_COLLECTION, DTS_ENTRY_CLASS, payload)
def upsert_study_to_dts(metadata, content, current_template_version: Optional[int] = None, template_snapshot_created_at: Optional[str] = None):
    client = DTSClient()
    payload = study_to_dts_record(
        metadata,
        content,
        current_template_version=current_template_version,
        template_snapshot_created_at=template_snapshot_created_at,
    )
    return client.post_record(DTS_COLLECTION, DTS_CLASS, payload)


def get_study_from_dts(study_id: int):
    client = DTSClient()
    record = client.get_record(DTS_COLLECTION, study_pid(study_id))
    return DTSMetadataShim(record), DTSContentShim(record)

def _parse_dt(value: Optional[str]):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None
def list_studies_from_dts() -> List[Dict[str, Any]]:
    client = DTSClient()

    # assumes your DTS client has this helper
    # if not, call requests directly against:
    # GET /casee_studies/records/CaseeStudy
    records = client.list_records(DTS_COLLECTION, "CaseeStudy")

    out: List[Dict[str, Any]] = []
    for rec in records or []:
        out.append({
            "id": int(rec["study_id"]),
            "study_name": rec.get("study_name") or "",
            "study_description": rec.get("study_description"),
            "status": rec.get("workflow_status") or "PUBLISHED",
            "draft_of_study_id": rec.get("draft_of_study_id"),
            "last_completed_step": rec.get("last_completed_step"),
            "created_by": int(rec["created_by"]) if rec.get("created_by") is not None else None,
            "created_at": _parse_dt(rec.get("created_at")),
            "updated_at": _parse_dt(rec.get("updated_at")),
        })
    return out