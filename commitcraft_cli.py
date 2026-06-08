"""Command-line entry point for CommitCraft."""

from __future__ import annotations

import sys

from commitcraft.dependencies import DependencyInstaller


def _bootstrap_dependencies() -> None:
    """Install missing dependencies before importing rich-powered modules."""

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


def main() -> None:
    """Start CommitCraft."""

    _bootstrap_dependencies()
    from commitcraft.app import CommitCraftApp

    CommitCraftApp().run()


if __name__ == "__main__":
    main()
