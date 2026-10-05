import pytest
from fastapi import HTTPException

from eCRF_backend.subject_ids import validate_new_subject_ids
from eCRF_backend.forms_hybrid import _validate_subject_identity_and_status_update


def study(*ids):
    return {"subjectIdConfig": {"mode": "manual"}, "subjects": [{"id": identifier, "group": "A"} for identifier in ids]}


def test_manual_enrollment_preserves_ids_and_allows_empty_skipped_setup():
    data = study("0008", "ARIA08LE", "Ab09")
    validate_new_subject_ids(data)
    assert [subject["id"] for subject in data["subjects"]] == ["0008", "ARIA08LE", "Ab09"]
    validate_new_subject_ids(study())


@pytest.mark.parametrize("ids", [("",), ("A", "A"), ("A", "a"), ("../bad",), ("A/B",), ("A B",)])
def test_invalid_manual_ids_rejected(ids):
    with pytest.raises(HTTPException) as error:
        validate_new_subject_ids(study(*ids))
    assert error.value.status_code == 400


def test_all_duplicate_ids_are_reported_without_mutating_input():
    data = study("BASE", "EXISTING", "existing", "DUP", "dup", "SECOND", "second")
    snapshot = [dict(subject) for subject in data["subjects"]]
    with pytest.raises(HTTPException) as error:
        validate_new_subject_ids(data, [{"id": "BASE"}, {"id": "EXISTING"}])
    assert '"existing", "dup", "second"' in error.value.detail
    assert "No subjects were added" in error.value.detail
    assert data["subjects"] == snapshot


def test_append_only_existing_subject_identity_and_status_protected():
    old = study("0008", "ARIA08LE")
    _validate_subject_identity_and_status_update(old, study("0008", "ARIA08LE", "NEW08"))
    for new in [study("0008"), study("ARIA08LE", "0008"), study("changed", "ARIA08LE"), study("0008", "ARIA08LE", "aria08le")]:
        with pytest.raises(HTTPException):
            _validate_subject_identity_and_status_update(old, new)


def test_legacy_ids_are_not_revalidated_or_rewritten():
    old = study("legacy id")
    updated = study("legacy id", "NEW08")
    _validate_subject_identity_and_status_update(old, updated)
    assert updated["subjects"][0] == old["subjects"][0]
