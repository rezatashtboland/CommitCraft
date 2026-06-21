"""AI provider clients for commit messages and split planning."""

from __future__ import annotations

import time
from dataclasses import dataclass
from collections.abc import Callable
from typing import Any

import requests

from .config import AIProviderConfig, AppConfig
from .logging_config import get_logger


class AIClientError(RuntimeError):
    """Raised when AI response cannot be obtained."""


@dataclass(frozen=True)
class AIResponse:
    """AI-generated commit data."""

    message: str
    raw: str


@dataclass(frozen=True)
class CommitSplit:
    """One AI-proposed logical commit group."""

    title: str
    files: list[str]


@dataclass(frozen=True)
class CommitSplitPlan:
    """AI-generated commit split plan."""

    groups: list[CommitSplit]
    raw: str


class AIClient:
    """Client for OpenAI-compatible and Anthropic message endpoints."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.provider = config.active_ai_provider()
        self.logger = get_logger()

    def generate_commit_message(
        self,
        diff: str,
        conventional: bool = True,
        on_retry: Callable[[int, int, Exception], None] | None = None,
    ) -> AIResponse:
        """Generate a commit message from Git diff with retry logic."""

        prompt = self._build_prompt(diff, conventional)
        self.logger.info("Generating commit message with provider %s", self.provider.name)
        content = self._request_text(
            prompt,
            system=(
                "You are an expert software engineer who writes concise, "
                "accurate Git commit messages."
            ),
            on_retry=on_retry,
        )
        message = self._sanitize_commit_message(content)
        if not message:
            raise AIClientError("ai_empty_message")
        return AIResponse(message=message, raw=content)

    def split_commit_groups(
        self,
        files: list[str],
        diff: str,
        on_retry: Callable[[int, int, Exception], None] | None = None,
    ) -> CommitSplitPlan:
        """Ask AI to split selected files into logical commit groups."""

        prompt = self._build_split_prompt(files, diff)
        self.logger.info("Requesting commit split plan for %s file(s)", len(files))
        content = self._request_text(
            prompt,
            system=(
                "You are an expert software engineer who groups Git changes into "
                "small, reviewable logical commits."
            ),
            on_retry=on_retry,
        )
        return CommitSplitPlan(groups=self._parse_split_groups(content, files), raw=content)

    def _request_text(
        self,
        prompt: str,
        *,
        system: str,
        on_retry: Callable[[int, int, Exception], None] | None = None,
    ) -> str:
        """Run the active provider request and return assistant text."""

        last_error: Exception | None = None
        for attempt in range(1, self.config.retry_attempts + 1):
            try:
                self.logger.debug(
                    "AI request attempt %s/%s to %s",
                    attempt,
                    self.config.retry_attempts,
                    self.provider.api_url,
                )
                response = requests.post(
                    self.provider.api_url,
                    headers=self._headers(self.provider),
                    json=self._payload(self.provider, prompt, system),
                    timeout=60,
                )
                response.raise_for_status()
                data = response.json()
                content = self._extract_content(data, self.provider)
                if content.strip():
                    return content.strip()
                raise AIClientError("ai_empty_message")
            except (requests.RequestException, ValueError, KeyError, AIClientError) as exc:
                last_error = exc
                if attempt < self.config.retry_attempts:
                    self.logger.warning(
                        "AI request attempt %s/%s failed: %s",
                        attempt,
                        self.config.retry_attempts,
                        exc,
                    )
                    if on_retry is not None:
                        on_retry(attempt, self.config.retry_attempts, exc)
                    time.sleep(self.config.retry_wait_seconds)

        if isinstance(last_error, AIClientError):
            self.logger.error("AI request failed with known error: %s", last_error)
            raise AIClientError(str(last_error)) from last_error
        self.logger.error("AI request failed after retries: %s", last_error)
        raise AIClientError("ai_request_failed") from last_error

    def _headers(self, provider: AIProviderConfig) -> dict[str, str]:
        """Build provider-specific request headers without exposing secrets."""

        if provider.provider_type == "anthropic":
            return {
                "x-api-key": provider.api_token,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            }
        return {
            "Authorization": f"Bearer {provider.api_token}",
            "Content-Type": "application/json",
        }

    def _payload(self, provider: AIProviderConfig, prompt: str, system: str) -> dict[str, Any]:
        """Build a provider-specific JSON payload."""

        if provider.provider_type == "anthropic":
            return {
                "model": provider.model,
                "system": system,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 1200,
                "temperature": 0.2,
            }
        return {
            "model": provider.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }

    def _build_prompt(self, diff: str, conventional: bool) -> str:
        """Create model prompt while keeping output language configurable."""

        language = "Persian" if self.config.model_output_language == "fa" else "English"
        if not conventional:
            return f"""
