import json
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from eCRF_backend import forms_hybrid, schemas
from eCRF_backend.datalad_repo import DataladStudyRepo
from eCRF_backend.forms_hybrid import (
    _assert_entry_subject_update_allowed,
    _assert_subject_active,
    _validate_subject_identity_and_status_update,
)


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


@pytest.mark.parametrize(
    "role,user_id,permissions,mode,status,expected",
    [
        ("Principal Investigator", 2, {"view": True, "edit_study": True}, "keep_data", "PUBLISHED", 400),
        ("Principal Investigator", 2, {"view": True, "edit_study": True}, "delete_data", "PUBLISHED", 400),
        ("Principal Investigator", 2, {"view": True, "add_data": True}, "keep_data", "PUBLISHED", 403),
        ("Principal Investigator", 2, {"view": True, "add_data": True}, "delete_data", "PUBLISHED", 403),
        ("Principal Investigator", 2, {"view": False, "edit_study": True}, "keep_data", "PUBLISHED", 403),
        ("Investigator", 2, {"view": True, "edit_study": True}, "keep_data", "PUBLISHED", 403),
        ("Investigator", 2, {"view": True, "edit_study": True}, "delete_data", "PUBLISHED", 403),
        ("Principal Investigator", 2, {"view": True, "edit_study": True}, "keep_data", "ARCHIVED", 409),
        ("Investigator", 1, {}, "delete_data", "PUBLISHED", 400),
        ("Administrator", 2, {}, "delete_data", "PUBLISHED", 400),
    ],
)
def test_dropout_endpoint_permissions(role, user_id, permissions, mode, status, expected):
    meta = SimpleNamespace(id=11, created_by=1, status=status)
    grant = SimpleNamespace(permissions=permissions)
    user = SimpleNamespace(id=user_id, profile=SimpleNamespace(role=role))

    def query(model):
        return SimpleNamespace(filter=lambda *_: SimpleNamespace(
            first=lambda: meta if model is forms_hybrid.models.StudyMetadata else grant
        ))

    # An invalid date lets us verify who reaches validation without writing data.
    payload = schemas.SubjectDropoutRequest(
        mode=mode,
        dropout_date="invalid",
        reason="Disease progression with best support of care",
    )
    with pytest.raises(HTTPException) as exc:
        forms_hybrid.drop_out_subject(11, 0, payload, SimpleNamespace(query=query), user)
    assert exc.value.status_code == expected
    if expected == 400:
        assert exc.value.detail == "Dropout date must use YYYY-MM-DD"


def test_active_subject_guard_accepts_legacy_subject_and_blocks_dropout():
    assert _assert_subject_active({"subjects": [{"id": "SUB-001"}]}, 0)["id"] == "SUB-001"

    with pytest.raises(HTTPException) as exc:
        _assert_subject_active(
            {
                "subjects": [{
                    "id": "SUB-002",
                    "status": "DROPPED_DATA_RETAINED",
                    "dropout_date": "2026-08-06",
                }]
            },
            0,
        )
    assert exc.value.status_code == 409
    assert "SUB-002" in exc.value.detail


def test_generic_study_update_cannot_remove_reorder_or_change_dropout_status():
    old = {"subjects": [{"id": "SUB-001"}, {"id": "SUB-002", "status": "DROPPED_DATA_RETAINED"}]}

    with pytest.raises(HTTPException, match="cannot be removed"):
        _validate_subject_identity_and_status_update(old, {"subjects": old["subjects"][:1]})
    with pytest.raises(HTTPException, match="positions cannot be changed"):
        _validate_subject_identity_and_status_update(old, {"subjects": list(reversed(old["subjects"]))})
    with pytest.raises(HTTPException, match="Dropped subjects cannot be modified"):
        _validate_subject_identity_and_status_update(
            old,
            {"subjects": [{"id": "SUB-001"}, {"id": "SUB-002", "status": "DROPPED_DATA_RETAINED", "group": "B"}]},
        )


