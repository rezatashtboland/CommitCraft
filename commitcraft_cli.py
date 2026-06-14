"""Command-line entry point for CommitCraft."""

from __future__ import annotations

import sys
from pathlib import Path

from commitcraft.repository_state import (
    GitRepositoryError,
    RepositoryPathStore,
    valid_stored_repository_path,
    validate_repository_path,
)


CLI_MESSAGES = {
    "repository_path_prompt": "Working copy folder path / مسیر پوشه کاری",
    "repository_selected": "Working copy / پوشه کاری",
    "path_not_found": "Path does not exist. / این مسیر وجود ندارد.",
    "path_not_directory": "Path is not a directory. / این مسیر یک پوشه نیست.",
    "repository_path_save_failed": (
        "Could not remember this path for next run. / "
        "امکان ذخیره این مسیر برای اجرای بعدی نبود."
    ),
    "git_not_repo": "This directory is not a Git repository. / این مسیر یک مخزن Git نیست.",
    "git_missing": (
        "Git is not installed or is not available in PATH. / "
        "Git نصب نیست یا در PATH در دسترس نیست."
    ),
    "value_required": "Value cannot be empty. / مقدار نمی‌تواند خالی باشد.",
}


def _bootstrap_dependencies() -> None:
    """Install missing dependencies before importing rich-powered modules."""

    from commitcraft.dependencies import DependencyInstaller

    installer = DependencyInstaller()
    missing = installer.missing()
    if not missing:
        return

    specs = ", ".join(dependency.install_spec for dependency in missing)
    print(f"Checking dependencies: installing {specs}")
    ok, output = installer.install(missing)
    if ok:
        return

    print("Automatic dependency installation failed.", file=sys.stderr)
    if output:
        print(output, file=sys.stderr)
    for dependency in missing:
        print(
            "Install manually: "
            f"{dependency.package} >= {dependency.version} | "
            f"{sys.executable} -m pip install {dependency.install_spec}",
            file=sys.stderr,
        )
    raise SystemExit(1)


def _ask_repository_path() -> Path:
    """Ask for the working-copy path before any other startup work."""

    store = RepositoryPathStore()
    default_path = valid_stored_repository_path(store)
    while True:
        prompt = CLI_MESSAGES["repository_path_prompt"]
        if default_path is not None:
            prompt = f"{prompt} [{default_path}]"
        raw_path = input(f"{prompt}: ").strip()
        if not raw_path and default_path is not None:
            raw_path = str(default_path)

        try:
            repo_path = validate_repository_path(raw_path)
        except ValueError as exc:
            print(CLI_MESSAGES.get(str(exc), str(exc)), file=sys.stderr)
            default_path = None
            continue
        except GitRepositoryError as exc:
            print(CLI_MESSAGES.get(str(exc), str(exc)), file=sys.stderr)
            if str(exc) == "git_missing":
                raise SystemExit(1) from exc
            default_path = None
            continue

        print(f"{CLI_MESSAGES['repository_selected']}: {repo_path}")
        try:
            store.save(repo_path)
        except OSError:
            print(CLI_MESSAGES["repository_path_save_failed"], file=sys.stderr)
        return repo_path


def main() -> None:
    """Start CommitCraft."""

    repo_path = _ask_repository_path()
    _bootstrap_dependencies()
    from commitcraft.app import CommitCraftApp

    CommitCraftApp(str(repo_path)).run()


if __name__ == "__main__":
    main()
