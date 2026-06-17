"""Configuration management for CommitCraft."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .i18n import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES, normalize_language


CONFIG_DIR = Path.home() / ".commitcraft"
CONFIG_FILE = CONFIG_DIR / "config.json"
DEFAULT_API_URL = "https://api.gapgpt.app/v1/chat/completions"
DEFAULT_PROVIDER_NAME = "GapGPT"
DEFAULT_PROVIDER_TYPE = "openai"
DEFAULT_RETRY_WAIT_SECONDS = 5
DEFAULT_RETRY_ATTEMPTS = 10
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_ANTHROPIC_MODEL = "claude-3-5-sonnet-latest"
DEFAULT_CONVENTIONAL_COMMITS = True
DEFAULT_PULL_STRATEGY = "merge"
DEFAULT_AUTO_STASH = True
DEFAULT_AUTO_SPLIT_COMMITS = False
PULL_STRATEGIES = {"merge", "rebase"}
AI_PROVIDER_TYPES = {"openai", "anthropic"}
PROVIDER_DEFAULTS = {
    "gapgpt": {
        "name": "GapGPT",
        "provider_type": "openai",
        "api_url": DEFAULT_API_URL,
        "model": DEFAULT_MODEL,
    },
    "openai": {
        "name": "OpenAI",
        "provider_type": "openai",
        "api_url": "https://api.openai.com/v1/chat/completions",
        "model": DEFAULT_MODEL,
    },
    "claude": {
        "name": "Claude",
        "provider_type": "anthropic",
        "api_url": "https://api.anthropic.com/v1/messages",
        "model": DEFAULT_ANTHROPIC_MODEL,
    },
}


@dataclass
class AIProviderConfig:
    """One persisted AI provider profile."""

    name: str
    api_token: str
    api_url: str
    provider_type: str = DEFAULT_PROVIDER_TYPE
    model: str = DEFAULT_MODEL

    @classmethod
    def from_dict(cls, data: dict[str, Any], fallback_name: str) -> "AIProviderConfig":
        """Build a provider profile from JSON-safe data with defaults."""

        provider_name = str(data.get("name") or fallback_name).strip() or fallback_name
        defaults = provider_defaults(provider_name)
        return cls(
            name=provider_name,
            api_token=str(data.get("api_token", "")).strip(),
            api_url=str(data.get("api_url") or defaults["api_url"]).strip(),
            provider_type=validate_provider_type(
                str(data.get("provider_type") or defaults["provider_type"])
            ),
            model=str(data.get("model") or defaults["model"]).strip(),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize provider data for disk storage."""

        return asdict(self)


