import json
from types import SimpleNamespace

import pytest

from eCRF_backend.datalad_repo import DataladStudyRepo


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _file_record(file_id, file_path, *, storage_option="bids", modalities=None):
    return {
        "id": file_id,
        "study_id": 11,
        "file_name": "scan.nii.gz",
        "file_path": file_path,
        "description": "MRI",
        "storage_option": storage_option,
        "subject_index": 0,
        "visit_index": 1,
        "group_index": 0,
        "modalities": modalities or ["MRI"],
        "form_version": 1,
        "created_at": "2026-07-31T10:00:00",
    }


def _configured_repo(tmp_path, monkeypatch):
    repo = DataladStudyRepo()
    files_dir = tmp_path / "canonical" / "files"
    paths = SimpleNamespace(dataset_path=tmp_path, files_dir=files_dir)
    audits = []

    monkeypatch.setattr(repo, "paths", lambda *_args, **_kwargs: paths)
    monkeypatch.setattr(
        repo,
        "_resolve_subject_visit_group_labels",
        lambda *_args, **_kwargs: {},
    )
    monkeypatch.setattr(repo, "_append_audit", lambda *_args, **kwargs: audits.append(kwargs))
    monkeypatch.setattr(repo, "save", lambda *_args, **_kwargs: None)
    return repo, files_dir, audits


def test_delete_file_removes_only_exact_payload_and_metadata_record(tmp_path, monkeypatch):
    repo, files_dir, audits = _configured_repo(tmp_path, monkeypatch)
    first_payload = files_dir / "v001" / "sub-001" / "ses-01" / "mri" / "000000001_scan.nii.gz"
    second_payload = files_dir / "v001" / "sub-001" / "ses-01" / "ct" / "000000002_scan.nii.gz"
    first_payload.parent.mkdir(parents=True, exist_ok=True)
    second_payload.parent.mkdir(parents=True, exist_ok=True)
    first_payload.write_bytes(b"first")
    second_payload.write_bytes(b"second")

    first_record = _file_record(1, str(first_payload.relative_to(tmp_path)))
    second_record = _file_record(
        2,
        str(second_payload.relative_to(tmp_path)),
        modalities=["CT"],
    )
    _write_json(files_dir / "file_000000001.json", first_record)
    _write_json(files_dir / "file_000000002.json", second_record)

    deleted = repo.delete_file(
        study_id=11,
        study_name="Deletion test",
        file_id=1,
        actor="clinician@example.org",
        actor_name="Test Clinician",
        user_id=7,
        audit_label="Delete File",
    )

    assert deleted == first_record
    assert not first_payload.exists()
    assert not (files_dir / "file_000000001.json").exists()
    assert second_payload.read_bytes() == b"second"
    assert (files_dir / "file_000000002.json").exists()
    assert audits[0]["action"] == "file_deleted"
    assert audits[0]["payload"]["file_id"] == 1
    assert audits[0]["payload"]["modalities"] == ["MRI"]


def test_delete_url_file_removes_metadata_without_touching_external_url(tmp_path, monkeypatch):
    repo, files_dir, audits = _configured_repo(tmp_path, monkeypatch)
    record = _file_record(
        3,
        "https://example.org/files/report.pdf",
        storage_option="url",
        modalities=["Clinical document"],
    )
    _write_json(files_dir / "file_000000003.json", record)

    repo.delete_file(
        study_id=11,
        study_name="Deletion test",
        file_id=3,
        actor="clinician@example.org",
    )

    assert not (files_dir / "file_000000003.json").exists()
    assert audits[0]["payload"]["storage_option"] == "url"


def test_delete_study_level_file_removes_payload_from_metadata_directory(tmp_path, monkeypatch):
    repo, files_dir, _audits = _configured_repo(tmp_path, monkeypatch)
    payload = files_dir / "metadata" / "000000005_protocol.pdf"
    payload.parent.mkdir(parents=True, exist_ok=True)
    payload.write_bytes(b"protocol")
    record = _file_record(5, str(payload.relative_to(tmp_path)), modalities=[])
    record.update(
        {
            "file_name": "protocol.pdf",
            "subject_index": None,
            "visit_index": None,
            "group_index": None,
        }
    )
    _write_json(files_dir / "file_000000005.json", record)

    repo.delete_file(
        study_id=11,
        study_name="Deletion test",
        file_id=5,
        actor="clinician@example.org",
    )

    assert not payload.exists()
    assert not (files_dir / "file_000000005.json").exists()


