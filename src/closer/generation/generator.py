"""Deterministic cold-email generator for Phase 3."""

from __future__ import annotations

import sys

from closer.config import AppConfig, load_config
from closer.domain import Contact, EmailDraft, count_words
from closer.input import load_targets

_WORD_LIMIT = 150


def generate_email(contact: Contact, config: AppConfig) -> EmailDraft:
    """Generate subject and body using only provided contact fields."""
    subject = _build_subject(contact)
    body = _build_body(contact)
    word_count = count_words(body)

    if word_count > _WORD_LIMIT:
        print(
            f"[email_generator] warning: generated {word_count} words "
            f"(limit {_WORD_LIMIT}) for {contact.recipient_email}",
            file=sys.stderr,
        )

    return EmailDraft(subject=subject, body=body, word_count=word_count)


def _build_subject(contact: Contact) -> str:
    # Optional variant: mention company when no explicit personalization note exists.
    if contact.personalization_note:
        return f"Quick note on the {contact.role} role"
    return f"Interest in {contact.role} at {contact.company}"


def _build_body(contact: Contact) -> str:
    recipient_name = contact.recipient_name or "there"
    hook = _build_personalization_hook(contact)
    sign_off_lines = [contact.candidate_name]
    if contact.portfolio_url:
        sign_off_lines.append(contact.portfolio_url)

    lines = [
        f"Hi {recipient_name},",
        "",
        hook,
        "",
        (
            f"I'm {contact.candidate_name}, and I've been building projects around "
            f"{contact.candidate_background}."
        ),
        (
            f"The {contact.role} role stood out because it aligns with how I like "
            "to build practical, product-focused solutions."
        ),
        "",
        (
            "Would you be open to a quick look at my profile or pointing me to "
            "the right person to connect with?"
        ),
        "",
        "Best,",
        *sign_off_lines,
    ]
    return "\n".join(lines)


def _build_personalization_hook(contact: Contact) -> str:
    if contact.personalization_note:
        return (
            f"I noticed {contact.company} is hiring for {contact.role}. "
            f"{contact.personalization_note}"
        )
    return (
        f"I noticed {contact.company} is hiring for {contact.role}, and that "
        "combination of domain and role is exactly what I have been preparing for."
    )


if __name__ == "__main__":
    cfg = load_config()
    contacts = load_targets(cfg.input_path)
    if not contacts:
        print("No contacts available to generate email.")
        raise SystemExit(0)

    draft = generate_email(contacts[0], cfg)
    print(f"Recipient: {contacts[0].recipient_email}")
    print(f"Subject: {draft.subject}")
    print(f"Word count: {draft.word_count}")
    print()
    print(draft.body)
