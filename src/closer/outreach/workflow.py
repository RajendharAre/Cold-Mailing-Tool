"""Reusable outreach actions (generate → confirm → deliver → log)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from closer.audit import append_log
from closer.config import AppConfig
from closer.delivery import deliver_email
from closer.domain import Contact, DeliveryResult, EmailDraft, LogEntry
from closer.tracking import append_outreach_row

Action = Literal["send", "draft", "skip"]


@dataclass
class ActionOutcome:
    log_status: str
    message: str
    delivery_result: DeliveryResult | None = None


def apply_guardrails(contacts: list[Contact], config: AppConfig) -> list[Contact]:
    cap = config.max_outreach_per_run
    if cap <= 0:
        return []
    return contacts[:cap]


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def record_log(
    config: AppConfig,
    contact: Contact,
    draft: EmailDraft,
    status: str,
    error_message: str = "",
) -> None:
    append_log(
        LogEntry(
            timestamp=_utc_timestamp(),
            recipient_email=contact.recipient_email,
            company=contact.company,
            role=contact.role,
            subject=draft.subject,
            status=status,
            error_message=error_message,
            word_count=draft.word_count,
            job_url=contact.job_url,
        ),
        path=config.log_path,
    )


def _sync_tracking(contact: Contact, draft: EmailDraft, status: str, config: AppConfig) -> None:
    result = append_outreach_row(contact, draft, status, config)
    if result.get("enabled"):
        print(f"[tracking] {result['message']}")
    else:
        print(f"[tracking] {result['message']}")


def handle_contact_action(
    contact: Contact,
    draft: EmailDraft,
    config: AppConfig,
    action: Action,
) -> ActionOutcome:
    """
    Execute skip, send, or draft for one contact and write the audit log.

    Never calls deliver_email when action is skip.
    """
    if action == "skip":
        record_log(config, contact, draft, status="skipped")
        _sync_tracking(contact, draft, "skipped", config)
        return ActionOutcome(
            log_status="skipped",
            message="Skipped — no delivery attempted.",
        )

    result = deliver_email(draft, contact, config, mode=action)

    if result.status == "failed":
        record_log(
            config,
            contact,
            draft,
            status="failed",
            error_message=result.error or "Unknown delivery error",
        )
        _sync_tracking(contact, draft, "failed", config)
        return ActionOutcome(
            log_status="failed",
            message=result.error or "Delivery failed.",
            delivery_result=result,
        )

    if config.dry_run:
        record_log(config, contact, draft, status="dry_run")
        _sync_tracking(contact, draft, "dry_run", config)
        return ActionOutcome(
            log_status="dry_run",
            message=f"Dry-run complete (simulated {result.status}).",
            delivery_result=result,
        )

    record_log(config, contact, draft, status=result.status)
    _sync_tracking(contact, draft, result.status, config)
    return ActionOutcome(
        log_status=result.status,
        message=f"Delivery status: {result.status}.",
        delivery_result=result,
    )
