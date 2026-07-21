import json
import threading
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest

from eCRF_backend.datalad_repo import DataladStudyRepo
from eCRF_backend.forms_hybrid import _merge_submitted_entry_sections


def test_save_entry_rechecks_revision_inside_dataset_lock(tmp_path, monkeypatch):
    repo = DataladStudyRepo()
    paths = SimpleNamespace(dataset_path=tmp_path)
    latest = {
        "id": 7,
        "study_id": 1,
        "subject_index": 0,
        "visit_index": 0,
        "group_index": 0,
        "form_version": 1,
        "data": {"Vitals": {"temperature": "38.0"}},
        "skipped_required_flags": [],
        "created_at": "2026-07-17T10:00:00",
        "updated_at": "2026-07-17T10:01:00",
    }

    monkeypatch.setattr(repo, "ensure_dataset", lambda *_args, **_kwargs: paths)
    monkeypatch.setattr(
        repo,
        "get_latest_entry_for_slot",
        lambda **_kwargs: latest,
    )

    with pytest.raises(ValueError, match="Slot state changed"):
        repo.save_entry(
            study_id=1,
            study_name="Concurrent study",
            subject_index=0,
            visit_index=0,
            group_index=0,
            form_version=1,
            data={"Vitals": {"temperature": "37.0"}},
            skipped_required_flags=[],
            actor="tester",
            expected_revision_token="stale-token",
        )


def test_eight_simultaneous_saves_with_same_token_only_write_once(tmp_path, monkeypatch):
    repo = DataladStudyRepo()
    paths = SimpleNamespace(dataset_path=tmp_path)

    def stored_entries():
        rows = []
        for entry_path in tmp_path.glob("entry_*.json"):
            rows.append(json.loads(entry_path.read_text(encoding="utf-8")))
        return sorted(rows, key=lambda row: int(row["id"]))

    monkeypatch.setattr(repo, "ensure_dataset", lambda *_args, **_kwargs: paths)
    monkeypatch.setattr(
        repo,
        "get_latest_entry_for_slot",
        lambda **_kwargs: stored_entries()[-1] if stored_entries() else None,
    )
    monkeypatch.setattr(
        repo,
        "_next_entry_id",
        lambda _paths: len(stored_entries()) + 1,
    )
    monkeypatch.setattr(
        repo,
        "_entry_path",
        lambda _paths, **kwargs: tmp_path / f"entry_{int(kwargs['entry_id']):09d}.json",
    )
    monkeypatch.setattr(
        repo,
        "_resolve_subject_visit_group_labels",
        lambda *_args, **_kwargs: {},
    )
    monkeypatch.setattr(repo, "_build_actor_payload", lambda **_kwargs: {})
    monkeypatch.setattr(repo, "_append_audit", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(repo, "save", lambda *_args, **_kwargs: None)

    starting_token = repo.compute_entry_revision_token(None)
    clinician_count = 8
    barrier = threading.Barrier(clinician_count)

    def clinician_save(value):
        barrier.wait(timeout=5)
        try:
            repo.save_entry(
                study_id=1,
                study_name="Concurrent study",
                subject_index=0,
                visit_index=0,
                group_index=0,
                form_version=1,
                data={"Vitals": {"temperature": value}},
                skipped_required_flags=[],
                actor=value,
                expected_revision_token=starting_token,
            )
            return "saved"
        except ValueError:
            return "conflict"

    with ThreadPoolExecutor(max_workers=clinician_count) as executor:
        outcomes = list(
            executor.map(
                clinician_save,
                [f"clinician-{index + 1}" for index in range(clinician_count)],
            )
        )

    assert outcomes.count("saved") == 1
    assert outcomes.count("conflict") == clinician_count - 1
    assert len(stored_entries()) == 1


def test_shared_section_submission_preserves_hidden_and_unedited_data():
    latest = {
        "Vitals": {"pulse": 70, "temperature": 36.5},
        "Medication": {"drug": "A", "dose": "5 mg"},
        "Private notes": {"note": "not visible through this link"},
    }
    submitted = {
        "Vitals": {"temperature": 37.2},
    }

    merged = _merge_submitted_entry_sections(latest, submitted)

    assert merged == {
        "Vitals": {"pulse": 70, "temperature": 37.2},
        "Medication": {"drug": "A", "dose": "5 mg"},
        "Private notes": {"note": "not visible through this link"},
    }
    assert latest["Vitals"]["temperature"] == 36.5
