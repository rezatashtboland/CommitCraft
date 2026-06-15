"""Dependency bootstrapper for first-run convenience."""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass

from .subprocess_utils import run_capture


@dataclass(frozen=True)
class Dependency:
    """A Python dependency required by the application."""

    package: str
    import_name: str
    version: str

    @property
    def install_spec(self) -> str:
        """Return pip install spec pinned for reproducible installs."""

        return f"{self.package}>={self.version}"


CORE_DEPENDENCIES = (
    Dependency("requests", "requests", "2.31.0"),
    Dependency("rich", "rich", "13.7.0"),
)

PERSIAN_DEPENDENCIES = (
    Dependency("python-bidi", "bidi", "0.4.2"),
    Dependency("arabic-reshaper", "arabic_reshaper", "3.0.0"),
)


class DependencyInstaller:
    """Check and install missing runtime dependencies."""

    def missing(self, dependencies: tuple[Dependency, ...] = CORE_DEPENDENCIES) -> list[Dependency]:
        """Return dependencies that cannot be imported."""

        return [
            dependency
            for dependency in dependencies
            if importlib.util.find_spec(dependency.import_name) is None
        ]

    def install(self, dependencies: list[Dependency]) -> tuple[bool, str]:
        """Install missing dependencies with pip."""

        if not dependencies:
            return True, ""

        command = [
            sys.executable,
            "-m",
            "pip",
            "install",
            *[dependency.install_spec for dependency in dependencies],
        ]
        result = run_capture(command)
        output = "\n".join(part for part in (result.stdout, result.stderr) if part)
        return result.returncode == 0, output
