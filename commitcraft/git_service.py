"""Git command wrapper."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


class GitError(RuntimeError):
    """Raised when a Git command fails."""


@dataclass(frozen=True)
class ChangedFile:
    """A changed file reported by Git porcelain status."""

    status: str
    path: str


class GitService:
    """Service responsible for all Git interactions."""

    def __init__(self, repo_path: str = ".") -> None:
        self.repo_path = repo_path

    def ensure_available(self) -> None:
        """Ensure Git is installed and current directory is a repository."""

        try:
            self._run(["git", "--version"])
        except FileNotFoundError as exc:
            raise GitError("git_missing") from exc

        result = self._run(["git", "rev-parse", "--is-inside-work-tree"], check=False)
        if result.returncode != 0 or result.stdout.strip() != "true":
            raise GitError("git_not_repo")

    def changed_files(self) -> list[ChangedFile]:
        """Return changed files using porcelain v1 output."""

        result = self._run(["git", "status", "--porcelain"], check=True)
        files: list[ChangedFile] = []
        for line in result.stdout.splitlines():
            if not line:
                continue
            status = line[:2].strip() or "?"
            path = line[3:].strip()
            if " -> " in path:
                path = path.split(" -> ", maxsplit=1)[1]
            files.append(ChangedFile(status=status, path=path))
        return files

    def diff_for_files(self, files: list[str]) -> str:
        """Return staged and unstaged diff for selected files."""

        if not files:
            return ""
        diff_parts = []
        unstaged = self._run(["git", "diff", "--", *files], check=True).stdout
        staged = self._run(["git", "diff", "--cached", "--", *files], check=True).stdout
        name_status = self._run(["git", "status", "--short", "--", *files], check=True).stdout
        untracked = self._untracked_file_snapshots(files)
        for title, body in (
            ("STATUS", name_status),
            ("UNSTAGED DIFF", unstaged),
            ("STAGED DIFF", staged),
            ("UNTRACKED FILE CONTENT", untracked),
        ):
            if body.strip():
                diff_parts.append(f"## {title}\n{body}")
        return "\n\n".join(diff_parts)

    def add(self, files: list[str]) -> None:
        """Stage selected files."""

        if not files:
            return
        self._run(["git", "add", "--", *files], check=True)

    def commit(self, message: str) -> None:
        """Create a Git commit."""

        self._run(["git", "commit", "-m", message], check=True)

    def push(self) -> None:
        """Push current branch to its configured upstream."""

        self._run(["git", "push"], check=True)

    def current_branch(self) -> str:
        """Return current branch name."""

        result = self._run(["git", "branch", "--show-current"], check=True)
        return result.stdout.strip() or "HEAD"

    def _untracked_file_snapshots(self, files: list[str]) -> str:
        """Return readable snapshots for selected untracked text files."""

        status = self._run(["git", "status", "--short", "--", *files], check=True).stdout
        untracked_paths = [
            line[3:].strip()
            for line in status.splitlines()
            if line.startswith("?? ")
        ]
        snapshots: list[str] = []
        for relative_path in untracked_paths:
            file_path = Path(self.repo_path) / relative_path
            if not file_path.is_file():
                continue
            try:
                content = file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                snapshots.append(f"### {relative_path}\n<binary or non-UTF-8 file>")
                continue
            snapshots.append(f"### {relative_path}\n{content[:8000]}")
        return "\n\n".join(snapshots)

    def _run(
        self,
        command: list[str],
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        """Run a Git command and raise a friendly error on failure."""

        result = subprocess.run(
            command,
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            check=False,
        )
        if check and result.returncode != 0:
            message = result.stderr.strip() or result.stdout.strip() or "Git command failed."
            raise GitError(message)
        return result
