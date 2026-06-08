"""Terminal rendering utilities."""

from __future__ import annotations

import re
from typing import Iterable

from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

from .i18n import Translator

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
except ImportError:  # pragma: no cover - bootstrap installs these before normal use.
    arabic_reshaper = None
    get_display = None


RTL_PATTERN = re.compile(r"[\u0600-\u06FF]")


class TerminalUI:
    """Colorful terminal UI with Persian RTL support."""

    def __init__(self, translator: Translator) -> None:
        self.translator = translator
        self.console = Console()

    def set_language(self, translator: Translator) -> None:
        """Change UI language at runtime."""

        self.translator = translator

    def display(self, value: object) -> str:
        """Prepare plain text for terminal display."""

        text = str(value)
        if not self.translator.is_rtl or not text:
            return text
        if RTL_PATTERN.search(text) is None:
            return text
        if arabic_reshaper is None or get_display is None:
            return text
        return get_display(arabic_reshaper.reshape(text))

    def t(self, key: str) -> str:
        """Translate and shape a UI string."""

        return self.display(self.translator.text(key))

    def banner(self) -> None:
        """Render application banner."""

        title = Text(self.display(self.translator.text("app_title")), style="bold cyan")
        subtitle = self.display(self.translator.text("subtitle"))
        panel = Panel(
            Align.center(Text.assemble(title, "\n", Text(subtitle, style="magenta"))),
            border_style="bright_blue",
            padding=(1, 4),
        )
        self.console.print(panel)

    def menu(self) -> str:
        """Render main menu and return selected option."""

        self.banner()
        table = Table(show_header=False, border_style="bright_magenta", box=None)
        table.add_column("key", style="bold yellow", justify="center")
        table.add_column("label", style="bold white")
        table.add_row("1", self.t("menu_commit"))
        table.add_row("2", self.t("menu_push"))
        table.add_row("0", self.t("menu_exit"))
        self.console.print(Panel(table, border_style="green"))
        return Prompt.ask(
            f"[bold cyan]{self.t('menu_prompt')}[/bold cyan]",
            choices=["", "1", "2", "0"],
            default="1",
            show_choices=False,
        )

    def info(self, message: str) -> None:
        """Print informational message."""

        self.console.print(f"[bold cyan]ℹ[/bold cyan] {self.display(message)}")

    def success(self, message: str) -> None:
        """Print success message."""

        self.console.print(f"[bold green]✓[/bold green] {self.display(message)}")

    def warning(self, message: str) -> None:
        """Print warning message."""

        self.console.print(f"[bold yellow]![/bold yellow] {self.display(message)}")

    def error(self, message: str) -> None:
        """Print error message."""

        self.console.print(f"[bold red]✗[/bold red] {self.display(message)}")

    def ask(self, label: str, default: str | None = None, password: bool = False) -> str:
        """Prompt for text input."""

        prompt = self.display(label)
        return Prompt.ask(prompt, default=default, password=password)

    def confirm(self, label: str, default: bool = True) -> bool:
        """Prompt for confirmation."""

        return Confirm.ask(self.display(label), default=default)

    def table(self, title: str, rows: Iterable[tuple[str, str]]) -> None:
        """Render a simple two-column table."""

        table = Table(title=self.display(title), border_style="blue")
        table.add_column("#", style="bold yellow", justify="right")
        table.add_column("Value", style="white")
        for key, value in rows:
            table.add_row(self.display(key), self.display(value))
        self.console.print(table)

    def panel(self, title: str, body: str, style: str = "cyan") -> None:
        """Render a titled panel."""

        self.console.print(
            Panel(
                self.display(body),
                title=self.display(title),
                border_style=style,
            )
        )

    def pause(self) -> None:
        """Wait for user before returning to menu."""

        input(self.t("press_enter"))
