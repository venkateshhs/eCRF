from __future__ import annotations

import hashlib
import html
import secrets
import smtplib
import ssl
from email.message import EmailMessage
from urllib.parse import quote

from .settings import get_settings


settings = get_settings()


def new_token() -> str:
    return secrets.token_urlsafe(32)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def mask_email(address: str) -> str:
    """Return a useful address hint without exposing the complete address."""
    local, separator, domain = (address or "").strip().partition("@")
    if not separator or not local or not domain:
        return "hidden address"
    visible = local[0]
    return f"{visible}{'*' * max(3, len(local) - 1)}@{domain}"


def build_reset_url(token: str) -> str:
    return f"{settings.frontend_base_url}/reset-password?token={quote(token, safe='')}"


def send_password_reset_email(*, recipient: str, username: str, reset_url: str) -> None:
    """Send a reset link using the configured authenticated or relay SMTP server."""
    safe_username = html.escape(username)
    safe_url = html.escape(reset_url, quote=True)

    message = EmailMessage()
    message["Subject"] = "Reset your case-e password"
    message["From"] = settings.mail_from
    message["To"] = recipient
    message.set_content(
        "Hello {username},\n\n"
        "A password reset was requested for your case-e account.\n\n"
        "Open this link to choose a new password:\n{url}\n\n"
        "This link expires in {minutes} minutes and can be used only once. "
        "If you did not request this, you can ignore this email.\n".format(
            username=username,
            url=reset_url,
            minutes=settings.password_reset_ttl_minutes,
        )
    )
    message.add_alternative(
        """
        <p>Hello {username},</p>
        <p>A password reset was requested for your case-e account.</p>
        <p><a href="{url}">Choose a new password</a></p>
        <p>This link expires in {minutes} minutes and can be used only once.</p>
        <p>If you did not request this, you can ignore this email.</p>
        """.format(
            username=safe_username,
            url=safe_url,
            minutes=settings.password_reset_ttl_minutes,
        ),
        subtype="html",
    )

    smtp_class = smtplib.SMTP_SSL if settings.smtp_ssl else smtplib.SMTP
    smtp_kwargs = {
        "host": settings.smtp_host,
        "port": settings.smtp_port,
        "timeout": settings.smtp_timeout_seconds,
    }
    if settings.smtp_ssl:
        smtp_kwargs["context"] = ssl.create_default_context()

    with smtp_class(**smtp_kwargs) as session:
        if settings.smtp_starttls:
            session.starttls(context=ssl.create_default_context())
        if settings.smtp_username:
            session.login(settings.smtp_username, settings.smtp_password)
        session.send_message(message)
