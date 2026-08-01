"""Domain models for contacts, drafts, delivery, and audit logs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

DeliveryStatus = Literal["drafted", "sent", "failed"]
LogStatus = Literal[
    "generated",
    "drafted",
    "sent",
    "skipped",
    "failed",
    "dry_run",
]


@dataclass
class Contact:
    """Outreach target loaded from JSON, CSV, or hardcoded data."""

    recipient_email: str
    company: str
    role: str
    candidate_name: str
    candidate_background: str
    recipient_name: str | None = None
    job_url: str | None = None
    portfolio_url: str | None = None
    personalization_note: str | None = None
    linkedin_url: str | None = None
    resume_link: str | None = None
    job_description: str | None = None
    resume_context: str | None = None


@dataclass
class EmailDraft:
    """Generated cold email before human review and delivery."""

    subject: str
    body: str
    word_count: int


@dataclass
class LogEntry:
    """One row in outreach_log.csv."""

    timestamp: str
    recipient_email: str
    company: str
    role: str
    subject: str
    status: str
    error_message: str = ""
    word_count: int | None = None
    job_url: str | None = None


@dataclass
class DeliveryResult:
    """Result of a send or draft attempt."""

    status: DeliveryStatus
    provider_message_id: str | None = None
    error: str | None = None
