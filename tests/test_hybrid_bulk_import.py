import json
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from eCRF_backend import forms_hybrid, models, schemas
from eCRF_backend.datalad_repo import DataladStudyRepo


def _entry(subject_index, visit_index, group_index=0):
    return {
        "subject_index": subject_index,
        "visit_index": visit_index,
        "group_index": group_index,
        "data": {"Imported Fields": {"value": f"{subject_index}-{visit_index}"}},
        "skipped_required_flags": [],
    }


def test_repo_bulk_save_writes_all_entries_with_one_datalad_save(tmp_path, monkeypatch):
    repo = DataladStudyRepo()
    paths = SimpleNamespace(dataset_path=tmp_path)
    save_calls = []
    audit_calls = []

    monkeypatch.setattr(repo, "ensure_dataset", lambda *_args, **_kwargs: paths)
    monkeypatch.setattr(repo, "list_entries", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        repo,
        "_entry_path",
        lambda _paths, **kwargs: tmp_path / f"entry_{int(kwargs['entry_id']):09d}.json",
    )
    monkeypatch.setattr(repo, "_resolve_subject_visit_group_labels", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(repo, "_append_audit", lambda *_args, **kwargs: audit_calls.append(kwargs))
    monkeypatch.setattr(repo, "save", lambda *args, **_kwargs: save_calls.append(args))

    written = repo.save_entries_bulk(
        study_id=11,
        study_name="Bulk import study",
        form_version=1,
        entries=[_entry(0, 0), _entry(0, 1), _entry(1, 0)],
        actor="admin@example.test",
        actor_name="Admin User",
        user_id=1,
        audit_label="Study Data Import",
    )

    assert [row["id"] for row in written] == [1, 2, 3]
    assert len(save_calls) == 1
    assert "count=3" in save_calls[0][1]
    assert len(audit_calls) == 3
    stored = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(tmp_path.glob("entry_*.json"))
    ]
    assert stored == written


@pytest.mark.parametrize(
    "existing, entries, message",
    [
        ([_entry(0, 0) | {"id": 7, "form_version": 1}], [_entry(0, 0)], "already contains data"),
        ([], [_entry(0, 0), _entry(0, 0)], "more than one row"),
    ],
)
def test_repo_bulk_save_rejects_occupied_or_duplicate_slots_atomically(
    tmp_path,
    monkeypatch,
    existing,
    entries,
    message,
):
    repo = DataladStudyRepo()
    paths = SimpleNamespace(dataset_path=tmp_path)
    save_calls = []

    monkeypatch.setattr(repo, "ensure_dataset", lambda *_args, **_kwargs: paths)
    monkeypatch.setattr(repo, "list_entries", lambda *_args, **_kwargs: existing)
    monkeypatch.setattr(repo, "save", lambda *args, **_kwargs: save_calls.append(args))

    with pytest.raises(ValueError, match=message):
        repo.save_entries_bulk(
            study_id=11,
            study_name="Bulk import study",
            form_version=1,
            entries=entries,
            actor="admin@example.test",
        )

    assert save_calls == []
    assert list(tmp_path.glob("entry_*.json")) == []


class _Query:
    def __init__(self, value):
        self.value = value

    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
        return self.value


class _Db:
    def __init__(self, metadata):
        self.metadata = metadata

    def query(self, model):
        assert model is models.StudyMetadata
        return _Query(self.metadata)


