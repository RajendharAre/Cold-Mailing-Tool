"""Google Sheets integration for outreach tracking."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from closer.config import AppConfig
from closer.domain import Contact, EmailDraft

_IST = ZoneInfo("Asia/Kolkata")


def _ist_timestamp() -> str:
    """Current time in Indian Standard Time as DD/MM/YYYY, HH:MM:SS (IST)."""
    return datetime.now(_IST).strftime("%d/%m/%Y, %H:%M:%S (IST)")


def append_outreach_row(
    contact: Contact,
    draft: EmailDraft,
    status: str,
    config: AppConfig,
) -> dict[str, Any]:
    """Append a row to Google Sheets when configured."""
    if not config.google_sheets_spreadsheet_id:
        return {"enabled": False, "message": "Google Sheets not configured."}

    payload = {
        "timestamp": _ist_timestamp(),
        "recipient_email": contact.recipient_email,
        "recipient_name": contact.recipient_name or "",
        "company": contact.company,
        "role": contact.role,
        "job_link": contact.job_url or "",
        "status": status,
        "subject": draft.subject,
        "word_count": draft.word_count,
    }

    return _append_with_gspread(payload, config)


def _gspread_client(config: AppConfig) -> "gspread.Client | None":
    """Build a gspread service-account client, or None when not possible."""
    credentials_json = config.google_sheets_credentials_json
    credentials_file = config.google_sheets_credentials_file

    if not credentials_json and not credentials_file:
        return None

    try:
        import gspread  # type: ignore

        if credentials_json:
            creds = json.loads(credentials_json)
            return gspread.service_account_from_dict(creds)
        return gspread.service_account(filename=credentials_file)
    except Exception as exc:  # pragma: no cover - defensive path
        print(f"[sheets] client creation failed: {exc}", file=sys.stderr)
        return None


def _append_with_gspread(payload: dict[str, Any], config: AppConfig) -> dict[str, Any]:
    """Best-effort append using gspread when available."""
    try:
        import gspread  # type: ignore
    except ImportError:
        return {
            "enabled": False,
            "message": "gspread is not installed; install requirements to enable Sheets sync.",
        }

    credentials_json = config.google_sheets_credentials_json
    credentials_file = config.google_sheets_credentials_file

    if not credentials_json and not credentials_file:
        return {"enabled": False, "message": "Google Sheets credentials not configured."}

    try:
        client = _gspread_client(config)
        if client is None:
            return {"enabled": False, "message": "Google Sheets credentials not configured."}

        sheet = client.open_by_key(config.google_sheets_spreadsheet_id)
        worksheet = sheet.worksheet(config.google_sheets_worksheet_name)
        _ensure_headers(worksheet)
        worksheet.append_row(
            [
                payload["timestamp"],
                payload["recipient_email"],
                payload["recipient_name"],
                payload["company"],
                payload["role"],
                payload["job_link"],
                payload["status"],
                payload["subject"],
                payload["word_count"],
            ]
        )
        return {"enabled": True, "status": "ok", "message": "Google Sheets updated."}
    except Exception as exc:  # pragma: no cover - defensive path
        return {"enabled": False, "message": f"Sheets sync failed: {exc}"}


# Column layout used by append_outreach_row (1-based):
# 1 timestamp | 2 recipient_email | 3 recipient_name | 4 company | 5 role
# 6 job_link | 7 status | 8 subject | 9 word_count
_STATUS_COLUMN = 7
_EMAIL_COLUMN = 2
_LINK_COLUMN = 6

_HEADERS = [
    "timestamp",
    "recipient_email",
    "recipient_name",
    "company",
    "role",
    "job_link",
    "status",
    "subject",
    "word_count",
]


def _ensure_headers(worksheet: Any) -> None:
    """Write the header row once when the worksheet is empty."""
    values = worksheet.get_all_values()
    if not values or (len(values) == 1 and not values[0]):
        worksheet.append_row(_HEADERS)


def update_outreach_status(
    recipient_email: str,
    status: str,
    config: AppConfig,
    job_link: str | None = None,
) -> dict[str, Any]:
    """Update the status column of matching row(s) in Google Sheets."""
    if not config.google_sheets_spreadsheet_id:
        return {"enabled": False, "message": "Google Sheets not configured."}

    try:
        import gspread  # type: ignore
    except ImportError:
        return {
            "enabled": False,
            "message": "gspread is not installed; install requirements to enable Sheets sync.",
        }

    try:
        client = _gspread_client(config)
        if client is None:
            return {"enabled": False, "message": "Google Sheets credentials not configured."}

        sheet = client.open_by_key(config.google_sheets_spreadsheet_id)
        worksheet = sheet.worksheet(config.google_sheets_worksheet_name)
        rows = worksheet.get_all_values()
    except Exception as exc:  # pragma: no cover - defensive path
        return {"enabled": False, "message": f"Sheets sync failed: {exc}"}

    target_email = recipient_email.strip().lower()
    target_link = (job_link or "").strip().lower()
    updated = 0
    for index, row in enumerate(rows, start=1):
        if index == 1:
            continue
        if not row or len(row) < _STATUS_COLUMN:
            continue
        row_email = row[_EMAIL_COLUMN - 1].strip().lower()
        if row_email != target_email:
            continue
        if target_link and row[_LINK_COLUMN - 1].strip().lower() != target_link:
            continue
        try:
            worksheet.update_cell(index, _STATUS_COLUMN, status)
            updated += 1
        except Exception:  # pragma: no cover - defensive path
            continue

    if updated:
        return {
            "enabled": True,
            "status": "ok",
            "message": f"Updated {updated} row(s) to status '{status}'.",
        }
    return {
        "enabled": True,
        "status": "no_match",
        "message": "No matching row found for that recipient email.",
    }
