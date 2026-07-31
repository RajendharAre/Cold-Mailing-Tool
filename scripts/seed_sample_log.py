#!/usr/bin/env python3
"""Create a redacted sample outreach log for submission (no SMTP required)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from closer.audit.logger import append_log  # noqa: E402
from closer.config import load_config  # noqa: E402
from closer.domain import LogEntry  # noqa: E402
from closer.generation import generate_email  # noqa: E402
from closer.input import load_targets  # noqa: E402
from datetime import datetime, timezone  # noqa: E402


def main() -> None:
    config = load_config()
    contacts = load_targets(config.input_path)[:5]
    sample_path = ROOT / "logs" / "outreach_log.sample.csv"

    if sample_path.exists():
        sample_path.unlink()

    for contact in contacts:
        draft = generate_email(contact, config)
        append_log(
            LogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                recipient_email=contact.recipient_email,
                company=contact.company,
                role=contact.role,
                subject=draft.subject,
                status="dry_run",
                error_message="",
                word_count=draft.word_count,
                job_url=contact.job_url,
            ),
            path=sample_path,
        )

    print(f"Wrote {len(contacts)} sample rows to {sample_path}")


if __name__ == "__main__":
    main()
