from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace

from eCRF_backend import forms_hybrid, models, schemas
from eCRF_backend.audit_datalad import _normalize_event
from eCRF_backend.audit_labels import (
    SHARED_URL_DATA_ENTRY_ACTOR,
    SHARED_URL_MACHINE_ACTOR,
)


class _Query:
    def __init__(self, result):
        self.result = result

    def filter_by(self, **_kwargs):
        return self

    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
        return self.result


class _Db:
    def __init__(self, access, metadata):
        self.access = access
        self.metadata = metadata

    def query(self, model):
        if model is models.SharedFormAccess:
            return _Query(self.access)
        if model is models.StudyMetadata:
            return _Query(self.metadata)
        raise AssertionError(f"Unexpected query model: {model}")


def test_shared_data_entry_uses_anonymous_shared_url_audit_actor(monkeypatch):
    access = SimpleNamespace(
        study_id=7,
        subject_index=0,
        visit_index=0,
        group_index=0,
        expires_at=datetime.utcnow() + timedelta(hours=1),
        permission="add",
        allowed_section_ids=[],
    )
    metadata = SimpleNamespace(id=7, study_name="Audit study", status="PUBLISHED")
    content = SimpleNamespace(
        study_data={
            "subjects": [{"id": "ARIA08LE", "status": "ACTIVE"}],
            "selectedModels": [],
            "assignments": [],
        }
    )
    captured = {}

    monkeypatch.setattr(forms_hybrid, "_resolve_form_version_or_400", lambda *_args: 1)
    monkeypatch.setattr(forms_hybrid, "_get_content_row_or_404", lambda *_args: content)
    monkeypatch.setattr(
        forms_hybrid.repo,
        "get_current_slot_state",
        lambda **_kwargs: {
            "revision_token": "revision-1",
            "data": {},
            "skipped_required_flags": [],
        },
    )
    monkeypatch.setattr(
        forms_hybrid,
        "calculate_overall_entry_progress",
        lambda **_kwargs: {
            "progress_status": "not_started",
            "progress_percentage": 0,
            "progress_completed": 0,
            "progress_total": 0,
            "progress_skipped": 0,
        },
    )

    def save_entry(**kwargs):
        captured.update(kwargs)
        return {
            "id": 11,
            "study_id": 7,
            "subject_index": 0,
            "visit_index": 0,
            "group_index": 0,
            "form_version": 1,
            "data": {},
            "skipped_required_flags": [],
            "created_at": datetime.utcnow().isoformat(),
        }

    monkeypatch.setattr(forms_hybrid.repo, "save_entry", save_entry)
    monkeypatch.setattr(forms_hybrid.repo, "compute_entry_revision_token", lambda _entry: "revision-2")

    forms_hybrid.shared_upsert_data(
        token="shared-token",
        payload=schemas.SharedStudyDataEntryCreate(data={}),
        version=None,
        expected_revision_token="revision-1",
        audit_label=None,
        db=_Db(access, metadata),
    )

    assert captured["actor"] == SHARED_URL_MACHINE_ACTOR
    assert captured["actor_name"] == SHARED_URL_DATA_ENTRY_ACTOR
    assert captured["user_id"] is None


def test_shared_url_actor_is_displayed_without_a_user_identity():
    event = _normalize_event(
        {
            "id": "event-1",
            "timestamp": "2026-10-23T10:00:00Z",
            "action": "entry_upserted",
            "payload": {
                "actor": SHARED_URL_MACHINE_ACTOR,
                "actor_name": SHARED_URL_DATA_ENTRY_ACTOR,
                "subject_raw": "ARIA08LE",
            },
        }
    )

    assert event["user"] == "Entered via shared URL"
    assert event["user_id"] is None
    assert event["summary"].startswith("Entered via shared URL Data entry saved")
