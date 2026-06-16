"""Git command wrapper."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from .subprocess_utils import run_capture


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

        return self._status_entries()

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

    def staged_diff_for_files(self, files: list[str]) -> str:
        """Return only the staged diff and status for selected files."""

        if not files:
            return ""
        diff_parts = []
        staged = self._run(["git", "diff", "--cached", "--", *files], check=True).stdout
        name_status = self._run(
            ["git", "diff", "--cached", "--name-status", "--", *files],
            check=True,
        ).stdout
        for title, body in (("STAGED STATUS", name_status), ("STAGED DIFF", staged)):
            if body.strip():
                diff_parts.append(f"## {title}\n{body}")
        return "\n\n".join(diff_parts)

    def add(self, files: list[str]) -> None:
        """Stage selected files."""

        if not files:
            return
        deleted_files, other_files = self._split_deleted_files(files)
        if other_files:
            self._run(["git", "add", "--", *other_files], check=True)
        if deleted_files:
            self._run(["git", "rm", "--ignore-unmatch", "--", *deleted_files], check=True)

    def reset_paths(self, files: list[str]) -> None:
        """Remove selected paths from the index without changing the working tree."""

        if files:
            self._run(["git", "reset", "--", *files], check=True)

    def commit(self, message: str, files: list[str] | None = None) -> None:
        """Create a Git commit, optionally limited to explicit paths."""

        command = ["git", "commit", "-F", "-"]
        if files:
            command.extend(["--only", "--", *files])
        self._run(command, input_text=message, check=True)

    def push(self) -> None:
        """Push current branch to its configured upstream."""

        self._run(["git", "push"], check=True)

    def current_branch(self) -> str:
        """Return current branch name."""

        result = self._run(["git", "branch", "--show-current"], check=True)
        return result.stdout.strip() or "HEAD"

    def _untracked_file_snapshots(self, files: list[str]) -> str:
        """Return readable snapshots for selected untracked text files."""

        untracked_paths = [
            file.path
            for file in self._status_entries(files)
            if file.status == "??"
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

    def _split_deleted_files(self, files: list[str]) -> tuple[list[str], list[str]]:
        """Split selected files into deleted paths and paths safe for git add."""

        deleted_paths = {
            file.path
            for file in self._status_entries(files)
            if "D" in file.status
        }
        deleted_files = [file for file in files if file in deleted_paths]
        other_files = [file for file in files if file not in deleted_paths]
        return deleted_files, other_files

    def _status_entries(self, files: list[str] | None = None) -> list[ChangedFile]:
        """Return status entries using NUL-delimited porcelain output."""

        command = ["git", "status", "--porcelain=v1", "-z"]
        if files is not None:
            command.extend(["--", *files])
        result = self._run(command, check=True)
        changed_files: list[ChangedFile] = []
        entries = result.stdout.rstrip("\0").split("\0")
        index = 0
        while index < len(entries):
            entry = entries[index]
            index += 1
            if not entry:
                continue
            raw_status = entry[:2]
            status = raw_status.strip() or "?"
            path = entry[3:]
            if "R" in raw_status or "C" in raw_status:
                index += 1
            changed_files.append(ChangedFile(status=status, path=path))
        return changed_files

    def _run(
        self,
        command: list[str],
        check: bool = True,
        input_text: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        """Run a Git command and raise a friendly error on failure."""

        result = run_capture(command, cwd=self.repo_path, input=input_text)
        if check and result.returncode != 0:
            message = result.stderr.strip() or result.stdout.strip() or "Git command failed."
            raise GitError(message)
        return result
