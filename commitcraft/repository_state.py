"""Standalone storage for the last confirmed repository path."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from .subprocess_utils import run_capture


STATE_DIR = Path.home() / ".commitcraft"
LAST_REPOSITORY_PATHS_FILE = STATE_DIR / "last_repository_paths.log"


class RepositoryPathStore:
    """Append-only storage for suggested repository paths."""

    def __init__(self, state_file: Path = LAST_REPOSITORY_PATHS_FILE) -> None:
        self.state_file = state_file

    def load(self) -> Path | None:
        """Return the most recently stored path, if it can be read."""

        try:
            lines = self.state_file.read_text(encoding="utf-8").splitlines()
        except OSError:
            return None

        for line in reversed(lines):
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, str) and value.strip():
                return normalize_repository_path(value)
        return None

    def save(self, path: Path) -> None:
        """Remember a confirmed path without touching the main config file."""

        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with self.state_file.open("a", encoding="utf-8") as file:
            json.dump(str(path), file, ensure_ascii=False)
            file.write("\n")


def normalize_repository_path(value: str) -> Path:
    """Normalize a user-entered repository path."""

    normalized = value.strip().strip('"').strip("'")
    return Path(os.path.expandvars(normalized)).expanduser()


def validate_repository_path(raw_path: str) -> Path:
    """Validate a mandatory working-copy path."""

    logger = logging.getLogger("commitcraft")
    if not raw_path.strip().strip('"').strip("'"):
        logger.error("Repository path validation failed: empty path")
        raise ValueError("value_required")
    repo_path = normalize_repository_path(raw_path)
    if not repo_path.exists():
        logger.error("Repository path validation failed: path not found: %s", repo_path)
        raise ValueError("path_not_found")
    if not repo_path.is_dir():
        logger.error("Repository path validation failed: not a directory: %s", repo_path)
        raise ValueError("path_not_directory")
    resolved_path = repo_path.resolve()
    _ensure_git_repository(resolved_path)
    logger.info("Repository path validated: %s", resolved_path)
    return resolved_path


def valid_stored_repository_path(store: RepositoryPathStore) -> Path | None:
    """Return a valid stored repository path, ignoring stale values."""

    repo_path = store.load()
    if repo_path is None:
        return None
    try:
        return validate_repository_path(str(repo_path))
    except (ValueError, GitRepositoryError):
        return None


class GitRepositoryError(RuntimeError):
    """Raised when the selected path cannot be used as a Git repository."""


def _ensure_git_repository(repo_path: Path) -> None:
    """Ensure Git exists and the path is inside a working tree."""

    try:
        run_capture(["git", "--version"])
    except FileNotFoundError as exc:
        raise GitRepositoryError("git_missing") from exc

    result = run_capture(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=str(repo_path),
    )
    if result.returncode != 0 or result.stdout.strip() != "true":
        raise GitRepositoryError("git_not_repo")
