"""Terminal rendering utilities."""

from __future__ import annotations

import re
from typing import Iterable

from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
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

    def refresh_persian_support(self) -> None:
        """Load Persian display helpers after an on-demand installation."""

        global arabic_reshaper, get_display
        if arabic_reshaper is not None and get_display is not None:
            return
        try:
            import arabic_reshaper as reshaper
            from bidi.algorithm import get_display as bidi_get_display
        except ImportError:
            return
        arabic_reshaper = reshaper
        get_display = bidi_get_display

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
        table.add_row("3", self.t("menu_settings"))
        table.add_row("0", self.t("menu_exit"))
        self.console.print(Panel(table, border_style="green"))
        return Prompt.ask(
            f"[bold cyan]{self.t('menu_prompt')}[/bold cyan]",
            default="1",
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

    def ask_multiline(self, label: str, default: str) -> str:
        """Prompt for a possibly multi-line value terminated by an empty line."""

        self.info(label)
        self.console.print(self.display(default))
        lines: list[str] = []
        while True:
            line = input()
            if line == "":
                break
            lines.append(line)
        return "\n".join(lines) if lines else default

    def confirm(self, label: str, default: bool = True) -> bool:
        """Prompt for confirmation."""

        yes = self.translator.text("yes")
        no = self.translator.text("no")
        default_choice = yes if default else no
        while True:
            answer = Prompt.ask(self.display(label), default=default_choice)
            normalized = answer.strip().lower()
            if normalized == yes.lower():
                return True
            if normalized == no.lower():
                return False
            self.warning(self.translator.text("invalid_choice"))

    def table(self, title: str, rows: Iterable[tuple[str, str]]) -> None:
        """Render a simple two-column table."""

        table = Table(title=self.display(title), border_style="blue")
        table.add_column("#", style="bold yellow", justify="right")
        table.add_column(self.t("settings_value_column"), style="white")
        for key, value in rows:
            table.add_row(self.display(key), self.display(value))
        self.console.print(table)

    def settings_menu(self, rows: Iterable[tuple[str, str, str]]) -> str:
        """Render the persistent settings submenu and return selected option."""

        table = Table(
            title=self.t("settings_title"),
            border_style="bright_blue",
            show_lines=True,
        )
        table.add_column("#", style="bold yellow", justify="center")
        table.add_column(self.t("settings_column"), style="bold cyan")
        table.add_column(self.t("settings_value_column"), style="white")
        for key, label, value in rows:
            table.add_row(key, self.display(label), self.display(value))
        table.add_row("9", self.t("settings_reset"), "")
        table.add_row("10", self.t("settings_cancel"), "")
        table.add_row("0", self.t("settings_back"), "")
        self.console.print(Panel(table, border_style="green"))
        return Prompt.ask(
            f"[bold cyan]{self.t('settings_prompt')}[/bold cyan]",
        )

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
