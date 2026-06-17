"""Commit message normalization helpers."""

from __future__ import annotations


def normalize_commit_message(message: str) -> str:
    """Trim surrounding whitespace while preserving intentional body paragraphs."""

    lines = [line.rstrip() for line in message.strip().splitlines()]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines).strip()
