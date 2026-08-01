"""Tests for outreach target loading and validation."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from closer.input import extract_resume_text, load_targets  # noqa: E402


def _write_contacts(tmp_path: Path, records: list[dict]) -> Path:
    path = tmp_path / "contacts.json"
    path.write_text(json.dumps(records), encoding="utf-8")
    return path


def test_load_targets_normalizes_display_name_email(tmp_path: Path) -> None:
    path = _write_contacts(
        tmp_path,
        [
            {
                "recipient_name": "Priya Sharma",
                "recipient_email": "Priya Sharma <priya@example.com>",
                "company": "Acme AI",
                "role": "Backend Intern",
                "candidate_name": "Alex Kim",
                "candidate_background": "Python",
            }
        ],
    )

    contacts = load_targets(path)

    assert len(contacts) == 1
    assert contacts[0].recipient_email == "priya@example.com"


def test_load_targets_rejects_invalid_email(tmp_path: Path) -> None:
    path = _write_contacts(
        tmp_path,
        [
            {
                "recipient_email": "not-an-email",
                "company": "Acme AI",
                "role": "Backend Intern",
                "candidate_name": "Alex Kim",
                "candidate_background": "Python",
            }
        ],
    )

    contacts = load_targets(path)

    assert contacts == []


def test_extract_resume_text_from_plain_text() -> None:
    text = extract_resume_text("resume.txt", b"# Rajendhar Are\nPython developer")

    assert text == "# Rajendhar Are\nPython developer"


def test_extract_resume_text_from_markdown() -> None:
    text = extract_resume_text("resume.md", "## Summary\nStrong Python developer.")

    assert text == "## Summary\nStrong Python developer."


def test_extract_resume_text_from_pdf_uses_pypdf(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakePage:
        def extract_text(self) -> str:
            return "Fake PDF resume text"

    class FakeReader:
        def __init__(self, stream) -> None:
            assert stream is not None

        @property
        def pages(self):
            return [FakePage(), FakePage()]

    class FakePypdf:
        PdfReader = FakeReader

    import closer.input.resume as resume_module

    monkeypatch.setattr(resume_module, "_load_pypdf", lambda: FakePypdf())

    text = extract_resume_text("resume.pdf", b"%PDF-fake")

    assert text == "Fake PDF resume text\nFake PDF resume text"


def test_extract_resume_text_pdf_raises_without_pypdf(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import closer.input.resume as resume_module

    def missing(*args, **kwargs):
        raise RuntimeError(
            "pypdf is required to read PDF resumes. Install it with: pip install pypdf"
        )

    monkeypatch.setattr(resume_module, "_load_pypdf", missing)

    with pytest.raises(RuntimeError, match="pypdf is required"):
        extract_resume_text("resume.pdf", b"%PDF")
