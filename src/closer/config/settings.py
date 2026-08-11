"""Application configuration loaded from environment variables."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv

_REPO_ROOT = Path(__file__).resolve().parents[3]


class ConfigError(Exception):
    """Raised when required configuration is missing or invalid."""


@dataclass
class AppConfig:
    smtp_host: str
    smtp_port: int
    smtp_user: str | None
    smtp_password: str | None
    sender_name: str | None
    dry_run: bool
    send_mode: str
    max_outreach_per_run: int
    input_path: Path
    log_path: Path
    groq_api_key: str | None
    llm_provider: str
    llm_model: str | None
    google_sheets_credentials_json: str | None = None
    google_sheets_credentials_file: str | None = None
    google_sheets_spreadsheet_id: str | None = None
    google_sheets_worksheet_name: str = "Outreach"


def _repo_root() -> Path:
    return _REPO_ROOT


def _parse_bool(value: object, default: bool) -> bool:
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("true", "1", "yes", "on")


def _parse_int(value: object, default: int) -> int:
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return default
    try:
        return int(value)
    except (ValueError, TypeError) as exc:
        raise ConfigError(f"Invalid integer value: {value!r}") from exc


def _get_secret(name: str) -> object | None:
    """Read a setting from the environment, falling back to Streamlit secrets."""
    value = os.getenv(name)
    if value is not None:
        return value
    try:
        import streamlit as st  # type: ignore

        return st.secrets.get(name)
    except Exception:  # pragma: no cover - depends on Streamlit runtime
        return None


def _parse_path(value: object, default: Path) -> Path:
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return default
    text = str(value).strip()
    if not text:
        return default
    path = Path(text)
    if not path.is_absolute():
        path = _repo_root() / path
    return path


def load_config(env_file: str | Path | None = None) -> AppConfig:
    """Load settings from .env and environment. Defaults to DRY_RUN=true."""
    path = Path(env_file) if env_file else _repo_root() / ".env"
    if path.is_file():
        load_dotenv(path)
    else:
        load_dotenv()

    dry_run = _parse_bool(_get_secret("DRY_RUN"), default=True)
    send_mode = (str(_get_secret("SEND_MODE") or "") or "draft").strip().lower()
    llm_provider = (
        str(_get_secret("LLM_PROVIDER") or "") or _infer_llm_provider()
    ).strip().lower()
    if send_mode not in ("draft", "send"):
        raise ConfigError(
            f"SEND_MODE must be 'draft' or 'send', got {send_mode!r}"
        )

    config = AppConfig(
        smtp_host=(str(_get_secret("SMTP_HOST") or "") or "smtp.gmail.com").strip(),
        smtp_port=_parse_int(_get_secret("SMTP_PORT"), 587),
        smtp_user=_optional_str(_get_secret("SMTP_USER")),
        smtp_password=_optional_str(_get_secret("SMTP_PASSWORD")),
        sender_name=_optional_str(_get_secret("SENDER_NAME")),
        dry_run=dry_run,
        send_mode=send_mode,
        max_outreach_per_run=_parse_int(_get_secret("MAX_OUTREACH_PER_RUN"), 5),
        input_path=_parse_path(
            _get_secret("INPUT_PATH"), _repo_root() / "data" / "contacts.json"
        ),
        log_path=_parse_path(
            _get_secret("LOG_PATH"), _repo_root() / "logs" / "outreach_log.csv"
        ),
        groq_api_key=_optional_str(_get_secret("GROQ_API_KEY")),
        llm_provider=llm_provider,
        llm_model=_optional_str(_get_secret("LLM_MODEL")),
        google_sheets_credentials_json=_optional_str(
            _get_secret("GOOGLE_SHEETS_CREDENTIALS_JSON")
        ),
        google_sheets_credentials_file=_optional_str(
            _get_secret("GOOGLE_SHEETS_CREDENTIALS_FILE")
        ),
        google_sheets_spreadsheet_id=_optional_str(
            _get_secret("GOOGLE_SHEETS_SPREADSHEET_ID")
        ),
        google_sheets_worksheet_name=(
            str(_get_secret("GOOGLE_SHEETS_WORKSHEET_NAME") or "") or "Outreach"
        ).strip(),
    )

    if config.max_outreach_per_run < 0:
        raise ConfigError("MAX_OUTREACH_PER_RUN must be >= 0")

    if not config.dry_run:
        missing = []
        if not config.smtp_user:
            missing.append("SMTP_USER")
        if not config.smtp_password:
            missing.append("SMTP_PASSWORD")
        if missing:
            raise ConfigError(
                "When DRY_RUN=false, required variables are missing: "
                + ", ".join(missing)
                + ". Use a Gmail App Password or set DRY_RUN=true."
            )

    return config


def _infer_llm_provider() -> str:
    if _get_secret("GEMINI_API_KEY") or _get_secret("GOOGLE_API_KEY"):
        return "gemini"
    if _get_secret("GROQ_API_KEY"):
        return "groq"
    return "groq"


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    stripped = str(value).strip()
    return stripped if stripped else None
