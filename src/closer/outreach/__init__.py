"""Shared outreach workflow for CLI and UI."""

from closer.outreach.workflow import (
    ActionOutcome,
    apply_guardrails,
    handle_contact_action,
    record_log,
)

__all__ = [
    "ActionOutcome",
    "apply_guardrails",
    "handle_contact_action",
    "record_log",
]
