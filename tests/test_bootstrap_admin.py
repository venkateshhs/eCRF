from pydantic import EmailStr, TypeAdapter

from eCRF_backend.db_bootstrap import normalize_bootstrap_admin_email


def test_legacy_local_admin_email_is_repaired():
    repaired = normalize_bootstrap_admin_email("admin@case-e.local")

    assert repaired == "admin@case-e.org"
    assert TypeAdapter(EmailStr).validate_python(repaired) == repaired


def test_custom_valid_admin_email_is_preserved():
    assert normalize_bootstrap_admin_email("admin@clinic.org") == "admin@clinic.org"
