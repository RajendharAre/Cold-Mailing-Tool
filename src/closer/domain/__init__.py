"""Phase 1 — Domain models and text helpers."""

from closer.domain.models import (
    Contact,
    DeliveryResult,
    DeliveryStatus,
    EmailDraft,
    LogEntry,
    LogStatus,
)
from closer.domain.text import count_words

__all__ = [
    "Contact",
    "DeliveryResult",
    "DeliveryStatus",
    "EmailDraft",
    "LogEntry",
    "LogStatus",
    "count_words",
]
