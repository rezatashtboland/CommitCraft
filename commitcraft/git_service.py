"""Git command wrapper."""

from __future__ import annotations

import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .subprocess_utils import run_capture


class GitError(RuntimeError):
    """Raised when a Git command fails."""


class GitConflictError(GitError):
    """Raised when Git reports a merge, rebase, or stash conflict."""


class GitAuthError(GitError):
    """Raised when Git reports authentication or authorization failure."""


class GitTransientError(GitError):
    """Raised when Git reports a retryable transport failure."""


@dataclass(frozen=True)
class ChangedFile:
    """A changed file reported by Git porcelain status."""

    status: str
    path: str


@dataclass(frozen=True)
class GitOperationResult:
    """Captured output from a completed Git workflow operation."""

    stdout: str = ""
    stderr: str = ""

    @property
    def output(self) -> str:
        """Return combined Git output for user-facing diagnostics."""

        return "\n".join(part for part in (self.stdout.strip(), self.stderr.strip()) if part)


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

    def fetch(
        self,
        *,
        attempts: int,
        wait_seconds: int,
        on_retry: Callable[[int, int, GitError], None] | None = None,
    ) -> GitOperationResult:
        """Fetch remote refs, retrying only transient transport failures."""

        return self._run_retryable(
            ["git", "fetch", "--prune"],
            attempts=attempts,
            wait_seconds=wait_seconds,
            on_retry=on_retry,
        )

    def pull(
        self,
        strategy: str,
        *,
        auto_stash: bool,
        attempts: int,
        wait_seconds: int,
        on_retry: Callable[[int, int, GitError], None] | None = None,
    ) -> GitOperationResult:
        """Pull from upstream using merge or rebase with optional safe auto-stash."""

        command = ["git", "pull", "--rebase" if strategy == "rebase" else "--no-rebase"]
        return self._run_with_optional_stash(
            command,
            auto_stash=auto_stash,
            attempts=attempts,
            wait_seconds=wait_seconds,
            on_retry=on_retry,
        )

    def sync(
        self,
        strategy: str,
        *,
        auto_stash: bool,
        attempts: int,
        wait_seconds: int,
        on_retry: Callable[[int, int, GitError], None] | None = None,
    ) -> GitOperationResult:
        """Pull from upstream and push local commits after a successful pull."""

        pull_result = self.pull(
            strategy,
            auto_stash=auto_stash,
            attempts=attempts,
            wait_seconds=wait_seconds,
            on_retry=on_retry,
        )
        push_result = self._run_retryable(
            ["git", "push"],
            attempts=attempts,
            wait_seconds=wait_seconds,
            on_retry=on_retry,
        )
        return GitOperationResult(
            stdout="\n".join(part for part in (pull_result.stdout, push_result.stdout) if part),
            stderr="\n".join(part for part in (pull_result.stderr, push_result.stderr) if part),
        )

    def current_branch(self) -> str:
        """Return current branch name."""

        result = self._run(["git", "branch", "--show-current"], check=True)
        return result.stdout.strip() or "HEAD"

    def has_uncommitted_changes(self) -> bool:
        """Return whether the working tree or index has uncommitted changes."""

        result = self._run(["git", "status", "--porcelain=v1", "-z"], check=True)
        return bool(result.stdout.strip("\0"))

    def in_rebase(self) -> bool:
        """Return whether the repository is currently in a rebase state."""

        git_dir = self._git_dir()
        return (git_dir / "rebase-merge").exists() or (git_dir / "rebase-apply").exists()

    def in_merge(self) -> bool:
        """Return whether the repository is currently in an unresolved merge state."""

        return (self._git_dir() / "MERGE_HEAD").exists()

    def abort_integration(self) -> None:
        """Abort an active rebase or merge operation when possible."""

        if self.in_rebase():
            self._run(["git", "rebase", "--abort"], check=True)
            return
        if self.in_merge():
            self._run(["git", "merge", "--abort"], check=True)

    def _run_with_optional_stash(
        self,
        command: list[str],
        *,
        auto_stash: bool,
        attempts: int,
        wait_seconds: int,
        on_retry: Callable[[int, int, GitError], None] | None = None,
    ) -> GitOperationResult:
        """Run a Git integration command and restore an auto-stash afterward."""

        stash_ref: str | None = None
        if auto_stash and self.has_uncommitted_changes():
            stash_ref = self._create_autostash()
        try:
            return self._run_retryable(
                command,
                attempts=attempts,
                wait_seconds=wait_seconds,
                on_retry=on_retry,
            )
        finally:
            if stash_ref is not None and not self.in_merge() and not self.in_rebase():
                self._restore_autostash(stash_ref)

    def _create_autostash(self) -> str | None:
        """Create a named stash for local work and return its ref if one was made."""

        before = self._stash_top_oid()
        self._run(
            ["git", "stash", "push", "--include-untracked", "-m", "CommitCraft auto-stash"],
            check=True,
        )
        after = self._stash_top_oid()
        return "stash@{0}" if after and after != before else None

    def _restore_autostash(self, stash_ref: str) -> None:
        """Restore a previously created auto-stash and classify apply conflicts."""

        result = self._run(["git", "stash", "pop", "--index", stash_ref], check=False)
        if result.returncode == 0:
            return
        if self._has_unmerged_paths(result.stdout + result.stderr):
            raise GitConflictError("git_stash_conflict")
        raise self._classify_failed_result(result)

    def _stash_top_oid(self) -> str | None:
        """Return the current top stash object id, or None when the stash is empty."""

        result = self._run(["git", "stash", "list", "--format=%H", "-n", "1"], check=True)
        return result.stdout.strip() or None

    def _git_dir(self) -> Path:
        """Return the resolved .git directory path for the current working tree."""

        result = self._run(["git", "rev-parse", "--git-dir"], check=True)
        git_dir = Path(result.stdout.strip())
        if git_dir.is_absolute():
            return git_dir
        return Path(self.repo_path) / git_dir

    def _run_retryable(
        self,
        command: list[str],
        *,
        attempts: int,
        wait_seconds: int,
        on_retry: Callable[[int, int, GitError], None] | None = None,
    ) -> GitOperationResult:
        """Run a Git command with retry support for transient failures only."""

        last_error: GitError | None = None
        for attempt in range(1, attempts + 1):
            result = self._run(command, check=False)
            if result.returncode == 0:
                return GitOperationResult(stdout=result.stdout, stderr=result.stderr)
            error = self._classify_failed_result(result)
            if not isinstance(error, GitTransientError) or attempt >= attempts:
                raise error
            last_error = error
            if on_retry is not None:
                on_retry(attempt, attempts, error)
            time.sleep(wait_seconds)
        raise last_error or GitError("git_command_failed")

    def _classify_failed_result(self, result: subprocess.CompletedProcess[str]) -> GitError:
        """Map failed Git output to a retry, conflict, auth, or generic error."""

        output = "\n".join(part for part in (result.stdout, result.stderr) if part).strip()
        lowered = output.lower()
        if self._has_unmerged_paths(output) or self.in_merge() or self.in_rebase():
            return GitConflictError(output or "git_conflict")
        if any(pattern in lowered for pattern in _AUTH_ERROR_PATTERNS):
            return GitAuthError(output or "git_auth_failed")
        if any(pattern in lowered for pattern in _TRANSIENT_ERROR_PATTERNS):
            return GitTransientError(output or "git_transient_failure")
        return GitError(output or "git_command_failed")

    def _has_unmerged_paths(self, output: str) -> bool:
        """Return whether Git output or status indicates unresolved conflicts."""

        lowered = output.lower()
        if any(pattern in lowered for pattern in _CONFLICT_ERROR_PATTERNS):
            return True
        return any("U" in file.status or file.status in {"AA", "DD"} for file in self._status_entries())

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


_AUTH_ERROR_PATTERNS = (
    "authentication failed",
    "could not read username",
    "could not read password",
    "permission denied",
    "access denied",
    "403",
    "401",
    "repository not found",
)

_TRANSIENT_ERROR_PATTERNS = (
    "could not resolve host",
    "failed to connect",
    "connection timed out",
    "connection timeout",
    "connection reset",
    "network is unreachable",
    "remote end hung up unexpectedly",
    "the remote end hung up unexpectedly",
    "operation timed out",
    "tls connection",
    "ssl",
    "http 500",
    "http 502",
    "http 503",
    "http 504",
)

_CONFLICT_ERROR_PATTERNS = (
    "conflict",
    "merge failed",
    "fix conflicts",
    "unmerged",
    "you have divergent branches",
    "cannot rebase",
    "needs merge",
    "could not apply",
)
