from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from starlette.requests import Request

from eCRF_backend import forms_hybrid, models, schemas


class _Query:
    def __init__(self, result):
        self.result = result

    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
        return self.result


class _Db:
    def __init__(self, meta):
        self.meta = meta
        self.added = None
        self.committed = False
        self.rolled_back = False

    def query(self, *_args, **_kwargs):
        return _Query(self.meta)

    def add(self, value):
        self.added = value

    def flush(self):
        return None

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def refresh(self, *_args, **_kwargs):
        return None


def _request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/forms/share-link/",
            "headers": [(b"host", b"casee.example.org")],
            "query_string": b"",
            "scheme": "https",
            "server": ("casee.example.org", 443),
            "client": ("192.0.2.10", 12345),
        }
    )


def _payload(email="patient@example.org"):
    return schemas.ShareLinkCreate(
        study_id=1,
        subject_index=0,
        visit_index=0,
        group_index=0,
        allowed_section_ids=["section-1"],
        recipient_email=email,
    )


@pytest.fixture()
def share_endpoint(monkeypatch):
    content = SimpleNamespace(
        study_data={
            "subjects": [{"id": "SUB-001", "status": "ACTIVE"}],
            "selectedModels": [{"_id": "section-1"}],
            "assignments": [[[True]]],
        }
    )
    monkeypatch.setattr(forms_hybrid, "_assert_has_study_permission", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(forms_hybrid, "_assert_not_locked_by_other", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(forms_hybrid, "_get_content_row_or_404", lambda *_args, **_kwargs: content)


def test_recipient_email_is_not_a_persisted_shared_link_column():
    assert "recipient_email" not in models.SharedFormAccess.__table__.columns


def test_share_link_recipient_requires_a_valid_email():
    with pytest.raises(ValidationError):
        _payload("not-an-email")


def test_share_link_sends_email_without_persisting_or_exporting_it(share_endpoint, monkeypatch):
    db = _Db(SimpleNamespace(id=1, study_name="Test study"))
    sent = {}
    saved = {}
    monkeypatch.setattr(forms_hybrid, "shared_link_email_configured", lambda: True)
    monkeypatch.setattr(forms_hybrid, "send_shared_link_email", lambda **kwargs: sent.update(kwargs))
    monkeypatch.setattr(forms_hybrid.repo, "save_share_link", lambda **kwargs: saved.update(kwargs))

    response = forms_hybrid.create_share_link(
        _payload(),
        _request(),
        db,
        SimpleNamespace(id=9),
    )

    assert response["email_sent"] is True
    assert sent["recipient"] == "patient@example.org"
    assert "patient@example.org" not in repr(db.added.__dict__)
    assert "recipient" not in saved
    assert "email" not in saved
    assert db.committed is True


def test_failed_delivery_keeps_link_available_for_manual_sharing(share_endpoint, monkeypatch):
    db = _Db(SimpleNamespace(id=1, study_name="Test study"))
    saved = {}

    def fail_delivery(**_kwargs):
        raise TimeoutError("SMTP timeout")

    monkeypatch.setattr(forms_hybrid, "shared_link_email_configured", lambda: True)
    monkeypatch.setattr(forms_hybrid, "send_shared_link_email", fail_delivery)
    monkeypatch.setattr(forms_hybrid.repo, "save_share_link", lambda **kwargs: saved.update(kwargs))

    response = forms_hybrid.create_share_link(
        _payload(),
        _request(),
        db,
        SimpleNamespace(id=9),
    )

    assert response["email_sent"] is False
    assert response["email_delivery_status"] == "failed"
    assert response["link"]
    assert db.rolled_back is False
    assert db.committed is True
    assert saved["token"] == response["token"]


def test_missing_smtp_creates_link_without_attempting_delivery(share_endpoint, monkeypatch):
    db = _Db(SimpleNamespace(id=1, study_name="Test study"))
    saved = {}

    monkeypatch.setattr(forms_hybrid, "shared_link_email_configured", lambda: False)
    monkeypatch.setattr(
        forms_hybrid,
        "send_shared_link_email",
        lambda **_kwargs: pytest.fail("SMTP delivery must not be attempted"),
    )
    monkeypatch.setattr(forms_hybrid.repo, "save_share_link", lambda **kwargs: saved.update(kwargs))

    response = forms_hybrid.create_share_link(
        _payload(),
        _request(),
        db,
        SimpleNamespace(id=9),
    )

    assert response["email_sent"] is False
    assert response["email_delivery_available"] is False
    assert response["email_delivery_status"] == "unavailable"
    assert response["link"]
    assert db.committed is True
    assert saved["token"] == response["token"]
