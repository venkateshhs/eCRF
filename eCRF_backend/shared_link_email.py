from __future__ import annotations

import html
import smtplib
import ssl
from datetime import datetime
from email.message import EmailMessage

from .settings import get_settings


settings = get_settings()


def send_shared_link_email(
    *,
    recipient: str,
    shared_url: str,
    expires_at: datetime,
) -> None:
    """Send a shared-form link without retaining or logging the recipient."""
    safe_url = html.escape(shared_url, quote=True)
    expiry_text = expires_at.strftime("%Y-%m-%d %H:%M UTC")

    message = EmailMessage()
    message["Subject"] = "Your secure case-e form link"
    message["From"] = settings.mail_from
    message["To"] = recipient
    message.set_content(
        "You have been invited to access a secure case-e form.\n\n"
        f"Open the form using this link:\n{shared_url}\n\n"
        f"The link expires on {expiry_text}. Do not forward this email or link.\n"
    )
    message.add_alternative(
        "<p>You have been invited to access a secure case-e form.</p>"
        f'<p><a href="{safe_url}">Open the secure form</a></p>'
        f"<p>The link expires on {expiry_text}. Do not forward this email or link.</p>",
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
