"""MADSci TUI Application.

Main Textual application for the MADSci terminal user interface.
"""

from __future__ import annotations

import contextlib
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from madsci.client.cli.tui.constants import AUTO_REFRESH_INTERVAL, get_default_services
from madsci.client.cli.tui.screens.dashboard import DashboardScreen
from madsci.client.cli.tui.screens.logs import LogsScreen
from madsci.client.cli.tui.screens.nodes import NodesScreen
from madsci.client.cli.tui.screens.resources import ResourcesScreen
from madsci.client.cli.tui.screens.status import StatusScreen
from madsci.client.cli.tui.screens.workflows import WorkflowsScreen
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header

if TYPE_CHECKING:
    from madsci.common.types.context_types import MadsciContext


class MadsciApp(App):
    """MADSci Terminal User Interface Application.

    Provides an interactive terminal interface for managing and
    monitoring MADSci labs.
    """

    TITLE = "MADSci"
    SUB_TITLE = "Self-Driving Laboratory Manager"

    CSS_PATH = Path("styles/theme.tcss")

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("d", "switch_screen('dashboard')", "Dashboard", show=True),
        Binding("s", "switch_screen('status')", "Status", show=True),
        Binding("l", "switch_screen('logs')", "Logs", show=True),
        Binding("n", "switch_screen('nodes')", "Nodes", show=True),
        Binding("w", "switch_screen('workflows')", "Workflows", show=True),
        Binding("i", "switch_screen('resources')", "Inventory", show=True),
        Binding("q", "quit", "Quit", show=True),
        Binding("?", "show_help", "Help", show=True),
        Binding("r", "refresh", "Refresh", show=True),
        Binding("ctrl+p", "command_palette", "Commands", show=True),
    ]

    SCREENS: ClassVar[dict[str, type[Screen]]] = {
        "dashboard": DashboardScreen,
        "status": StatusScreen,
        "logs": LogsScreen,
        "nodes": NodesScreen,
        "workflows": WorkflowsScreen,
        "resources": ResourcesScreen,
    }

    def __init__(
        self,
        lab_url: str = "http://localhost:8000/",
        initial_screen: str = "dashboard",
        context: MadsciContext | None = None,
    ) -> None:
        """Initialize the MADSci TUI application.

        Args:
            lab_url: URL of the Lab Manager.
            initial_screen: Name of the screen to show on launch.
            context: Optional MadsciContext for service URLs.
        """
        super().__init__()
        self.lab_url = lab_url
        self._initial_screen = initial_screen
        self.context = context
        self.service_urls = get_default_services(context)

    def compose(self) -> ComposeResult:
        """Compose the application layout."""
        yield Header()
        yield Footer()

    async def on_mount(self) -> None:
        """Handle application mount event."""
        await self.push_screen(self._initial_screen)
        self.set_interval(
            AUTO_REFRESH_INTERVAL,
            self._auto_refresh_active_screen,
            name="app-auto-refresh",
        )

    async def _auto_refresh_active_screen(self) -> None:
        """Auto-refresh the active screen if it supports and enables auto-refresh."""
        screen = self.screen
        if getattr(screen, "auto_refresh_enabled", False) and hasattr(
            screen, "refresh_data"
        ):
            with contextlib.suppress(Exception):
                await screen.refresh_data()

    def action_switch_screen(self, screen: str) -> None:
        """Switch to a named screen.

        Args:
            screen: Name of the screen to switch to.
        """
        self.switch_screen(screen)

    def action_show_help(self) -> None:
        """Show help information."""
        self.notify(
            "Keyboard shortcuts:\n"
            "  d - Dashboard\n"
            "  s - Status\n"
            "  l - Logs\n"
            "  n - Nodes\n"
            "  w - Workflows\n"
            "  i - Inventory (Resources)\n"
            "  r - Refresh\n"
            "  Ctrl+P - Command Palette\n"
            "  q - Quit",
            title="Help",
            timeout=10,
        )

    def action_command_palette(self) -> None:
        """Exit TUI and launch Trogon command palette."""
        self.exit(return_code=2, message="Launching command palette...")

    async def action_refresh(self) -> None:
        """Refresh the current screen."""
        screen = self.screen
        if hasattr(screen, "refresh_data"):
            await screen.refresh_data()
            self.notify("Refreshed", timeout=2)