def test_hybrid_bulk_route_uses_repo_batch_and_returns_legacy_shape(monkeypatch):
    metadata = SimpleNamespace(id=11, study_name="Bulk import study", status="PUBLISHED")
    content = SimpleNamespace(
        study_data={
            "selectedModels": [],
            "subjects": [{"status": "ACTIVE"}, {"status": "ACTIVE"}],
        }
    )
    user = SimpleNamespace(id=1, email="admin@example.test", username="admin", profile=None)
    captured = {}

    monkeypatch.setattr(forms_hybrid, "_assert_has_study_permission", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(forms_hybrid, "_assert_not_locked_by_other", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(forms_hybrid, "_resolve_form_version_or_400", lambda *_args, **_kwargs: 1)
    monkeypatch.setattr(forms_hybrid, "_get_content_row_or_404", lambda *_args, **_kwargs: content)

    def save_entries_bulk(**kwargs):
        captured.update(kwargs)
        return [{"id": 1}, {"id": 2}]

    monkeypatch.setattr(forms_hybrid.repo, "save_entries_bulk", save_entries_bulk)

    response = forms_hybrid.bulk_insert_data(
        study_id=11,
        payload=schemas.BulkPayload(
            entries=[
                schemas.StudyDataEntryCreate(**_entry(0, 0)),
                schemas.StudyDataEntryCreate(**_entry(0, 1)),
            ]
        ),
        version=None,
        create_bids=False,
        audit_label=None,
        db=_Db(metadata),
        current_user=user,
    )

    assert response == {"inserted": 2, "failed": 0, "errors": []}
    assert captured["study_id"] == 11
    assert captured["form_version"] == 1
    assert captured["require_empty_slots"] is True
    assert captured["audit_label"] == "Study Data Import"
    assert len(captured["entries"]) == 2


def test_hybrid_bulk_route_reports_slot_conflict(monkeypatch):
    metadata = SimpleNamespace(id=11, study_name="Bulk import study", status="PUBLISHED")
    content = SimpleNamespace(
        study_data={
            "selectedModels": [],
            "subjects": [{"status": "ACTIVE"}],
        }
    )
    user = SimpleNamespace(id=1, email="admin@example.test", username="admin", profile=None)

    monkeypatch.setattr(forms_hybrid, "_assert_has_study_permission", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(forms_hybrid, "_assert_not_locked_by_other", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(forms_hybrid, "_resolve_form_version_or_400", lambda *_args, **_kwargs: 1)
    monkeypatch.setattr(forms_hybrid, "_get_content_row_or_404", lambda *_args, **_kwargs: content)
    monkeypatch.setattr(
        forms_hybrid.repo,
        "save_entries_bulk",
        lambda **_kwargs: (_ for _ in ()).throw(ValueError("slot already contains data")),
    )

    with pytest.raises(HTTPException) as exc_info:
        forms_hybrid.bulk_insert_data(
            study_id=11,
            payload=schemas.BulkPayload(entries=[schemas.StudyDataEntryCreate(**_entry(0, 0))]),
            version=None,
            create_bids=False,
            audit_label=None,
            db=_Db(metadata),
            current_user=user,
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["conflict"] is True


def _progress_entry_payload():
    return schemas.StudyDataEntryCreate(
        **_entry(0, 0),
        progress_status="complete",
        progress_percentage=100,
        progress_completed=30,
        progress_total=30,
        progress_skipped=0,
    )


def _patch_regular_entry_route_dependencies(monkeypatch, content):
    monkeypatch.setattr(forms_hybrid, "_assert_has_study_permission", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(forms_hybrid, "_assert_not_locked_by_other", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(forms_hybrid, "_assert_subject_active_for_study", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(forms_hybrid, "_assert_entry_subject_update_allowed", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(forms_hybrid, "_resolve_form_version_or_400", lambda *_args, **_kwargs: 1)
    monkeypatch.setattr(forms_hybrid, "_get_content_row_or_404", lambda *_args, **_kwargs: content)
    monkeypatch.setattr(forms_hybrid.repo, "assert_slot_revision_unchanged", lambda **_kwargs: None)


def test_regular_create_route_persists_frontend_progress_snapshot(monkeypatch):
    metadata = SimpleNamespace(id=11, study_name="Progress study", status="PUBLISHED")
    content = SimpleNamespace(study_data={"selectedModels": []})
    user = SimpleNamespace(id=1, email="admin@example.test", username="admin", profile=None)
    captured = {}
    _patch_regular_entry_route_dependencies(monkeypatch, content)

    monkeypatch.setattr(
        forms_hybrid.repo,
        "save_entry",
        lambda **kwargs: captured.update(kwargs) or kwargs,
    )

    forms_hybrid.save_study_data(
        study_id=11,
        payload=_progress_entry_payload(),
        version=None,
        expected_revision_token="revision-1",
        audit_label="New Data Entry",
        db=_Db(metadata),
        current_user=user,
    )

    assert captured["progress_status"] == "complete"
    assert captured["progress_percentage"] == 100
    assert captured["progress_completed"] == 30
    assert captured["progress_total"] == 30
    assert captured["progress_skipped"] == 0


def test_regular_update_route_persists_frontend_progress_snapshot(monkeypatch):
    metadata = SimpleNamespace(id=11, study_name="Progress study", status="PUBLISHED")
    content = SimpleNamespace(study_data={"selectedModels": []})
    user = SimpleNamespace(id=1, email="admin@example.test", username="admin", profile=None)
    captured = {}
    _patch_regular_entry_route_dependencies(monkeypatch, content)
    monkeypatch.setattr(
        forms_hybrid.repo,
        "list_entries",
        lambda *_args, **_kwargs: [{"id": 51, "subject_index": 0, "form_version": 1}],
    )
    monkeypatch.setattr(
        forms_hybrid.repo,
        "update_entry",
        lambda **kwargs: captured.update(kwargs) or kwargs["payload"],
    )

    forms_hybrid.update_study_data_entry(
        study_id=11,
        entry_id=51,
        payload=_progress_entry_payload(),
        expected_revision_token="revision-1",
        audit_label="Update/Edit Data Entry",
        db=_Db(metadata),
        user=user,
    )

    stored_payload = captured["payload"]
    assert stored_payload["progress_status"] == "complete"
    assert stored_payload["progress_percentage"] == 100
    assert stored_payload["progress_completed"] == 30
    assert stored_payload["progress_total"] == 30
    assert stored_payload["progress_skipped"] == 0
