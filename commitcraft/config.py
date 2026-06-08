"""Configuration management for CommitCraft."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .i18n import DEFAULT_LANGUAGE, normalize_language


CONFIG_DIR = Path.home() / ".commitcraft"
CONFIG_FILE = CONFIG_DIR / "config.json"
DEFAULT_API_URL = "https://api.gapgpt.app/v1/chat/completions"
DEFAULT_RETRY_WAIT_SECONDS = 5
DEFAULT_RETRY_ATTEMPTS = 10


@dataclass
class AppConfig:
    """Runtime settings persisted in a JSON file."""

    api_token: str
    api_url: str = DEFAULT_API_URL
    ui_language: str = DEFAULT_LANGUAGE
    model_output_language: str = DEFAULT_LANGUAGE
    retry_wait_seconds: int = DEFAULT_RETRY_WAIT_SECONDS
    retry_attempts: int = DEFAULT_RETRY_ATTEMPTS
    model: str = "gpt-4o-mini"

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
            model=str(data.get("model") or "gpt-4o-mini").strip(),
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


def _positive_int(value: Any, default: int) -> int:
    """Convert a value to a positive integer or return default."""

    try:
        integer = int(value)
    except (TypeError, ValueError):
        return default
    return integer if integer > 0 else default
