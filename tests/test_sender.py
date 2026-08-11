from __future__ import annotations

from email.mime.multipart import MIMEMultipart
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from closer.config import AppConfig  # noqa: E402
from closer.domain import Contact  # noqa: E402
from closer.delivery.sender import _attach_resume, _build_message  # noqa: E402


@pytest.fixture
def config() -> AppConfig:
    return AppConfig(
        smtp_host="smtp.gmail.com",
        smtp_port=587,
        smtp_user=None,
        smtp_password=None,
        sender_name="Rajendhar Are",
        dry_run=True,
        send_mode="draft",
        max_outreach_per_run=5,
        input_path=ROOT / "data" / "contacts.json",
        log_path=ROOT / "logs" / "outreach_log.csv",
        groq_api_key=None,
        llm_provider="groq",
        llm_model=None,
    )


def test_build_message_includes_uploaded_resume_attachment() -> None:
    contact = Contact(
        recipient_email="hr@example.com",
        company="Acme",
        role="Engineer",
        candidate_name="Rajendhar Are",
        candidate_background="Python developer",
        resume_filename="Rajendhar_Resume.pdf",
        resume_file_bytes=b"%PDF-1.4 fake pdf bytes",
    )

    message = _build_message(
        subject="Job application",
        body="Hello",
        to_email=contact.recipient_email,
        from_email="sender@gmail.com",
        sender_name="Rajendhar Are",
        contact=contact,
    )

    assert isinstance(message, MIMEMultipart)
    parts = [part for part in message.walk() if part.is_multipart() is False]
    filenames = [part.get_filename() for part in parts]
    assert "Rajendhar_Resume.pdf" in filenames


def test_build_message_attaches_default_resume_when_none_uploaded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    contact = Contact(
        recipient_email="hr@example.com",
        company="Acme",
        role="Engineer",
        candidate_name="Rajendhar Are",
        candidate_background="Python developer",
    )

    monkeypatch.setattr(
        "closer.delivery.sender._default_resume_path",
        lambda: ROOT / "resume_background.md",
    )

    message = _build_message(
        subject="Job application",
        body="Hello",
        to_email=contact.recipient_email,
        from_email="sender@gmail.com",
        sender_name="Rajendhar Are",
        contact=contact,
    )

    parts = [part for part in message.walk() if part.is_multipart() is False]
    filenames = [part.get_filename() for part in parts]
    assert "resume_background.md" in filenames


def test_attach_resume_skips_when_no_resume_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    contact = Contact(
        recipient_email="hr@example.com",
        company="Acme",
        role="Engineer",
        candidate_name="Rajendhar Are",
        candidate_background="Python developer",
    )

    monkeypatch.setattr(
        "closer.delivery.sender._default_resume_path",
        lambda: None,
    )

    message = MIMEMultipart()
    _attach_resume(message, contact)

    parts = [part for part in message.walk() if part.is_multipart() is False]
    assert all(part.get_filename() is None for part in parts)
