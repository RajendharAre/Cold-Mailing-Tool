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


def _repo_root() -> Path:
    return _REPO_ROOT


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in ("true", "1", "yes", "on")


def _parse_int(value: str | None, default: int) -> int:
    if value is None or value.strip() == "":
        return default
    try:
        return int(value.strip())
    except ValueError as exc:
        raise ConfigError(f"Invalid integer value: {value!r}") from exc


def _parse_path(value: str | None, default: Path) -> Path:
    if value is None or value.strip() == "":
        return default
    path = Path(value.strip())
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

    dry_run = _parse_bool(os.getenv("DRY_RUN"), default=True)
    send_mode = (os.getenv("SEND_MODE") or "draft").strip().lower()
    if send_mode not in ("draft", "send"):
        raise ConfigError(
            f"SEND_MODE must be 'draft' or 'send', got {send_mode!r}"
        )

    config = AppConfig(
        smtp_host=(os.getenv("SMTP_HOST") or "smtp.gmail.com").strip(),
        smtp_port=_parse_int(os.getenv("SMTP_PORT"), 587),
        smtp_user=_optional_str(os.getenv("SMTP_USER")),
        smtp_password=_optional_str(os.getenv("SMTP_PASSWORD")),
        sender_name=_optional_str(os.getenv("SENDER_NAME")),
        dry_run=dry_run,
        send_mode=send_mode,
        max_outreach_per_run=_parse_int(os.getenv("MAX_OUTREACH_PER_RUN"), 5),
        input_path=_parse_path(
            os.getenv("INPUT_PATH"), _repo_root() / "data" / "contacts.json"
        ),
        log_path=_parse_path(
            os.getenv("LOG_PATH"), _repo_root() / "logs" / "outreach_log.csv"
        ),
        groq_api_key=_optional_str(os.getenv("GROQ_API_KEY")),
        llm_provider=(os.getenv("LLM_PROVIDER") or "groq").strip().lower(),
        llm_model=_optional_str(os.getenv("LLM_MODEL")),
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


def _optional_str(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped if stripped else None
