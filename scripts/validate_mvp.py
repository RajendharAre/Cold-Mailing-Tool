#!/usr/bin/env python3
"""Non-interactive MVP validation for Phase 8 acceptance criteria."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from closer.config import load_config  # noqa: E402
from closer.generation import generate_email  # noqa: E402
from closer.input import load_targets  # noqa: E402

_WORD_LIMIT = 150
_MIN_CONTACTS = 5


def main() -> int:
    config = load_config()
    contacts = load_targets(config.input_path)

    print("The Closer — MVP validation")
    print(f"  contacts loaded: {len(contacts)}")
    print(f"  input_path: {config.input_path}")
    print()

    if len(contacts) < _MIN_CONTACTS:
        print(f"FAIL: need at least {_MIN_CONTACTS} valid contacts, got {len(contacts)}")
        return 1

    subjects: set[str] = set()
    over_limit = 0

    for index, contact in enumerate(contacts, start=1):
        draft = generate_email(contact, config)
        subjects.add(draft.subject)

        company_ok = contact.company in draft.body
        role_ok = contact.role in draft.body
        within_limit = draft.word_count <= _WORD_LIMIT

        if not within_limit:
            over_limit += 1

        status = "OK" if company_ok and role_ok and within_limit else "CHECK"
        print(
            f"  [{status}] {index}. {contact.company} — {contact.role} "
            f"| words={draft.word_count} | subject={draft.subject!r}"
        )

        if not company_ok or not role_ok:
            print("         missing company/role personalization in body")
        if not within_limit:
            print(f"         exceeds {_WORD_LIMIT} words")

    print()
    print(f"  distinct subjects: {len(subjects)}")
    print(f"  over word limit:   {over_limit}")

    if over_limit > 0:
        print("\nFAIL: one or more emails exceed the word limit.")
        return 1

    if len(subjects) < min(3, len(contacts)):
        print("\nFAIL: subjects are not sufficiently distinct.")
        return 1

    print("\nPASS: MVP generation checks succeeded.")
    print("Next: run `python main.py` interactively and capture submission screenshots.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
