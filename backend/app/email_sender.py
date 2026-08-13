from __future__ import annotations

import smtplib
from email.message import EmailMessage
from typing import List

from .config import load_settings

_settings = load_settings()


class EmailSendError(Exception):
    pass


def send_email_mock(
    sender: str,
    recipients: List[str],
    subject: str,
    body: str,
) -> None:
    """
    Mock sending via local SMTP (Mailpit).
    Uses localhost:1025, no auth.
    """
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        with smtplib.SMTP("127.0.0.1", 1025, timeout=10) as smtp:
            smtp.send_message(msg)
    except Exception as exc:  # noqa: BLE001
        raise EmailSendError(f"Mock email send failed: {exc}") from exc


def send_email_real(
    sender: str,
    recipients: List[str],
    subject: str,
    body: str,
) -> None:
    """
    Stub for real sending (e.g., Brevo).

    TODO: Implement Brevo SMTP/API integration here.
    For now, we raise a clear error to avoid accidental real sends.
    """
    raise EmailSendError(
        "Real email sending is not yet implemented. Configure Brevo/SMTP here when ready."
    )


def send_email(
    sender: str,
    recipients: List[str],
    subject: str,
    body: str,
) -> None:
    """
    Dispatch send based on EMAIL_MODE: 'mock' vs 'real'.
    """
    mode = _settings.email_mode.lower()
    if mode == "mock":
        return send_email_mock(sender, recipients, subject, body)
    if mode == "real":
        return send_email_real(sender, recipients, subject, body)

    raise EmailSendError(f"Unsupported EMAIL_MODE: {mode}")
