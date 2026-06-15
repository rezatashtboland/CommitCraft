"""GapGPT-compatible ChatGPT-like API client."""

from __future__ import annotations

import time
from dataclasses import dataclass
from collections.abc import Callable
from typing import Any

import requests

from .config import AppConfig


class AIClientError(RuntimeError):
    """Raised when AI response cannot be obtained."""


@dataclass(frozen=True)
class AIResponse:
    """AI-generated commit data."""

    message: str
    raw: str


class GapGPTClient:
    """Client for gapgpt API endpoints compatible with OpenAI chat completions."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def generate_commit_message(
        self,
        diff: str,
        on_retry: Callable[[int, int, Exception], None] | None = None,
    ) -> AIResponse:
        """Generate a commit message from Git diff with retry logic."""

        prompt = self._build_prompt(diff)
        payload = {
            "model": self.config.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert software engineer who writes concise, accurate Git commit messages.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }

        last_error: Exception | None = None
        for attempt in range(1, self.config.retry_attempts + 1):
            try:
                # GapGPT exposes an OpenAI-compatible chat-completions endpoint.
                response = requests.post(
                    self.config.api_url,
                    headers={
                        "Authorization": f"Bearer {self.config.api_token}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=60,
                )
                response.raise_for_status()
                data = response.json()
                content = self._extract_content(data)
                message = self._sanitize_commit_message(content)
                if message:
                    return AIResponse(message=message, raw=content)
                raise AIClientError("ai_empty_message")
            except (requests.RequestException, ValueError, KeyError, AIClientError) as exc:
                last_error = exc
                if attempt < self.config.retry_attempts:
                    if on_retry is not None:
                        on_retry(attempt, self.config.retry_attempts, exc)
                    time.sleep(self.config.retry_wait_seconds)

        if isinstance(last_error, AIClientError):
            raise AIClientError(str(last_error)) from last_error
        raise AIClientError("ai_request_failed") from last_error

    def _build_prompt(self, diff: str) -> str:
        """Create model prompt while keeping output language configurable."""

        language = "Persian" if self.config.model_output_language == "fa" else "English"
        return f"""
Analyze the following Git changes and write exactly one commit message.

Output language: {language}

Commit message structure:
- First line: Conventional Commit style summary, e.g. "feat: add AI commit assistant".
- Optional body: 1-3 short bullet points only when useful.
- No Markdown code fences.
- No explanations outside the commit message.
- Keep the first line under 72 characters when possible.
- Use one of these types when appropriate: feat, fix, docs, style, refactor, test, chore, perf, ci, build.

Git changes:
{diff[:30000]}
""".strip()

    def _extract_content(self, data: dict[str, Any]) -> str:
        """Extract assistant message from ChatGPT-like response."""

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
