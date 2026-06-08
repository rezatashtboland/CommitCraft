"""Application orchestration for CommitCraft."""

from __future__ import annotations

from rich.table import Table

from .ai_client import AIClientError, GapGPTClient
from .config import (
    DEFAULT_API_URL,
    DEFAULT_RETRY_ATTEMPTS,
    DEFAULT_RETRY_WAIT_SECONDS,
    AppConfig,
    ConfigManager,
)
from .dependencies import DependencyInstaller
from .git_service import ChangedFile, GitError, GitService
from .i18n import DEFAULT_LANGUAGE, Translator, normalize_language
from .terminal import TerminalUI


class CommitCraftApp:
    """Main application controller."""

    def __init__(self) -> None:
        self.config_manager = ConfigManager()
        self.translator = Translator(DEFAULT_LANGUAGE)
        self.ui = TerminalUI(self.translator)
        self.git = GitService()
        self.config: AppConfig | None = None

    def run(self) -> None:
        """Run the menu loop until user exits."""

        try:
            self._bootstrap()
            while True:
                choice = self.ui.menu()
                if choice in {"", "1"}:
                    self._handle_commit()
                elif choice == "2":
                    self._handle_push()
                elif choice == "0":
                    break
                else:
                    self.ui.warning(self.ui.translator.text("invalid_choice"))
                self.ui.pause()
        except KeyboardInterrupt:
            self.ui.warning(self.ui.translator.text("ctrl_c"))
        except Exception as exc:  # pragma: no cover - final safety net.
            self.ui.error(f"{self.ui.translator.text('error')}: {exc}")

    def _bootstrap(self) -> None:
        """Prepare dependencies, config, and Git prerequisites."""

        if not self.config_manager.exists():
            self.ui.info(self.ui.translator.text("dependency_check"))
            self._ensure_dependencies()
            self.ui.warning(self.ui.translator.text("config_missing"))
            self.config = self._create_config()
            self.config_manager.save(self.config)
            self.ui.success(self.ui.translator.text("config_saved"))
        else:
            self.config = self.config_manager.load()

        self._apply_config_language()
        self.git.ensure_available()

    def _ensure_dependencies(self) -> None:
        """Install missing dependencies on first run."""

        installer = DependencyInstaller()
        missing = installer.missing()
        if not missing:
            return

        # First-run bootstrap keeps the script usable on fresh systems.
        self.ui.info(
            f"{self.ui.translator.text('dependency_installing')}: "
            f"{', '.join(dependency.install_spec for dependency in missing)}"
        )
        ok, output = installer.install(missing)
        if ok:
            return

        self.ui.error(self.ui.translator.text("dependency_failed"))
        for dependency in missing:
            command = f"python -m pip install {dependency.install_spec}"
            self.ui.warning(
                f"{self.ui.translator.text('dependency_manual')}: "
                f"{dependency.package} >= {dependency.version} | {command}"
            )
        if output:
            self.ui.panel("pip", output, style="red")

    def _create_config(self) -> AppConfig:
        """Ask user for first-run config values."""

        api_token = self.ui.ask(self.ui.translator.text("api_token"), password=True)
        api_url = self.ui.ask(
            f"{self.ui.translator.text('api_url')} ({self.ui.translator.text('leave_default')})",
            default=DEFAULT_API_URL,
        )
        ui_language = normalize_language(
            self.ui.ask(
                f"{self.ui.translator.text('ui_language')} [fa/en]",
                default=DEFAULT_LANGUAGE,
            )
        )
        model_language = normalize_language(
            self.ui.ask(
                f"{self.ui.translator.text('model_language')} [fa/en]",
                default=DEFAULT_LANGUAGE,
            )
        )
        retry_wait = self.ui.ask(
            self.ui.translator.text("retry_wait"),
            default=str(DEFAULT_RETRY_WAIT_SECONDS),
        )
        retry_attempts = self.ui.ask(
            self.ui.translator.text("retry_attempts"),
            default=str(DEFAULT_RETRY_ATTEMPTS),
        )
        return AppConfig.from_dict(
            {
                "api_token": api_token,
                "api_url": api_url,
                "ui_language": ui_language,
                "model_output_language": model_language,
                "retry_wait_seconds": retry_wait,
                "retry_attempts": retry_attempts,
            }
        )

    def _apply_config_language(self) -> None:
        """Apply configured UI language."""

        if self.config is None:
            return
        self.translator = Translator(self.config.ui_language)
        self.ui.set_language(self.translator)

    def _handle_commit(self) -> None:
        """Select changed files, generate message, and commit."""

        if self.config is None:
            return

        try:
            changed_files = self.git.changed_files()
            if not changed_files:
                self.ui.warning(self.ui.translator.text("no_changes"))
                return

            # All files start selected; the user removes unwanted indexes.
            selected = self._select_files(changed_files)
            if not selected:
                self.ui.warning(self.ui.translator.text("nothing_selected"))
                return

            diff = self.git.diff_for_files(selected)
            if not diff.strip():
                diff = "\n".join(selected)

            self.ui.info(self.ui.translator.text("generating"))
            ai_response = GapGPTClient(self.config).generate_commit_message(
                diff,
                on_retry=self._show_ai_retry,
            )
            self.ui.panel(
                self.ui.translator.text("commit_message"),
                ai_response.message,
                style="bright_green",
            )

            if not self.ui.confirm(self.ui.translator.text("confirm_commit"), default=True):
                return

            self.ui.info(self.ui.translator.text("committing"))
            self.git.add(selected)
            self.git.commit(ai_response.message)
            self.ui.success(self.ui.translator.text("commit_done"))
        except (GitError, AIClientError) as exc:
            self.ui.error(self._friendly_error(exc))

    def _select_files(self, changed_files: list[ChangedFile]) -> list[str]:
        """Show changed files and remove user-specified items from default selection."""

        table = Table(
            title=self.ui.display(self.ui.translator.text("changed_files")),
            border_style="bright_blue",
        )
        table.add_column("#", style="bold yellow", justify="right")
        table.add_column("Status", style="cyan")
        table.add_column("Path", style="white")
        for index, file in enumerate(changed_files, start=1):
            table.add_row(str(index), file.status, self.ui.display(file.path))
        self.ui.console.print(table)
        self.ui.info(self.ui.translator.text("selection_help"))
        raw = self.ui.ask("Remove / حذف", default="")
        removed_indexes = self._parse_indexes(raw, len(changed_files))
        return [
            file.path
            for index, file in enumerate(changed_files, start=1)
            if index not in removed_indexes
        ]

    def _parse_indexes(self, raw: str, max_index: int) -> set[int]:
        """Parse comma-separated indexes."""

        indexes: set[int] = set()
        for part in raw.replace(" ", "").split(","):
            if not part:
                continue
            try:
                index = int(part)
            except ValueError:
                continue
            if 1 <= index <= max_index:
                indexes.add(index)
        return indexes

    def _handle_push(self) -> None:
        """Push current branch."""

        try:
            branch = self.git.current_branch()
            self.ui.info(f"{self.ui.translator.text('current_branch')}: {branch}")
            if not self.ui.confirm(self.ui.translator.text("push_confirm"), default=True):
                return
            self.ui.info(self.ui.translator.text("pushing"))
            self.git.push()
            self.ui.success(self.ui.translator.text("push_done"))
        except GitError as exc:
            self.ui.error(self._friendly_error(exc))

    def _show_ai_retry(self, attempt: int, total: int, exc: Exception) -> None:
        """Show retry progress for failed AI requests."""

        if self.config is None:
            return
        self.ui.warning(
            f"{self.ui.translator.text('ai_retry')} "
            f"{attempt}/{total} ({self.config.retry_wait_seconds}s): {exc}"
        )

    def _friendly_error(self, exc: Exception) -> str:
        """Translate known error keys."""

        message = str(exc)
        if message in {"git_missing", "git_not_repo"}:
            return self.ui.translator.text(message)
        return message
