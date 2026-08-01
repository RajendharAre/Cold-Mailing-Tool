from __future__ import annotations

from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from closer.config import AppConfig  # noqa: E402
from closer.domain import Contact, EmailDraft  # noqa: E402
from closer.tracking.sheets import append_outreach_row, update_outreach_status  # noqa: E402


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
        google_sheets_credentials_json=None,
        google_sheets_credentials_file=None,
        google_sheets_spreadsheet_id=None,
        google_sheets_worksheet_name="Outreach",
    )


def test_append_outreach_row_is_disabled_without_sheet_config(config: AppConfig) -> None:
    contact = Contact(
        recipient_email="test@example.com",
        company="Acme Labs",
        role="Backend Intern",
        candidate_name="Alex Kim",
        candidate_background="Python automation",
        recipient_name="Jamie",
        job_url="https://jobs.example/acme",
        job_description="Backend Intern at Acme Labs",
    )
    draft = EmailDraft(subject="Test subject", body="Test body", word_count=5)

    result = append_outreach_row(contact, draft, "sent", config)

    assert result["enabled"] is False
    assert "not configured" in result["message"].lower()


def test_append_outreach_row_uses_configured_sheet_settings(
    config: AppConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    config.google_sheets_spreadsheet_id = "spreadsheet-id"
    config.google_sheets_credentials_json = '{"type": "service_account"}'

    captured: dict[str, object] = {}

    def fake_append(payload: dict[str, object]) -> dict[str, object]:
        captured["payload"] = payload
        return {"enabled": True, "status": "ok", "message": "ok"}

    monkeypatch.setattr(
        "closer.tracking.sheets._append_with_gspread",
        lambda payload, config: fake_append(payload),
    )

    contact = Contact(
        recipient_email="test@example.com",
        company="Acme Labs",
        role="Backend Intern",
        candidate_name="Alex Kim",
        candidate_background="Python automation",
        recipient_name="Jamie",
        job_url="https://jobs.example/acme",
        job_description="Backend Intern at Acme Labs",
    )
    draft = EmailDraft(subject="Test subject", body="Test body", word_count=5)

    result = append_outreach_row(contact, draft, "sent", config)

    assert result["enabled"] is True
    assert captured["payload"]["company"] == "Acme Labs"
    assert captured["payload"]["role"] == "Backend Intern"
    assert captured["payload"]["status"] == "sent"


def test_update_outreach_status_is_disabled_without_sheet_config(config: AppConfig) -> None:
    result = update_outreach_status("test@example.com", "replied", config)

    assert result["enabled"] is False
    assert "not configured" in result["message"].lower()


def test_update_outreach_status_updates_matching_rows(
    config: AppConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    config.google_sheets_spreadsheet_id = "spreadsheet-id"
    config.google_sheets_credentials_json = '{"type": "service_account"}'

    updated_cells: list[tuple[int, int, str]] = []

    class FakeWorksheet:
        def get_all_values(self):
            return [
                ["timestamp", "recipient_email", "name", "company", "role", "job_link", "status", "subject", "words"],
                ["t1", "alice@example.com", "Alice", "Acme", "Intern", "https://jobs.acme/1", "sent", "subj", "80"],
                ["t2", "bob@example.com", "Bob", "Nimbus", "Intern", "https://jobs.nimbus/2", "sent", "subj", "90"],
                ["t3", "alice@example.com", "Alice", "Acme", "Intern", "https://jobs.acme/3", "sent", "subj", "81"],
            ]

        def update_cell(self, row, col, value):
            updated_cells.append((row, col, value))

    class FakeSheet:
        def worksheet(self, name):
            return FakeWorksheet()

    class FakeClient:
        def open_by_key(self, key):
            return FakeSheet()

    monkeypatch.setattr(
        "closer.tracking.sheets._gspread_client",
        lambda config: FakeClient(),
    )

    result = update_outreach_status("alice@example.com", "awaiting reply", config)

    assert result["enabled"] is True
    assert result["status"] == "ok"
    assert result["message"] == "Updated 2 row(s) to status 'awaiting reply'."
    assert updated_cells == [
        (2, 7, "awaiting reply"),
        (4, 7, "awaiting reply"),
    ]


def test_update_outreach_status_filters_by_job_link(
    config: AppConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    config.google_sheets_spreadsheet_id = "spreadsheet-id"
    config.google_sheets_credentials_json = '{"type": "service_account"}'

    updated_cells: list[tuple[int, int, str]] = []

    class FakeWorksheet:
        def get_all_values(self):
            return [
                ["timestamp", "recipient_email", "name", "company", "role", "job_link", "status", "subject", "words"],
                ["t1", "alice@example.com", "Alice", "Acme", "Intern", "https://jobs.acme/1", "sent", "subj", "80"],
                ["t3", "alice@example.com", "Alice", "Acme", "Intern", "https://jobs.acme/3", "sent", "subj", "81"],
            ]

        def update_cell(self, row, col, value):
            updated_cells.append((row, col, value))

    class FakeSheet:
        def worksheet(self, name):
            return FakeWorksheet()

    class FakeClient:
        def open_by_key(self, key):
            return FakeSheet()

    monkeypatch.setattr(
        "closer.tracking.sheets._gspread_client",
        lambda config: FakeClient(),
    )

    result = update_outreach_status(
        "alice@example.com", "replied", config, job_link="https://jobs.acme/1"
    )

    assert result["status"] == "ok"
    assert updated_cells == [(2, 7, "replied")]


def test_update_outreach_status_reports_no_match(
    config: AppConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    config.google_sheets_spreadsheet_id = "spreadsheet-id"
    config.google_sheets_credentials_json = '{"type": "service_account"}'

    class FakeWorksheet:
        def get_all_values(self):
            return [
                ["timestamp", "recipient_email", "name", "company", "role", "job_link", "status", "subject", "words"],
                ["t1", "alice@example.com", "Alice", "Acme", "Intern", "https://jobs.acme/1", "sent", "subj", "80"],
            ]

        def update_cell(self, row, col, value):
            raise AssertionError("should not update")

    class FakeSheet:
        def worksheet(self, name):
            return FakeWorksheet()

    class FakeClient:
        def open_by_key(self, key):
            return FakeSheet()

    monkeypatch.setattr(
        "closer.tracking.sheets._gspread_client",
        lambda config: FakeClient(),
    )

    result = update_outreach_status("nobody@example.com", "replied", config)

    assert result["status"] == "no_match"
    assert "No matching row" in result["message"]
