from __future__ import annotations

from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.requests import Request

from eCRF_backend import models, users
from eCRF_backend.auth import hash_password, verify_password


def _request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/users/password-reset",
            "headers": [],
            "query_string": b"",
            "scheme": "https",
            "server": ("casee.example.org", 443),
            "client": ("192.0.2.10", 12345),
        }
    )


@pytest.fixture()
def db(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'reset.db'}")
    models.Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    reset_settings = SimpleNamespace(
        password_reset_enabled=True,
        password_reset_confirmation_ttl_minutes=10,
        password_reset_ttl_minutes=20,
        password_reset_max_per_user_hour=3,
        password_reset_max_lookups_per_ip_hour=10,
        trust_proxy_headers=False,
    )
    monkeypatch.setattr(users, "settings", reset_settings)
    monkeypatch.setattr(users, "audit_change_both", lambda **kwargs: None)
    yield session
    session.close()


def _add_user(db):
    user = models.User(
        username="nurse.one",
        email="nurse.one@example.org",
        password=hash_password("OldPassword1!"),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_complete_password_reset_flow_revokes_sessions(db, monkeypatch):
    user = _add_user(db)
    session = models.UserSession(
        user_id=user.id,
        jti="existing-session",
        absolute_expires_at=users.local_now(),
    )
    db.add(session)
    db.commit()

    sent = {}
    monkeypatch.setattr(
        users,
        "build_reset_url",
        lambda token: f"https://casee.example.org/reset-password?token={token}",
    )
    monkeypatch.setattr(users, "send_password_reset_email", lambda **kwargs: sent.update(kwargs))

    lookup = users.password_reset_lookup(
        users.PasswordResetLookupRequest(username="nurse.one"),
        _request(),
        db,
    )
    assert lookup.eligible is True
    assert lookup.masked_email == "n********@example.org"
    assert "nurse.one" not in lookup.masked_email

    result = users.password_reset_request_email(
        users.PasswordResetEmailRequest(confirmation_token=lookup.confirmation_token),
        _request(),
        db,
    )
    assert result["message"] == "Password reset email sent."
    assert sent["recipient"] == "nurse.one@example.org"
    raw_reset_token = parse_qs(urlparse(sent["reset_url"]).query)["token"][0]

    result = users.password_reset_confirm(
        users.PasswordResetConfirmRequest(
            token=raw_reset_token,
            new_password="NewPassword2!",
        ),
        db,
    )
    assert result["message"] == "Password reset successfully."

    db.refresh(user)
    db.refresh(session)
    assert verify_password("NewPassword2!", user.password)
    assert user.must_change_password is False
    assert session.revoked_at is not None

    with pytest.raises(HTTPException) as reused:
        users.password_reset_confirm(
            users.PasswordResetConfirmRequest(
                token=raw_reset_token,
                new_password="AnotherPassword3!",
            ),
            db,
        )
    assert reused.value.status_code == 400


def test_unknown_username_does_not_expose_an_email(db):
    response = users.password_reset_lookup(
        users.PasswordResetLookupRequest(username="missing-user"),
        _request(),
        db,
    )
    assert response.eligible is False
    assert response.masked_email is None
    assert response.confirmation_token is None


def test_weak_password_is_rejected_before_token_lookup(db):
    with pytest.raises(HTTPException) as rejected:
        users.password_reset_confirm(
            users.PasswordResetConfirmRequest(token="x" * 32, new_password="too-weak"),
            db,
        )
    assert rejected.value.status_code == 400
    assert "special character" in rejected.value.detail
