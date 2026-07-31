"""Tests for cold email generation (Phase 8)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from closer.config import AppConfig  # noqa: E402
from closer.domain import Contact  # noqa: E402
from closer.generation import generate_email  # noqa: E402


@pytest.fixture
def config() -> AppConfig:
    return AppConfig(
        smtp_host="smtp.gmail.com",
        smtp_port=587,
        smtp_user=None,
        smtp_password=None,
        sender_name="Alex Kim",
        dry_run=True,
        send_mode="draft",
        max_outreach_per_run=5,
        input_path=ROOT / "data" / "contacts.json",
        log_path=ROOT / "logs" / "outreach_log.csv",
        groq_api_key=None,
        llm_provider="groq",
        llm_model=None,
    )


@pytest.fixture
def contact() -> Contact:
    return Contact(
        recipient_email="test@example.com",
        company="Acme AI",
        role="Backend Intern",
        candidate_name="Alex Kim",
        candidate_background="Python and automation",
        personalization_note="Recently launched a new API platform.",
        recipient_name="Jamie",
    )


def test_generate_email_has_subject_and_body(config: AppConfig, contact: Contact) -> None:
    draft = generate_email(contact, config)
    assert draft.subject.strip()
    assert draft.body.strip()
    assert "Acme AI" in draft.body
    assert "Backend Intern" in draft.body


def test_generate_email_word_count_within_limit(
    config: AppConfig, contact: Contact
) -> None:
    draft = generate_email(contact, config)
    assert draft.word_count <= 150
    assert draft.word_count > 0


def test_fallback_hook_without_personalization_note(config: AppConfig) -> None:
    contact = Contact(
        recipient_email="test@example.com",
        company="Nimbus Health",
        role="SWE Intern",
        candidate_name="Alex Kim",
        candidate_background="data workflows",
    )
    draft = generate_email(contact, config)
    assert "Nimbus Health" in draft.body
    assert "SWE Intern" in draft.body
