"""Command-line entry point for CommitCraft."""

from __future__ import annotations

import sys
from pathlib import Path

from commitcraft.config import ConfigManager
from commitcraft.i18n import DEFAULT_LANGUAGE, Translator
from commitcraft.repository_state import (
    GitRepositoryError,
    RepositoryPathStore,
    valid_stored_repository_path,
    validate_repository_path,
)


def _startup_translator() -> Translator:
    """Return the configured UI translator before the rich-powered app starts."""

    manager = ConfigManager()
    if not manager.exists():
        return Translator(DEFAULT_LANGUAGE)
    try:
        return Translator(manager.load().ui_language)
    except (OSError, ValueError):
        return Translator(DEFAULT_LANGUAGE)


def _bootstrap_dependencies() -> None:
    """Install missing dependencies before importing rich-powered modules."""

    from commitcraft.dependencies import DependencyInstaller

    translator = _startup_translator()
    installer = DependencyInstaller()
    missing = installer.missing()
    if not missing:
        return

    specs = ", ".join(dependency.install_spec for dependency in missing)
    print(f"{translator.text('dependency_installing')}: {specs}")
    ok, _output = installer.install(missing)
    if ok:
        return

    print(translator.text("dependency_failed"), file=sys.stderr)
    for dependency in missing:
        print(
            f"{translator.text('dependency_manual')}: "
            f"{dependency.package} >= {dependency.version} | "
            f"{sys.executable} -m pip install {dependency.install_spec}",
            file=sys.stderr,
        )
    raise SystemExit(1)


def _ask_repository_path() -> Path:
    """Ask for the working-copy path before any other startup work."""

    translator = _startup_translator()
    store = RepositoryPathStore()
    default_path = valid_stored_repository_path(store)
    while True:
        prompt = translator.text("repository_path_prompt")
        if default_path is not None:
            prompt = f"{prompt} [{default_path}]"
        raw_path = input(f"{prompt}: ").strip()
        if not raw_path and default_path is not None:
            raw_path = str(default_path)

        try:
            repo_path = validate_repository_path(raw_path)
        except ValueError as exc:
            print(translator.text(str(exc)), file=sys.stderr)
            default_path = None
            continue
        except GitRepositoryError as exc:
            print(translator.text(str(exc)), file=sys.stderr)
            if str(exc) == "git_missing":
                raise SystemExit(1) from exc
            default_path = None
            continue

        print(f"{translator.text('repository_selected')}: {repo_path}")
        try:
            store.save(repo_path)
        except OSError:
            print(translator.text("repository_path_save_failed"), file=sys.stderr)
        return repo_path


def main() -> None:
    """Start CommitCraft."""

    repo_path = _ask_repository_path()
    _bootstrap_dependencies()
    from commitcraft.app import CommitCraftApp

    CommitCraftApp(str(repo_path)).run()


if __name__ == "__main__":
    main()