@dataclass
class AppConfig:
    """Runtime settings persisted in a JSON file."""

    providers: dict[str, AIProviderConfig] = field(default_factory=dict)
    active_provider: str = DEFAULT_PROVIDER_NAME
    ui_language: str = DEFAULT_LANGUAGE
    model_output_language: str = DEFAULT_LANGUAGE
    retry_wait_seconds: int = DEFAULT_RETRY_WAIT_SECONDS
    retry_attempts: int = DEFAULT_RETRY_ATTEMPTS
    conventional_commits: bool = DEFAULT_CONVENTIONAL_COMMITS
    pull_strategy: str = DEFAULT_PULL_STRATEGY
    auto_stash: bool = DEFAULT_AUTO_STASH
    auto_split_commits: bool = DEFAULT_AUTO_SPLIT_COMMITS

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppConfig":
        """Build config from JSON-safe data with defaults."""

        providers = _providers_from_data(data)
        active_provider = str(data.get("active_provider") or DEFAULT_PROVIDER_NAME).strip()
        if active_provider not in providers:
            active_provider = next(iter(providers), DEFAULT_PROVIDER_NAME)
        return cls(
            providers=providers,
            active_provider=active_provider,
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
            conventional_commits=_bool(
                data.get("conventional_commits"),
                DEFAULT_CONVENTIONAL_COMMITS,
            ),
            pull_strategy=validate_pull_strategy(
                str(data.get("pull_strategy") or DEFAULT_PULL_STRATEGY)
            ),
            auto_stash=_bool(data.get("auto_stash"), DEFAULT_AUTO_STASH),
            auto_split_commits=_bool(
                data.get("auto_split_commits"),
                DEFAULT_AUTO_SPLIT_COMMITS,
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize config for disk storage."""

        return {
            "providers": {
                name: provider.to_dict() for name, provider in self.providers.items()
            },
            "active_provider": self.active_provider,
            "ui_language": self.ui_language,
            "model_output_language": self.model_output_language,
            "retry_wait_seconds": self.retry_wait_seconds,
            "retry_attempts": self.retry_attempts,
            "conventional_commits": self.conventional_commits,
            "pull_strategy": self.pull_strategy,
            "auto_stash": self.auto_stash,
            "auto_split_commits": self.auto_split_commits,
        }

    def active_ai_provider(self) -> AIProviderConfig:
        """Return the currently selected AI provider profile."""

        provider = self.providers.get(self.active_provider)
        if provider is not None:
            return provider
        if self.providers:
            return next(iter(self.providers.values()))
        return AIProviderConfig.from_dict({}, DEFAULT_PROVIDER_NAME)


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

    return AppConfig(
        providers={
            DEFAULT_PROVIDER_NAME: AIProviderConfig.from_dict({}, DEFAULT_PROVIDER_NAME),
        },
        active_provider=DEFAULT_PROVIDER_NAME,
    )


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


def validate_provider_name(value: str) -> str:
    """Validate and normalize an AI provider profile name."""

    normalized = value.strip()
    if not normalized:
        raise ValueError("value_required")
    if any(character in normalized for character in "\r\n\t"):
        raise ValueError("invalid_provider_name")
    return normalized


def validate_provider_type(value: str) -> str:
    """Validate and normalize an AI provider protocol type."""

    normalized = value.strip().lower()
    aliases = {
        "gapgpt": "openai",
        "openai-compatible": "openai",
        "openai compatible": "openai",
        "claude": "anthropic",
        "anthropic": "anthropic",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized not in AI_PROVIDER_TYPES:
        raise ValueError("invalid_provider_type")
    return normalized


def provider_defaults(name: str) -> dict[str, str]:
    """Return default provider settings for a known provider name."""

    return PROVIDER_DEFAULTS.get(name.strip().lower(), PROVIDER_DEFAULTS["gapgpt"])


def validate_bool(value: str) -> bool:
    """Validate a localized yes/no-like setting value and return a boolean."""

    normalized = value.strip().lower()
    if normalized in {"yes", "y", "true", "1", "on", "بله", "آری", "روشن"}:
        return True
    if normalized in {"no", "n", "false", "0", "off", "خیر", "نه", "خاموش"}:
        return False
    raise ValueError("invalid_bool")


def validate_pull_strategy(value: str) -> str:
    """Validate and normalize the Git pull integration strategy."""

    normalized = value.strip().lower()
    if normalized in PULL_STRATEGIES:
        return normalized
    raise ValueError("invalid_pull_strategy")


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


def _providers_from_data(data: dict[str, Any]) -> dict[str, AIProviderConfig]:
    """Read provider profiles and migrate legacy flat AI settings when needed."""

    raw_providers = data.get("providers")
    providers: dict[str, AIProviderConfig] = {}
    if isinstance(raw_providers, dict):
        for fallback_name, raw_provider in raw_providers.items():
            if isinstance(raw_provider, dict):
                provider = AIProviderConfig.from_dict(raw_provider, str(fallback_name))
                providers[provider.name] = provider

    # Legacy config stored the GapGPT token, URL, and model at the top level.
    if not providers:
        legacy_provider = AIProviderConfig.from_dict(
            {
                "name": DEFAULT_PROVIDER_NAME,
                "api_token": data.get("api_token", ""),
                "api_url": data.get("api_url", DEFAULT_API_URL),
                "provider_type": DEFAULT_PROVIDER_TYPE,
                "model": data.get("model", DEFAULT_MODEL),
            },
            DEFAULT_PROVIDER_NAME,
        )
        providers[legacy_provider.name] = legacy_provider

    return providers
