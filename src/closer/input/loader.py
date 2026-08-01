"""Load outreach targets from JSON and validate required fields."""

from __future__ import annotations

import json
from email.utils import parseaddr
from pathlib import Path
import re
import sys
from typing import Any

from closer.domain import Contact

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_INPUT_PATH = _REPO_ROOT / "data" / "contacts.json"
_REQUIRED_FIELDS = (
    "recipient_email",
    "company",
    "role",
    "candidate_name",
    "candidate_background",
)
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def load_targets(path: str | Path | None = None) -> list[Contact]:
    """Load and validate outreach targets from a JSON file."""
    input_path = _resolve_input_path(path)
    records = _load_json_array(input_path)

    contacts: list[Contact] = []
    for index, raw_record in enumerate(records, start=1):
        contact = _to_contact(raw_record, index=index)
        if contact is not None:
            contacts.append(contact)

    return contacts


def _resolve_input_path(path: str | Path | None) -> Path:
    if path is None:
        return _DEFAULT_INPUT_PATH

    resolved = Path(path)
    if not resolved.is_absolute():
        resolved = _REPO_ROOT / resolved
    return resolved


def _load_json_array(path: Path) -> list[Any]:
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")
    if not path.is_file():
        raise ValueError(f"Input path is not a file: {path}")

    try:
        raw_text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"Input file must be UTF-8 encoded: {path}") from exc

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc

    if not isinstance(parsed, list):
        raise ValueError(f"Expected a JSON array in {path}")

    return parsed


def _to_contact(record: Any, index: int) -> Contact | None:
    if not isinstance(record, dict):
        _warn(index, "record is not an object; skipping")
        return None

    missing = [
        field
        for field in _REQUIRED_FIELDS
        if _optional_str(record.get(field)) is None
    ]
    if missing:
        _warn(index, f"missing required fields: {', '.join(missing)}; skipping")
        return None

    recipient_email = _optional_str(record.get("recipient_email"))
    assert recipient_email is not None
    recipient_email = _normalize_email(recipient_email)
    if recipient_email is None:
        _warn(
            index,
            f"invalid recipient_email {record.get('recipient_email')!r}; skipping",
        )
        return None

    return Contact(
        recipient_email=recipient_email,
        company=_required_str(record, "company"),
        role=_required_str(record, "role"),
        candidate_name=_required_str(record, "candidate_name"),
        candidate_background=_required_str(record, "candidate_background"),
        recipient_name=_optional_str(record.get("recipient_name")) or "there",
        job_url=_optional_str(record.get("job_url")),
        portfolio_url=_optional_str(record.get("portfolio_url")),
        personalization_note=_optional_str(record.get("personalization_note")),
        linkedin_url=_optional_str(record.get("linkedin_url")),
        resume_link=_optional_str(record.get("resume_link")),
    )


def _required_str(record: dict[str, Any], field: str) -> str:
    value = _optional_str(record.get(field))
    if value is None:
        raise ValueError(f"Missing required field {field!r}")
    return value


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def _normalize_email(email: str) -> str | None:
    """Return the bare address from an email or display-name form, or None if invalid."""
    _name, parsed_email = parseaddr(email)
    parsed_email = parsed_email.strip()
    if not parsed_email or not _EMAIL_RE.match(parsed_email):
        return None
    return parsed_email


def _warn(index: int, message: str) -> None:
    print(f"[input_loader] row {index}: {message}", file=sys.stderr)