Analyze the following Git changes and write exactly one concise free-form commit message.

Output language: {language}

Rules:
- No Markdown code fences.
- No explanations outside the commit message.
- Use an optional body only when it clarifies important details.

Git changes:
{diff[:30000]}
""".strip()
        return f"""
Analyze the following Git changes and write exactly one commit message.

Output language: {language}

Commit message structure:
- First line: type(scope): description, type: description, type(scope)!: description,
  or type!: description.
- Allowed types: feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert.
- Infer the most accurate type and a short lowercase scope from the staged diff.
- Use an imperative, present-tense description with no final period.
- Add a blank line before any body or footer.
- Optional body: 1-5 short lines only when useful.
- For breaking changes, add ! in the header and include a BREAKING CHANGE: footer.
- No Markdown code fences.
- No explanations outside the commit message.

Git changes:
{diff[:30000]}
""".strip()

    def _build_split_prompt(self, files: list[str], diff: str) -> str:
        """Create model prompt for logical commit grouping."""

        file_list = "\n".join(f"- {path}" for path in files)
        return f"""
Analyze these selected Git changes and split them into logical commits only when the
changes are unrelated by feature, concern, or context.

Return strict JSON only, with this shape:
{{
  "groups": [
    {{"title": "short reason", "files": ["path/from/list"]}}
  ]
}}

Rules:
- Every file must appear exactly once.
- Use only paths from the selected file list.
- Keep related changes together.
- Return one group when the changes belong in one commit.
- No Markdown code fences.
- No explanations outside JSON.

Selected files:
{file_list}

Git changes:
{diff[:30000]}
""".strip()

    def _extract_content(self, data: dict[str, Any], provider: AIProviderConfig) -> str:
        """Extract assistant message from a provider response."""

        if provider.provider_type == "anthropic":
            content_blocks = data.get("content")
            if not isinstance(content_blocks, list):
                raise AIClientError("ai_missing_content")
            text_parts = [
                block.get("text", "")
                for block in content_blocks
                if isinstance(block, dict) and block.get("type") == "text"
            ]
            content = "\n".join(part for part in text_parts if part)
            if not content:
                raise AIClientError("ai_missing_content")
            return content.strip()

        choices = data["choices"]
        if not choices:
            raise AIClientError("ai_empty_choices")
        message = choices[0].get("message", {})
        content = message.get("content")
        if not isinstance(content, str):
            raise AIClientError("ai_missing_content")
        return content.strip()

    def _sanitize_commit_message(self, content: str) -> str:
        """Clean AI output for use as a Git commit message."""

        lines = [line.rstrip() for line in content.strip().splitlines()]
        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()
        cleaned = "\n".join(lines).strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`").strip()
        return cleaned

    def _parse_split_groups(self, content: str, files: list[str]) -> list[CommitSplit]:
        """Parse and validate model-proposed split groups."""

        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`").strip()
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:].strip()
        try:
            parsed = __import__("json").loads(cleaned)
        except ValueError as exc:
            raise AIClientError("ai_split_parse_failed") from exc

        raw_groups = parsed.get("groups") if isinstance(parsed, dict) else None
        if not isinstance(raw_groups, list):
            raise AIClientError("ai_split_parse_failed")

        allowed = set(files)
        seen: set[str] = set()
        groups: list[CommitSplit] = []
        for index, raw_group in enumerate(raw_groups, start=1):
            if not isinstance(raw_group, dict):
                raise AIClientError("ai_split_parse_failed")
            raw_files = raw_group.get("files")
            if not isinstance(raw_files, list):
                raise AIClientError("ai_split_parse_failed")
            group_files = []
            for raw_path in raw_files:
                path = str(raw_path)
                if path not in allowed or path in seen:
                    raise AIClientError("ai_split_parse_failed")
                group_files.append(path)
                seen.add(path)
            if group_files:
                title = str(raw_group.get("title") or f"Commit {index}").strip()
                groups.append(CommitSplit(title=title, files=group_files))

        if seen != allowed or not groups:
            raise AIClientError("ai_split_parse_failed")
        return groups


GapGPTClient = AIClient