def test_entry_update_validates_existing_owner_and_prevents_subject_reassignment():
    study_data = {
        "subjects": [
            {"id": "SUB-001", "status": "DROPPED_DATA_RETAINED", "dropout_date": "2026-08-06"},
            {"id": "SUB-002", "status": "ACTIVE"},
            {"id": "SUB-003", "status": "ACTIVE"},
        ]
    }

    with pytest.raises(HTTPException) as dropped_owner:
        _assert_entry_subject_update_allowed(
            study_data,
            {"id": 77, "subject_index": 0},
            requested_subject_index=1,
        )
    assert dropped_owner.value.status_code == 409
    assert "SUB-001" in dropped_owner.value.detail

    with pytest.raises(HTTPException, match="cannot be moved") as reassignment:
        _assert_entry_subject_update_allowed(
            study_data,
            {"id": 78, "subject_index": 1},
            requested_subject_index=2,
        )
    assert reassignment.value.status_code == 409

    _assert_entry_subject_update_allowed(
        study_data,
        {"id": 78, "subject_index": 1},
        requested_subject_index=1,
    )


def test_delete_subject_active_data_removes_only_target_and_invalidates_links(tmp_path, monkeypatch):
    repo = DataladStudyRepo()
    canonical = tmp_path / "canonical"
    paths = SimpleNamespace(
        dataset_path=tmp_path,
        entries_dir=canonical / "entries",
        files_dir=canonical / "files",
        shares_dir=canonical / "shared_links",
    )
    paths.entries_dir.mkdir(parents=True)
    paths.files_dir.mkdir(parents=True)
    paths.shares_dir.mkdir(parents=True)
    monkeypatch.setattr(repo, "ensure_dataset", lambda *_args, **_kwargs: paths)
    monkeypatch.setattr(repo, "save", lambda *_args, **_kwargs: None)
    audits = []
    monkeypatch.setattr(repo, "_append_audit", lambda *_args, **kwargs: audits.append(kwargs))

    _write_json(paths.entries_dir / "entry_000000001.json", {"id": 1, "subject_index": 0})
    _write_json(paths.entries_dir / "entry_000000002.json", {"id": 2, "subject_index": 1})
    payload = paths.files_dir / "sub-0" / "scan.bin"
    payload.parent.mkdir(parents=True)
    payload.write_bytes(b"subject zero")
    _write_json(paths.files_dir / "file_000000001.json", {
        "id": 1,
        "study_id": 11,
        "subject_index": 0,
        "storage_option": "local",
        "file_path": str(payload.relative_to(tmp_path)),
    })
    _write_json(paths.files_dir / "file_000000002.json", {
        "id": 2,
        "study_id": 11,
        "subject_index": 1,
        "storage_option": "url",
        "file_path": "https://example.org/keep",
    })
    _write_json(paths.shares_dir / "target.json", {"subject_index": 0, "used_count": 1, "max_uses": 10})
    _write_json(paths.shares_dir / "keep.json", {"subject_index": 1, "used_count": 0, "max_uses": 10})

    counts = repo.delete_subject_active_data(
        study_id=11,
        study_name="Dropout test",
        subject_index=0,
        audit_payload={"subject_raw": "SUB-001"},
    )

    assert counts == {"entries_deleted": 1, "files_deleted": 1, "shared_links_revoked": 1}
    assert not (paths.entries_dir / "entry_000000001.json").exists()
    assert (paths.entries_dir / "entry_000000002.json").exists()
    assert not payload.exists()
    assert (paths.files_dir / "file_000000002.json").exists()
    invalidated = json.loads((paths.shares_dir / "target.json").read_text())
    assert invalidated["max_uses"] == invalidated["used_count"] == 1
    assert json.loads((paths.shares_dir / "keep.json").read_text())["max_uses"] == 10
    assert audits[0]["action"] == "subject_dropped_delete_data"
    assert audits[0]["payload"]["entries_deleted"] == 1
