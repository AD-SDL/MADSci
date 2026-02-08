"""MADSci TUI Application.

Main Textual application for the MADSci terminal user interface.
"""

from typing import ClassVar

from madsci.client.cli.tui.screens.dashboard import DashboardScreen
from madsci.client.cli.tui.screens.logs import LogsScreen
from madsci.client.cli.tui.screens.status import StatusScreen
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header


class MadsciApp(App):
    """MADSci Terminal User Interface Application.

    Provides an interactive terminal interface for managing and
    monitoring MADSci labs.
    """

    TITLE = "MADSci"
    SUB_TITLE = "Self-Driving Laboratory Manager"

    CSS = """
    Screen {
        background: $surface;
    }

    #main-content {
        width: 100%;
        height: 100%;
        padding: 1 2;
    }

    .panel {
        border: solid $primary;
        padding: 1 2;
        margin: 1 0;
    }

    .panel-title {
        text-style: bold;
        color: $primary;
    }

    .status-healthy {
        color: $success;
    }

    .status-unhealthy {
        color: $warning;
    }

    .status-offline {
        color: $error;
    }
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("d", "switch_screen('dashboard')", "Dashboard", show=True),
        Binding("s", "switch_screen('status')", "Status", show=True),
        Binding("l", "switch_screen('logs')", "Logs", show=True),
        Binding("q", "quit", "Quit", show=True),
        Binding("?", "show_help", "Help", show=True),
        Binding("r", "refresh", "Refresh", show=True),
    ]

    SCREENS: ClassVar[dict[str, type[Screen]]] = {
        "dashboard": DashboardScreen,
        "status": StatusScreen,
        "logs": LogsScreen,
    }

    def __init__(self, lab_url: str = "http://localhost:8000/") -> None:
        """Initialize the MADSci TUI application.

        Args:
            lab_url: URL of the Lab Manager.
        """
        super().__init__()
        self.lab_url = lab_url

    def compose(self) -> ComposeResult:
        """Compose the application layout."""
        yield Header()
        yield Footer()

    async def on_mount(self) -> None:
        """Handle application mount event."""
        # Push the dashboard screen as the initial screen
        await self.push_screen("dashboard")

    def action_switch_screen(self, screen: str) -> None:
        """Switch to a named screen.

        Args:
            screen: Name of the screen to switch to.
        """
        self.switch_screen(screen)

    def action_show_help(self) -> None:
        """Show help information."""
        # For now, just notify - can be expanded to a full help screen
        self.notify(
            "Keyboard shortcuts:\n"
            "  d - Dashboard\n"
            "  s - Status\n"
            "  l - Logs\n"
            "  r - Refresh\n"
            "  q - Quit",
            title="Help",
            timeout=10,
        )

    async def action_refresh(self) -> None:
        """Refresh the current screen."""
        screen = self.screen
        if hasattr(screen, "refresh_data"):
            await screen.refresh_data()
            self.notify("Refreshed", timeout=2)
