"""Application orchestration for CommitCraft."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from rich.table import Table

from .ai_client import AIClient, AIClientError
from .changelog import ChangelogGenerator
from .config import (
    AIProviderConfig,
    DEFAULT_CONVENTIONAL_COMMITS,
    DEFAULT_PULL_STRATEGY,
    DEFAULT_PROVIDER_NAME,
    DEFAULT_RETRY_ATTEMPTS,
    DEFAULT_RETRY_WAIT_SECONDS,
    AppConfig,
    ConfigManager,
    default_config,
    mask_secret,
    validate_api_token,
    validate_api_url,
    validate_bool,
    validate_language,
    validate_model,
    validate_pull_strategy,
    validate_positive_int,
    validate_provider_name,
    validate_provider_type,
    provider_defaults,
)
from .conventional import normalize_commit_message
from .dependencies import Dependency, DependencyInstaller, PERSIAN_DEPENDENCIES
from .git_service import (
    ChangedFile,
    GitAuthError,
    GitConflictError,
    GitError,
    GitRepositoryStateError,
    GitService,
)
from .i18n import DEFAULT_LANGUAGE, Translator
from .repository_state import (
    GitRepositoryError,
    RepositoryPathStore,
    validate_repository_path,
)
from . import __version__
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
    SettingsOption(
        "8",
        "conventional_commits",
        "conventional_commits",
        validate_bool,
        hint_key="bool_options_hint",
    ),
    SettingsOption(
        "9",
        "auto_split_commits",
        "auto_split_commits",
        validate_bool,
        hint_key="bool_options_hint",
    ),
    SettingsOption(
        "10",
        "pull_strategy",
        "pull_strategy",
        validate_pull_strategy,
        hint_key="pull_strategy_hint",
    ),
    SettingsOption(
        "11",
        "auto_stash",
        "auto_stash",
        validate_bool,
        hint_key="bool_options_hint",
    ),
)


class CommitCraftApp:
    """Main application controller."""

    def __init__(self, repo_path: str) -> None:
        self.config_manager = ConfigManager()
        self.repository_store = RepositoryPathStore()
        self.translator = Translator(DEFAULT_LANGUAGE)
        self.ui = TerminalUI(self.translator)
        self.git = GitService(repo_path)
        self.config: AppConfig | None = None

    def run(self) -> None:
        """Run the menu loop until user exits."""

        try:
            self._bootstrap()
            while True:
                choice = self.ui.menu(self._repository_header())
                if choice in {"", "1"}:
                    self._handle_commit()
                elif choice == "2":
                    self._handle_push()
                elif choice == "3":
                    self._handle_fetch()
                elif choice == "4":
                    self._handle_pull()
                elif choice == "5":
                    self._handle_sync()
                elif choice == "6":
                    self._handle_changelog()
                elif choice == "7":
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
        provider_name = DEFAULT_PROVIDER_NAME
        provider_defaults_data = provider_defaults(provider_name)
        api_url = self._ask_validated(
            f"{self.ui.translator.text('api_url')} ({self.ui.translator.text('leave_default')})",
            validate_api_url,
            default=provider_defaults_data["api_url"],
        )
        model = self._ask_validated(
            self.ui.translator.text("model_name"),
            validate_model,
            default=provider_defaults_data["model"],
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
        conventional_commits = self._ask_validated(
            self._prompt_with_hint("conventional_commits", "bool_options_hint"),
            validate_bool,
            default=self.ui.translator.text("yes" if DEFAULT_CONVENTIONAL_COMMITS else "no"),
        )
        pull_strategy = self._choose_pull_strategy(default=DEFAULT_PULL_STRATEGY)
        auto_stash = self._ask_validated(
            self._prompt_with_hint("auto_stash", "bool_options_hint"),
            validate_bool,
            default=self.ui.translator.text("yes"),
        )
        auto_split_commits = self._ask_validated(
            self._prompt_with_hint("auto_split_commits", "bool_options_hint"),
            validate_bool,
            default=self.ui.translator.text("no"),
        )
        return AppConfig.from_dict(
            {
                "providers": {
                    provider_name: {
                        "name": provider_name,
                        "provider_type": provider_defaults_data["provider_type"],
                        "api_token": api_token,
                        "api_url": api_url,
                        "model": model,
                    }
                },
                "active_provider": provider_name,
                "ui_language": ui_language,
                "model_output_language": model_language,
                "retry_wait_seconds": retry_wait,
                "retry_attempts": retry_attempts,
                "conventional_commits": conventional_commits,
                "pull_strategy": pull_strategy,
                "auto_stash": auto_stash,
                "auto_split_commits": auto_split_commits,
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

    def _choose_pull_strategy(self, default: str) -> str:
        """Ask for a pull strategy from a localized numbered list."""

        rows = [
            ("1", self.ui.translator.text("pull_strategy_merge")),
            ("2", self.ui.translator.text("pull_strategy_rebase")),
        ]
        default_choice = "2" if default == "rebase" else "1"
        while True:
            raw_value = self.ui.choose_from_rows(
                self.ui.translator.text("pull_strategy_options"),
                rows,
                self._prompt_with_hint("pull_strategy_choice", "pull_strategy_hint"),
                default=default_choice,
            )
            try:
                return validate_pull_strategy(raw_value)
            except ValueError as exc:
                self.ui.error(self.ui.translator.text(str(exc)))

    def _apply_config_language(self) -> None:
        """Apply configured UI language."""

        if self.config is None:
            return
        language = self.config.ui_language
        if language == "fa" and self._missing_persian_dependencies():
            language = DEFAULT_LANGUAGE
        self.translator = Translator(language)
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
            if choice == "13":
                self.ui.info(self.ui.translator.text("settings_cancel_done"))
                continue
            if choice == "12":
                self._reset_settings()
                continue
            if choice == "1":
                self._add_or_update_provider()
                continue
            if choice == "2":
                self._switch_provider()
                continue
            if choice == "14":
                self._change_working_copy()
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

        self._set_session_language("fa")
        self.ui.info(self.ui.translator.text("persian_dependency_check"))
        installer = DependencyInstaller()
        missing = self._missing_persian_dependencies(installer)
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
        self._set_session_language(DEFAULT_LANGUAGE)
        return "en"

    def _set_session_language(self, language: str) -> None:
        """Apply a UI language for the current session without persisting config."""

        self.translator = Translator(language)
        self.ui.set_language(self.translator)

    def _missing_persian_dependencies(
        self,
        installer: DependencyInstaller | None = None,
    ) -> list[Dependency]:
        """Return missing Persian-only display dependencies without installing them."""

        return (installer or DependencyInstaller()).missing(PERSIAN_DEPENDENCIES)

    def _settings_rows(self) -> list[tuple[str, str, str]]:
        """Build display rows for current settings without exposing secrets."""

        if self.config is None:
            return []

        rows: list[tuple[str, str, str]] = []
        rows.append(
            (
                "1",
                self.ui.translator.text("provider_add_update"),
                self._provider_summary(self.config.active_ai_provider()),
            )
        )
        rows.append(
            (
                "2",
                self.ui.translator.text("active_provider"),
                self.config.active_provider,
            )
        )
        for option in SETTINGS_OPTIONS:
            if option.field_name == "model":
                value = self.config.active_ai_provider().model
            else:
                value = getattr(self.config, option.field_name)
            if isinstance(value, bool):
                value = self.ui.translator.text("yes" if value else "no")
            if option.field_name == "pull_strategy":
                value = self.ui.translator.text(f"pull_strategy_{value}")
            rows.append((option.key, self.ui.translator.text(option.label_key), str(value)))
        rows.append(("14", self.ui.translator.text("working_copy"), self._repository_header()))
        return rows

    def _provider_summary(self, provider: AIProviderConfig) -> str:
        """Return a masked one-line summary for a provider profile."""

        token = mask_secret(provider.api_token)
        if token:
            token = f"{token} ({self.ui.translator.text('sensitive_masked')})"
        return (
            f"{provider.name} | {provider.provider_type} | "
            f"{provider.model} | {provider.api_url} | {token}"
        )

    def _add_or_update_provider(self) -> None:
        """Create or update a provider profile from settings."""

        if self.config is None:
            return

        raw_name = self.ui.ask(
            self.ui.translator.text("provider_name"),
            default=self.config.active_provider,
        )
        try:
            name = validate_provider_name(raw_name)
        except ValueError as exc:
            self.ui.error(self.ui.translator.text(str(exc)))
            return

        existing = self.config.providers.get(name)
        defaults = provider_defaults(name)
        provider_type = self._ask_validated(
            self._prompt_with_hint("provider_type", "provider_type_hint"),
            validate_provider_type,
            default=existing.provider_type if existing else defaults["provider_type"],
        )
        api_token = self._ask_validated(
            self.ui.translator.text("api_token"),
            validate_api_token,
            default=None,
            password=True,
        )
        api_url = self._ask_validated(
            self.ui.translator.text("api_url"),
            validate_api_url,
            default=existing.api_url if existing else defaults["api_url"],
        )
        model = self._ask_validated(
            self.ui.translator.text("model_name"),
            validate_model,
            default=existing.model if existing else defaults["model"],
        )
        provider = AIProviderConfig(
            name=name,
            provider_type=str(provider_type),
            api_token=str(api_token),
            api_url=str(api_url),
            model=str(model),
        )
        providers = dict(self.config.providers)
        providers[name] = provider
        self._save_config(
            replace(
                self.config,
                providers=providers,
                active_provider=name,
            )
        )
        self.ui.success(self.ui.translator.text("provider_saved"))

    def _switch_provider(self) -> None:
        """Switch the active provider to one of the configured profiles."""

        if self.config is None:
            return
        rows = []
        for index, (name, provider) in enumerate(self.config.providers.items(), start=1):
            marker = ""
            if name == self.config.active_provider:
                marker = self.ui.translator.text("active_marker")
            rows.append((str(index), f"{provider.name} {marker}".strip()))
        self.ui.table(self.ui.translator.text("configured_providers"), rows)
        raw_choice = self.ui.ask(self.ui.translator.text("provider_switch_prompt"), default="1")
        indexes = self._parse_indexes(raw_choice, len(rows))
        if not indexes:
            self.ui.warning(self.ui.translator.text("invalid_choice"))
            return
        selected_index = min(indexes)
        selected_name = list(self.config.providers.keys())[selected_index - 1]
        self._save_config(replace(self.config, active_provider=selected_name))
        self.ui.success(self.ui.translator.text("provider_switched"))

    def _save_active_provider(self, provider: AIProviderConfig) -> None:
        """Persist changes to the active provider profile."""

        if self.config is None:
            return
        providers = dict(self.config.providers)
        providers[provider.name] = provider
        self._save_config(replace(self.config, providers=providers))

    def _change_working_copy(self) -> None:
        """Change the active repository path after validation."""

        raw_path = self.ui.ask(
            self.ui.translator.text("repository_path_prompt"),
            default=str(self._repository_path()),
        )
        try:
            repo_path = validate_repository_path(raw_path)
        except (ValueError, GitRepositoryError) as exc:
            self.ui.error(self.ui.translator.text(str(exc)))
            return
        self.git = GitService(str(repo_path))
        self.git.ensure_available()
        try:
            self.repository_store.save(repo_path)
        except OSError:
            self.ui.warning(self.ui.translator.text("repository_path_save_failed"))
        self.ui.success(f"{self.ui.translator.text('repository_selected')}: {repo_path}")

    def _edit_setting(self, option: SettingsOption) -> None:
        """Prompt until a valid value is entered or the edit is cancelled."""

        if self.config is None:
            return

        current_value = (
            self.config.active_ai_provider().model
            if option.field_name == "model"
            else getattr(self.config, option.field_name)
        )
        default = None if option.password else str(current_value)
        prompt = (
            f"{self.ui.translator.text('settings_enter_new')}: "
            f"{self.ui.translator.text(option.label_key)}"
            f"{self._localized_option_hint(option)} "
            f"({self.ui.translator.text('settings_cancel_hint')})"
        )
        if option.field_name == "pull_strategy":
            new_value = self._choose_pull_strategy(default=str(current_value))
            self._save_config(replace(self.config, pull_strategy=new_value))
            self.ui.success(self.ui.translator.text("settings_update_done"))
            return
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
            if option.field_name == "model":
                self._save_active_provider(
                    replace(self.config.active_ai_provider(), model=str(new_value))
                )
            else:
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
            for commit_files in self._commit_file_groups(selected):
                self._commit_selected_files(commit_files)
        except (GitError, AIClientError) as exc:
            self.ui.error(self._friendly_error(exc))

    def _commit_selected_files(self, selected: list[str]) -> None:
        """Generate, review, and commit one selected file group."""

        if self.config is None:
            return
        self.git.add(selected)
        try:
            diff = self.git.staged_diff_for_files(selected)
            if not diff.strip():
                diff = "\n".join(selected)

            self.ui.info(self.ui.translator.text("generating"))
            ai_response = AIClient(self.config).generate_commit_message(
                diff,
                conventional=self.config.conventional_commits,
                on_retry=self._show_ai_retry,
            )
            message = self._review_commit_message(ai_response.message)
        except AIClientError:
            raise
        if message is None:
            return

        self.ui.info(self.ui.translator.text("committing"))
        self.git.add(selected)
        self.git.commit(message, selected)
        self.ui.success(self.ui.translator.text("commit_done"))

    def _review_commit_message(self, generated_message: str) -> str | None:
        """Let the user inspect, edit, and approve a commit message."""

        if self.config is None:
            return None
        message = normalize_commit_message(generated_message)
        while True:
            self.ui.panel(self.ui.translator.text("commit_message"), message, style="bright_green")
            edited = self.ui.ask_multiline(
                self.ui.translator.text("edit_commit_message"),
                default=message,
            )
            if edited.strip():
                message = normalize_commit_message(edited)
            if self.ui.confirm(self.ui.translator.text("confirm_commit"), default=True):
                return message
            return None

    def _commit_file_groups(
        self,
        selected: list[str],
    ) -> list[list[str]]:
        """Use AI to optionally split selected paths into independent commit groups."""

        if self.config is None or len(selected) <= 1 or not self.config.auto_split_commits:
            return [selected]

        diff = self.git.diff_for_files(selected)
        if not diff.strip():
            diff = "\n".join(selected)
        self.ui.info(self.ui.translator.text("analyzing_splits"))
        plan = AIClient(self.config).split_commit_groups(
            selected,
            diff,
            on_retry=self._show_ai_retry,
        )
        if len(plan.groups) <= 1:
            self.ui.info(self.ui.translator.text("split_single_group"))
            return [selected]

        rows = [
            (
                str(index),
                f"{group.title}: {', '.join(group.files)}",
            )
            for index, group in enumerate(plan.groups, start=1)
        ]
        self.ui.table(
            f"{self.ui.translator.text('split_groups_identified')}: {len(plan.groups)}",
            rows,
        )
        if not self.ui.confirm(self.ui.translator.text("split_confirm"), default=True):
            return [selected]
        return [group.files for group in plan.groups]

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

    def _repository_path(self) -> Path:
        """Return the active repository root, falling back to the configured path."""

        try:
            return self.git.repository_path()
        except GitError:
            return Path(self.git.repo_path).resolve()

    def _repository_header(self) -> str:
        """Return a header with repository folder name and full path."""

        repo_path = self._repository_path()
        return f"{repo_path.name} | {repo_path}"

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

    def _handle_fetch(self) -> None:
        """Fetch current repository remotes with retryable network handling."""

        if self.config is None:
            return
        try:
            self._show_branch_and_confirm("fetch_confirm")
            self.ui.info(self.ui.translator.text("fetching"))
            result = self.git.fetch(
                attempts=self.config.retry_attempts,
                wait_seconds=self.config.retry_wait_seconds,
                on_retry=self._show_git_retry,
            )
            self._show_git_output(result.output)
            self.ui.success(self.ui.translator.text("fetch_done"))
        except GitError as exc:
            self.ui.error(self._friendly_error(exc))

    def _handle_pull(self) -> None:
        """Pull current branch using configured integration settings."""

        if self.config is None:
            return
        self._handle_integration_operation("pull")

    def _handle_sync(self) -> None:
        """Pull current branch and push it after a successful integration."""

        if self.config is None:
            return
        self._handle_integration_operation("sync")

    def _handle_changelog(self) -> None:
        """Generate or continue CHANGELOG.md from new Git commits."""

        try:
            self.ui.info(self.ui.translator.text("changelog_generating"))
            result = ChangelogGenerator(self.git, __version__).update()
            if result.added_count == 0:
                self.ui.warning(self.ui.translator.text("changelog_no_new_commits"))
                return
            self.ui.success(
                f"{self.ui.translator.text('changelog_done')}: "
                f"{result.added_count} "
                f"{self.ui.translator.text('changelog_entries')} | {result.path}"
            )
        except (OSError, GitError) as exc:
            self.ui.error(self._friendly_error(exc))

    def _handle_integration_operation(self, operation: str) -> None:
        """Run a pull-like operation with localized reporting and conflict guidance."""

        if self.config is None:
            return
        try:
            self.git.ensure_pull_ready()
            self._show_branch_and_confirm(f"{operation}_confirm")
            self.ui.info(self._strategy_summary())
            self.ui.info(self.ui.translator.text(f"{operation}ing"))
            if operation == "pull":
                result = self.git.pull(
                    self.config.pull_strategy,
                    auto_stash=self.config.auto_stash,
                    attempts=self.config.retry_attempts,
                    wait_seconds=self.config.retry_wait_seconds,
                    on_retry=self._show_git_retry,
                )
            else:
                result = self.git.sync(
                    self.config.pull_strategy,
                    auto_stash=self.config.auto_stash,
                    attempts=self.config.retry_attempts,
                    wait_seconds=self.config.retry_wait_seconds,
                    on_retry=self._show_git_retry,
                )
            self._show_git_output(result.output)
            self.ui.success(self.ui.translator.text(f"{operation}_done"))
        except GitConflictError as exc:
            self._report_conflict(exc)
        except GitError as exc:
            self.ui.error(self._friendly_error(exc))

    def _show_branch_and_confirm(self, confirm_key: str) -> None:
        """Show the current branch and stop the operation when user declines."""

        branch = self.git.current_branch()
        self.ui.info(f"{self.ui.translator.text('current_branch')}: {branch}")
        if not self.ui.confirm(self.ui.translator.text(confirm_key), default=True):
            raise GitError("operation_cancelled")

    def _strategy_summary(self) -> str:
        """Return a localized summary of pull strategy and auto-stash settings."""

        if self.config is None:
            return ""
        strategy = self.ui.translator.text(f"pull_strategy_{self.config.pull_strategy}")
        auto_stash = self.ui.translator.text("yes" if self.config.auto_stash else "no")
        return (
            f"{self.ui.translator.text('pull_strategy')}: {strategy} | "
            f"{self.ui.translator.text('auto_stash')}: {auto_stash}"
        )

    def _show_git_output(self, output: str) -> None:
        """Show Git output when available without hiding important diagnostics."""

        if output.strip():
            self.ui.panel(self.ui.translator.text("git_output"), output.strip(), style="cyan")

    def _report_conflict(self, exc: GitConflictError) -> None:
        """Show conflict details and explicit recovery guidance."""

        message = self._friendly_error(exc)
        self.ui.error(message)
        if str(exc).strip() and str(exc) not in {"git_conflict", "git_stash_conflict"}:
            self.ui.panel(self.ui.translator.text("git_output"), str(exc).strip(), style="red")
        guidance_key = "rebase_conflict_guidance" if self.git.in_rebase() else "merge_conflict_guidance"
        if str(exc) == "git_stash_conflict":
            guidance_key = "stash_conflict_guidance"
        self.ui.warning(self.ui.translator.text(guidance_key))

    def _show_git_retry(self, attempt: int, total: int, exc: Exception) -> None:
        """Show retry progress for retryable Git network failures."""

        if self.config is None:
            return
        self.ui.warning(
            f"{self.ui.translator.text('git_retry')} "
            f"{attempt}/{total} "
            f"({self.config.retry_wait_seconds} {self.ui.translator.text('seconds_short')})"
        )

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
            "git_conflict",
            "git_stash_conflict",
            "git_auth_failed",
            "git_no_commits",
            "git_no_upstream",
            "operation_cancelled",
            "ai_empty_message",
            "ai_empty_choices",
            "ai_missing_content",
            "ai_request_failed",
            "ai_split_parse_failed",
        }:
            return self.ui.translator.text(message)
        if isinstance(exc, GitConflictError):
            return self.ui.translator.text("git_conflict")
        if isinstance(exc, GitAuthError):
            return self.ui.translator.text("git_auth_failed")
        if isinstance(exc, GitRepositoryStateError):
            return self.ui.translator.text(str(exc))
        if isinstance(exc, GitError):
            return self.ui.translator.text("git_command_failed")
        if isinstance(exc, AIClientError):
            return self.ui.translator.text("ai_request_failed")
        return message
