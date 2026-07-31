"""Terminal preview and human confirmation before delivery."""

from __future__ import annotations

from typing import Literal

from closer.domain import Contact, EmailDraft

Action = Literal["send", "draft", "skip"]

_PROMPT = "Send this email? (send/draft/skip): "


def preview_email(draft: EmailDraft, contact: Contact) -> None:
    """Print a full draft preview for human review."""
    bar = "=" * 60
    recipient_label = contact.recipient_name or "there"
    print()
    print(bar)
    print(f"Company:   {contact.company}")
    print(f"Role:      {contact.role}")
    print(f"Recipient: {contact.recipient_email} ({recipient_label})")
    print(f"Subject:   {draft.subject}")
    print(f"Word count: {draft.word_count}")
    print(bar)
    print(draft.body)
    print(bar)
    print()


def prompt_action() -> Action:
    """
    Ask the operator to send, draft, or skip.

    Safety: never call deliver_email without passing through this function.

    Behavior:
    - Accepts exact keywords: send, draft, skip (case-insensitive).
    - Empty input defaults to skip.
    - Any other input re-prompts until a valid choice is entered.
    """
    while True:
        raw = input(_PROMPT).strip().lower()
        if raw in ("send", "draft", "skip"):
            return raw  # type: ignore[return-value]
        if raw == "":
            print("No input — skipping this email.")
            return "skip"
        print("Invalid choice. Please enter send, draft, or skip.")
