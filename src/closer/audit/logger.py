"""Append-only outreach audit log (CSV)."""

from __future__ import annotations

import csv
from pathlib import Path

from closer.domain import LogEntry

CSV_COLUMNS = [
    "timestamp",
    "recipient_email",
    "company",
    "role",
    "subject",
    "status",
    "error_message",
    "word_count",
    "job_url",
]


def append_log(entry: LogEntry, path: str | Path | None = None) -> None:
    """Append one log row, creating the file and header when missing."""
    log_path = Path(path) if path else Path("logs/outreach_log.csv")
    log_path.parent.mkdir(parents=True, exist_ok=True)

    write_header = not log_path.exists() or log_path.stat().st_size == 0
    with log_path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        if write_header:
            writer.writeheader()
        writer.writerow(_entry_to_row(entry))


def _entry_to_row(entry: LogEntry) -> dict[str, str]:
    return {
        "timestamp": entry.timestamp,
        "recipient_email": entry.recipient_email,
        "company": entry.company,
        "role": entry.role,
        "subject": entry.subject,
        "status": entry.status,
        "error_message": entry.error_message,
        "word_count": "" if entry.word_count is None else str(entry.word_count),
        "job_url": entry.job_url or "",
    }
