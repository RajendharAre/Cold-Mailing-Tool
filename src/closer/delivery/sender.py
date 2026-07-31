"""Email delivery adapters (dry-run and SMTP)."""

from __future__ import annotations

import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import Literal

from closer.config import AppConfig
from closer.domain import Contact, DeliveryResult, EmailDraft

DeliveryMode = Literal["draft", "send"]


def deliver_email(
    draft: EmailDraft,
    contact: Contact,
    config: AppConfig,
    mode: DeliveryMode,
) -> DeliveryResult:
    """Deliver an email via dry-run simulation or SMTP."""
    if config.dry_run:
        return _deliver_dry_run(draft, contact, mode)
    return _deliver_smtp(draft, contact, config, mode)


def _deliver_dry_run(
    draft: EmailDraft,
    contact: Contact,
    mode: DeliveryMode,
) -> DeliveryResult:
    verb = "send" if mode == "send" else "create draft for"
    print(
        f"[dry-run] Simulated {verb} {contact.recipient_email} "
        f"— subject: {draft.subject!r}"
    )
    status = "sent" if mode == "send" else "drafted"
    return DeliveryResult(
        status=status,
        provider_message_id="dry-run-simulated",
    )


def _deliver_smtp(
    draft: EmailDraft,
    contact: Contact,
    config: AppConfig,
    mode: DeliveryMode,
) -> DeliveryResult:
    if mode == "draft":
        return DeliveryResult(
            status="failed",
            error=(
                "SMTP cannot create Gmail drafts. Choose 'send' for a real email, "
                "or set DRY_RUN=true to simulate a draft."
            ),
        )

    subject = draft.subject.strip().replace("\n", " ").replace("\r", " ")
    body = draft.body.strip()
    if not subject or not body:
        return DeliveryResult(
            status="failed",
            error="Cannot send email with empty subject or body.",
        )

    if not config.smtp_user or not config.smtp_password:
        return DeliveryResult(
            status="failed",
            error="SMTP_USER and SMTP_PASSWORD are required when DRY_RUN=false.",
        )

    try:
        message = _build_message(
            subject=subject,
            body=body,
            to_email=contact.recipient_email,
            from_email=config.smtp_user,
            sender_name=config.sender_name,
        )
        _send_via_smtp(message, config, contact.recipient_email)
        print(f"Email sent to {contact.recipient_email}. Check your Gmail Sent folder.")
        return DeliveryResult(status="sent", provider_message_id=None)
    except smtplib.SMTPAuthenticationError as exc:
        return DeliveryResult(
            status="failed",
            error=(
                "SMTP authentication failed. Verify SMTP_USER and SMTP_PASSWORD "
                "(use a Gmail App Password, not your regular password). "
                f"Details: {exc}"
            ),
        )
    except smtplib.SMTPException as exc:
        return DeliveryResult(status="failed", error=f"SMTP error: {exc}")
    except OSError as exc:
        return DeliveryResult(status="failed", error=f"Connection error: {exc}")


def _build_message(
    subject: str,
    body: str,
    to_email: str,
    from_email: str,
    sender_name: str | None,
) -> MIMEText:
    message = MIMEText(body, "plain", "utf-8")
    message["Subject"] = subject
    message["To"] = to_email
    if sender_name:
        message["From"] = formataddr((sender_name, from_email))
    else:
        message["From"] = from_email
    return message


def _send_via_smtp(message: MIMEText, config: AppConfig, to_email: str) -> None:
    with smtplib.SMTP(config.smtp_host, config.smtp_port, timeout=30) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(config.smtp_user, config.smtp_password)
        server.sendmail(
            config.smtp_user,
            [to_email],
            message.as_string(),
        )
