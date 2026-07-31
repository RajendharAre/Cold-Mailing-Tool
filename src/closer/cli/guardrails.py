"""Ethics and quality guardrails for outreach runs."""

from __future__ import annotations

import sys

from closer.config import AppConfig
from closer.domain import Contact


def run_preflight_checks(contacts: list[Contact], config: AppConfig) -> None:
    """Print warnings for low personalization or sender identity mismatch."""
    if config.max_outreach_per_run > 5:
        print(
            f"[guardrail] warning: MAX_OUTREACH_PER_RUN={config.max_outreach_per_run} "
            "exceeds recommended demo cap of 5.",
            file=sys.stderr,
        )

    for contact in contacts:
        warn_weak_personalization(contact)
        warn_sender_identity(contact, config)


def warn_weak_personalization(contact: Contact) -> None:
    if not contact.personalization_note:
        print(
            f"[guardrail] {contact.company}: no personalization_note — "
            "using company/role fallback hook.",
            file=sys.stderr,
        )


def warn_sender_identity(contact: Contact, config: AppConfig) -> None:
    if not config.smtp_user:
        return

    smtp_local = config.smtp_user.split("@")[0].lower().replace(".", "")
    candidate_parts = contact.candidate_name.lower().split()
    first = candidate_parts[0] if candidate_parts else ""
    last = candidate_parts[-1] if len(candidate_parts) > 1 else ""

    matches = (
        first in smtp_local
        or last in smtp_local
        or smtp_local in contact.candidate_name.lower().replace(" ", "")
    )
    if not matches and not config.dry_run:
        print(
            f"[guardrail] SMTP_USER ({config.smtp_user}) may not match "
            f"candidate_name ({contact.candidate_name}). Use your own identity.",
            file=sys.stderr,
        )