def test_delete_git_annex_symlink_unlinks_dataset_file_without_following_it(
    tmp_path, monkeypatch
):
    repo, files_dir, _audits = _configured_repo(tmp_path, monkeypatch)
    annex_object = (
        tmp_path
        / ".git"
        / "annex"
        / "objects"
        / "key"
        / "MD5E-s4--scan.nii.gz"
    )
    annex_object.parent.mkdir(parents=True, exist_ok=True)
    annex_object.write_bytes(b"annex payload")

    payload = files_dir / "v001" / "sub-001" / "mri" / "000000006_scan.nii.gz"
    payload.parent.mkdir(parents=True, exist_ok=True)
    payload.symlink_to(annex_object)
    record = _file_record(6, str(payload.relative_to(tmp_path)))
    _write_json(files_dir / "file_000000006.json", record)

    repo.delete_file(
        study_id=11,
        study_name="Deletion test",
        file_id=6,
        actor="clinician@example.org",
    )

    assert not payload.is_symlink()
    assert annex_object.read_bytes() == b"annex payload"
    assert not (files_dir / "file_000000006.json").exists()


def test_delete_file_rejects_payload_outside_file_storage(tmp_path, monkeypatch):
    repo, files_dir, _audits = _configured_repo(tmp_path, monkeypatch)
    protected = tmp_path / "canonical" / "study_content.json"
    protected.parent.mkdir(parents=True, exist_ok=True)
    protected.write_text('{"keep": true}', encoding="utf-8")
    record = _file_record(4, str(protected.relative_to(tmp_path)))
    record_path = files_dir / "file_000000004.json"
    _write_json(record_path, record)

    with pytest.raises(ValueError, match="outside study file storage"):
        repo.delete_file(
            study_id=11,
            study_name="Deletion test",
            file_id=4,
            actor="clinician@example.org",
        )

    assert protected.exists()
    assert record_path.exists()


def test_delete_file_rejects_intermediate_symlink_escape(tmp_path, monkeypatch):
    repo, files_dir, _audits = _configured_repo(tmp_path, monkeypatch)
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir(parents=True, exist_ok=True)
    protected = outside_dir / "protected.bin"
    protected.write_bytes(b"keep")

    files_dir.mkdir(parents=True, exist_ok=True)
    escape = files_dir / "escape"
    escape.symlink_to(outside_dir, target_is_directory=True)
    record = _file_record(
        7,
        str((files_dir / "escape" / "protected.bin").relative_to(tmp_path)),
    )
    record_path = files_dir / "file_000000007.json"
    _write_json(record_path, record)

    with pytest.raises(ValueError, match="outside study file storage"):
        repo.delete_file(
            study_id=11,
            study_name="Deletion test",
            file_id=7,
            actor="clinician@example.org",
        )

    assert protected.read_bytes() == b"keep"
    assert record_path.exists()


def test_update_file_description_preserves_payload_and_other_metadata(tmp_path, monkeypatch):
    repo, files_dir, audits = _configured_repo(tmp_path, monkeypatch)
    payload = files_dir / "metadata" / "000000008_protocol.pdf"
    payload.parent.mkdir(parents=True, exist_ok=True)
    payload.write_bytes(b"protocol")
    record = _file_record(8, str(payload.relative_to(tmp_path)), modalities=[])
    record.update(
        {
            "file_name": "protocol.pdf",
            "subject_index": None,
            "visit_index": None,
            "group_index": None,
        }
    )
    record_path = files_dir / "file_000000008.json"
    _write_json(record_path, record)

    updated = repo.update_file_description(
        study_id=11,
        study_name="Description test",
        file_id=8,
        description="  Approved protocol v2  ",
        actor="clinician@example.org",
    )

    assert payload.read_bytes() == b"protocol"
    assert updated["description"] == "Approved protocol v2"
    assert json.loads(record_path.read_text(encoding="utf-8"))["modalities"] == ["MRI"]
    assert audits[0]["action"] == "file_description_updated"
    assert audits[0]["payload"]["previous_description"] == "MRI"


def test_update_file_description_can_clear_description(tmp_path, monkeypatch):
    repo, files_dir, audits = _configured_repo(tmp_path, monkeypatch)
    record = _file_record(9, "https://example.org/protocol", storage_option="url")
    record_path = files_dir / "file_000000009.json"
    _write_json(record_path, record)

    updated = repo.update_file_description(
        study_id=11,
        study_name="Description test",
        file_id=9,
        description="   ",
        actor="clinician@example.org",
    )

    assert updated["description"] == ""
    assert audits[0]["payload"]["description"] == ""
