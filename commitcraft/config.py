"""Configuration management for CommitCraft."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .i18n import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES, normalize_language


CONFIG_DIR = Path.home() / ".commitcraft"
CONFIG_FILE = CONFIG_DIR / "config.json"
DEFAULT_API_URL = "https://api.gapgpt.app/v1/chat/completions"
DEFAULT_RETRY_WAIT_SECONDS = 5
DEFAULT_RETRY_ATTEMPTS = 10
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_CONVENTIONAL_COMMITS = True


@dataclass
class AppConfig:
    """Runtime settings persisted in a JSON file."""

    api_token: str
    api_url: str = DEFAULT_API_URL
    ui_language: str = DEFAULT_LANGUAGE
    model_output_language: str = DEFAULT_LANGUAGE
    retry_wait_seconds: int = DEFAULT_RETRY_WAIT_SECONDS
    retry_attempts: int = DEFAULT_RETRY_ATTEMPTS
    model: str = DEFAULT_MODEL
    conventional_commits: bool = DEFAULT_CONVENTIONAL_COMMITS

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppConfig":
        """Build config from JSON-safe data with defaults."""

        return cls(
            api_token=str(data.get("api_token", "")).strip(),
            api_url=str(data.get("api_url") or DEFAULT_API_URL).strip(),
            ui_language=normalize_language(str(data.get("ui_language", DEFAULT_LANGUAGE))),
            model_output_language=normalize_language(
                str(data.get("model_output_language", DEFAULT_LANGUAGE))
            ),
            retry_wait_seconds=_positive_int(
                data.get("retry_wait_seconds"),
                DEFAULT_RETRY_WAIT_SECONDS,
            ),
            retry_attempts=_positive_int(
                data.get("retry_attempts"),
                DEFAULT_RETRY_ATTEMPTS,
            ),
            model=str(data.get("model") or DEFAULT_MODEL).strip(),
            conventional_commits=_bool(
                data.get("conventional_commits"),
                DEFAULT_CONVENTIONAL_COMMITS,
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize config for disk storage."""

        return asdict(self)


class ConfigManager:
    """Read, write, and initialize application config."""

    def __init__(self, config_file: Path = CONFIG_FILE) -> None:
        self.config_file = config_file

    def exists(self) -> bool:
        """Return whether config file exists."""

        return self.config_file.exists()

    def load(self) -> AppConfig:
        """Load config from disk."""

        with self.config_file.open("r", encoding="utf-8") as file:
            data = json.load(file)
        return AppConfig.from_dict(data)

    def save(self, config: AppConfig) -> None:
        """Write config to disk."""

        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        with self.config_file.open("w", encoding="utf-8") as file:
            json.dump(config.to_dict(), file, ensure_ascii=False, indent=2)


def default_config() -> AppConfig:
    """Return a config object populated with safe application defaults."""

    return AppConfig(api_token="")


def mask_secret(value: str, visible_chars: int = 4) -> str:
    """Mask sensitive values so secrets are never printed in full."""

    if not value:
        return ""
    if len(value) <= visible_chars:
        return "•" * len(value)
    return f"{'•' * 8}{value[-visible_chars:]}"


def validate_api_token(value: str) -> str:
    """Validate and normalize an API token."""

    normalized = value.strip()
    if not normalized:
        raise ValueError("value_required")
    return normalized


def validate_api_url(value: str) -> str:
    """Validate and normalize an HTTP(S) API URL."""

    normalized = value.strip()
    parsed = urlparse(normalized)
    if (
        not normalized
        or any(character.isspace() for character in normalized)
        or parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.hostname is None
    ):
        raise ValueError("invalid_url")
    return normalized


def validate_language(value: str) -> str:
    """Validate a supported language code or name."""

    normalized = normalize_language(value, default="")
    if normalized not in SUPPORTED_LANGUAGES:
        raise ValueError("invalid_language")
    return normalized


def validate_positive_int(value: str) -> int:
    """Validate a positive integer setting."""

    try:
        integer = int(value.strip())
    except (AttributeError, ValueError) as exc:
        raise ValueError("invalid_positive_number") from exc
    if integer <= 0:
        raise ValueError("invalid_positive_number")
    return integer


def validate_model(value: str) -> str:
    """Validate and normalize a model name."""

    normalized = value.strip()
    if not normalized:
        raise ValueError("value_required")
    return normalized


def validate_bool(value: str) -> bool:
    """Validate a localized yes/no-like setting value and return a boolean."""

    normalized = value.strip().lower()
    if normalized in {"yes", "y", "true", "1", "on", "بله", "آری", "روشن"}:
        return True
    if normalized in {"no", "n", "false", "0", "off", "خیر", "نه", "خاموش"}:
        return False
    raise ValueError("invalid_bool")


def _positive_int(value: Any, default: int) -> int:
    """Convert a value to a positive integer or return default."""

    try:
        integer = int(value)
    except (TypeError, ValueError):
        return default
    return integer if integer > 0 else default


def _bool(value: Any, default: bool) -> bool:
    """Convert persisted JSON values to booleans while preserving defaults."""

    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        try:
            return validate_bool(value)
        except ValueError:
            return default
    return default
