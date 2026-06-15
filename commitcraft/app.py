"""Application orchestration for CommitCraft."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

from rich.table import Table

from .ai_client import AIClientError, GapGPTClient
from .config import (
    DEFAULT_API_URL,
    DEFAULT_RETRY_ATTEMPTS,
    DEFAULT_RETRY_WAIT_SECONDS,
    AppConfig,
    ConfigManager,
    default_config,
    mask_secret,
    validate_api_token,
    validate_api_url,
    validate_language,
    validate_model,
    validate_positive_int,
)
from .dependencies import DependencyInstaller, PERSIAN_DEPENDENCIES
from .git_service import ChangedFile, GitError, GitService
from .i18n import DEFAULT_LANGUAGE, Translator
from .terminal import TerminalUI


SettingValidator = Callable[[str], object]


class SettingsOption:
    """Metadata for one editable setting in the interactive settings menu."""

    def __init__(
        self,
        key: str,
        label_key: str,
        field_name: str,
        validator: SettingValidator,
        *,
        password: bool = False,
        hint_key: str | None = None,
    ) -> None:
        self.key = key
        self.label_key = label_key
        self.field_name = field_name
        self.validator = validator
        self.password = password
        self.hint_key = hint_key


SETTINGS_OPTIONS = (
    SettingsOption("1", "api_token", "api_token", validate_api_token, password=True),
    SettingsOption("2", "api_url", "api_url", validate_api_url),
    SettingsOption("3", "model_name", "model", validate_model),
    SettingsOption(
        "4",
        "ui_language",
        "ui_language",
        validate_language,
        hint_key="language_options_hint",
    ),
    SettingsOption(
        "5",
        "model_language",
        "model_output_language",
        validate_language,
        hint_key="language_options_hint",
    ),
    SettingsOption("6", "retry_wait", "retry_wait_seconds", validate_positive_int),
    SettingsOption("7", "retry_attempts", "retry_attempts", validate_positive_int),
)


class CommitCraftApp:
    """Main application controller."""

    def __init__(self, repo_path: str) -> None:
        self.config_manager = ConfigManager()
        self.translator = Translator(DEFAULT_LANGUAGE)
        self.ui = TerminalUI(self.translator)
        self.git = GitService(repo_path)
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
                elif choice == "3":
                    self._handle_settings()
                    continue
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
        ok, _output = installer.install(missing)
        if ok:
            return

        self.ui.error(self.ui.translator.text("dependency_failed"))
        for dependency in missing:
            command = f"python -m pip install {dependency.install_spec}"
            self.ui.warning(
                f"{self.ui.translator.text('dependency_manual')}: "
                f"{dependency.package} >= {dependency.version} | {command}"
            )

    def _create_config(self) -> AppConfig:
        """Ask user for first-run config values."""

        api_token = self._ask_validated(
            self.ui.translator.text("api_token"),
            validate_api_token,
            password=True,
        )
        api_url = self._ask_validated(
            f"{self.ui.translator.text('api_url')} ({self.ui.translator.text('leave_default')})",
            validate_api_url,
            default=DEFAULT_API_URL,
        )
        ui_language = self._ask_validated(
            self._prompt_with_hint("ui_language", "language_options_hint"),
            validate_language,
            default=DEFAULT_LANGUAGE,
        )
        ui_language = self._ensure_language_available(str(ui_language))
        self.ui.set_language(Translator(str(ui_language)))
        model_language = self._ask_validated(
            self._prompt_with_hint("model_language", "language_options_hint"),
            validate_language,
            default=DEFAULT_LANGUAGE,
        )
        retry_wait = self._ask_validated(
            self.ui.translator.text("retry_wait"),
            validate_positive_int,
            default=str(DEFAULT_RETRY_WAIT_SECONDS),
        )
        retry_attempts = self._ask_validated(
            self.ui.translator.text("retry_attempts"),
            validate_positive_int,
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

    def _ask_validated(
        self,
        prompt: str,
        validator: SettingValidator,
        *,
        default: str | None = None,
        password: bool = False,
    ) -> object:
        """Ask for input until it passes the supplied validator."""

        while True:
            raw_value = self.ui.ask(prompt, default=default, password=password)
            try:
                return validator(raw_value)
            except ValueError as exc:
                self.ui.error(self.ui.translator.text(str(exc)))

    def _prompt_with_hint(self, label_key: str, hint_key: str) -> str:
        """Build a localized prompt with a localized hint."""

        return f"{self.ui.translator.text(label_key)} ({self.ui.translator.text(hint_key)})"

    def _apply_config_language(self) -> None:
        """Apply configured UI language."""

        if self.config is None:
            return
        self.translator = Translator(self.config.ui_language)
        self.ui.set_language(self.translator)

    def _handle_settings(self) -> None:
        """Show a persistent settings submenu until the user goes back."""

        if self.config is None:
            return

        options = {option.key: option for option in SETTINGS_OPTIONS}
        while True:
            choice = self.ui.settings_menu(self._settings_rows())
            if choice == "0":
                return
            if choice == "9":
                self.ui.info(self.ui.translator.text("settings_cancel_done"))
                continue
            if choice == "8":
                self._reset_settings()
                continue
            option = options.get(choice)
            if option is None:
                self.ui.warning(self.ui.translator.text("invalid_choice"))
                continue
            self._edit_setting(option)

    def _ensure_language_available(self, language: str) -> str:
        """Install optional language support and return a safe language choice."""

        if language != "fa":
            return language

        self.ui.info(self.ui.translator.text("persian_dependency_check"))
        installer = DependencyInstaller()
        missing = installer.missing(PERSIAN_DEPENDENCIES)
        if not missing:
            self.ui.success(self.ui.translator.text("persian_dependency_ready"))
            return language

        self.ui.info(
            f"{self.ui.translator.text('persian_dependency_installing')}: "
            f"{', '.join(dependency.install_spec for dependency in missing)}"
        )
        ok, _output = installer.install(missing)
        if ok:
            self.ui.refresh_persian_support()
            self.ui.success(self.ui.translator.text("persian_dependency_ready"))
            return language

        self.ui.error(self.ui.translator.text("persian_dependency_failed"))
        return "en"

    def _settings_rows(self) -> list[tuple[str, str, str]]:
        """Build display rows for current settings without exposing secrets."""

        if self.config is None:
            return []

        rows: list[tuple[str, str, str]] = []
        for option in SETTINGS_OPTIONS:
            value = getattr(self.config, option.field_name)
            if option.field_name == "api_token":
                value = mask_secret(str(value))
                if value:
                    value = f"{value} ({self.ui.translator.text('sensitive_masked')})"
            rows.append((option.key, self.ui.translator.text(option.label_key), str(value)))
        return rows

    def _edit_setting(self, option: SettingsOption) -> None:
        """Prompt until a valid value is entered or the edit is cancelled."""

        if self.config is None:
            return

        current_value = getattr(self.config, option.field_name)
        default = None if option.password else str(current_value)
        prompt = (
            f"{self.ui.translator.text('settings_enter_new')}: "
            f"{self.ui.translator.text(option.label_key)}"
            f"{self._localized_option_hint(option)} "
            f"({self.ui.translator.text('settings_cancel_hint')})"
        )
        while True:
            raw_value = self.ui.ask(prompt, default=default, password=option.password)
            if raw_value.strip() == "0":
                self.ui.info(self.ui.translator.text("settings_cancel_done"))
                return
            try:
                new_value = option.validator(raw_value)
            except ValueError as exc:
                self.ui.error(self.ui.translator.text(str(exc)))
                continue
            if option.field_name == "ui_language":
                new_value = self._ensure_language_available(str(new_value))
            self._save_config(replace(self.config, **{option.field_name: new_value}))
            self.ui.success(self.ui.translator.text("settings_update_done"))
            return

    def _localized_option_hint(self, option: SettingsOption) -> str:
        """Return a localized setting hint, including its surrounding spacing."""

        if option.hint_key is None:
            return ""
        return f" ({self.ui.translator.text(option.hint_key)})"

    def _reset_settings(self) -> None:
        """Reset settings to application defaults after confirmation."""

        if not self.ui.confirm(self.ui.translator.text("settings_reset_confirm"), default=False):
            return
        self._save_config(default_config())
        self.ui.success(self.ui.translator.text("settings_reset_done"))

    def _save_config(self, config: AppConfig) -> None:
        """Persist config and apply session-visible values immediately."""

        self.config = config
        self.config_manager.save(config)
        self._apply_config_language()

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
        table.add_column(self.ui.t("status_column"), style="cyan")
        table.add_column(self.ui.t("path_column"), style="white")
        for index, file in enumerate(changed_files, start=1):
            table.add_row(str(index), file.status, self.ui.display(file.path))
        self.ui.console.print(table)
        self.ui.info(self.ui.translator.text("selection_help"))
        raw = self.ui.ask(self.ui.translator.text("remove_files_prompt"), default="")
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
            f"{attempt}/{total} "
            f"({self.config.retry_wait_seconds} {self.ui.translator.text('seconds_short')})"
        )

    def _friendly_error(self, exc: Exception) -> str:
        """Translate known error keys."""

        message = str(exc)
        if message in {
            "git_missing",
            "git_not_repo",
            "git_command_failed",
            "ai_empty_message",
            "ai_empty_choices",
            "ai_missing_content",
            "ai_request_failed",
        }:
            return self.ui.translator.text(message)
        if isinstance(exc, GitError):
            return self.ui.translator.text("git_command_failed")
        if isinstance(exc, AIClientError):
            return self.ui.translator.text("ai_request_failed")
        return message
