"""Conventional Commit validation and normalization helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass


CONVENTIONAL_TYPES = (
    "feat",
    "fix",
    "docs",
    "style",
    "refactor",
    "perf",
    "test",
    "build",
    "ci",
    "chore",
    "revert",
)
SUBJECT_MAX_LENGTH = 72
HEADER_PATTERN = re.compile(
    rf"^({'|'.join(CONVENTIONAL_TYPES)})(\([a-z0-9._/-]+\))?(!)?: .+"
)
NON_IMPERATIVE_WORDS = {
    "added",
    "adds",
    "adding",
    "changed",
    "changes",
    "changing",
    "fixed",
    "fixes",
    "fixing",
    "updated",
    "updates",
    "updating",
    "removed",
    "removes",
    "removing",
}


@dataclass(frozen=True)
class ValidationResult:
    """Result object describing whether a commit message is conventional."""

    is_valid: bool
    errors: tuple[str, ...] = ()


def validate_conventional_commit(message: str) -> ValidationResult:
    """Validate a commit message against project Conventional Commit rules."""

    errors: list[str] = []
    lines = message.strip().splitlines()
    header = lines[0].strip() if lines else ""
    if not HEADER_PATTERN.match(header):
        errors.append("conventional_invalid_header")
    elif not _has_imperative_subject(header):
        errors.append("conventional_imperative_subject")
    if len(header) > SUBJECT_MAX_LENGTH:
        errors.append("conventional_subject_too_long")
    if header.endswith("."):
        errors.append("conventional_subject_period")
    if len(lines) > 1 and lines[1].strip():
        errors.append("conventional_blank_line_required")
    if "!" in header and not _has_breaking_footer(lines):
        errors.append("conventional_breaking_footer_required")
    return ValidationResult(is_valid=not errors, errors=tuple(errors))


def normalize_commit_message(message: str) -> str:
    """Trim surrounding whitespace while preserving intentional body paragraphs."""

    lines = [line.rstrip() for line in message.strip().splitlines()]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines).strip()


def _has_breaking_footer(lines: list[str]) -> bool:
    """Return whether a message includes the required breaking-change footer."""

    return any(line.startswith("BREAKING CHANGE: ") for line in lines[1:])


def _has_imperative_subject(header: str) -> bool:
    """Use conservative wording checks to reject common non-imperative subjects."""

    description = header.split(": ", 1)[1].strip().lower()
    first_word = description.split(maxsplit=1)[0] if description else ""
    return bool(first_word) and first_word not in NON_IMPERATIVE_WORDS
