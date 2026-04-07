"""Screen mixins for MADSci TUI.

Provides reusable behaviours that can be mixed into any
:class:`~textual.screen.Screen` subclass.
"""

from __future__ import annotations

import contextlib
from collections.abc import Generator
from typing import ClassVar

import httpx
from madsci.client.cli.tui.constants import AUTO_REFRESH_INTERVAL, DEFAULT_SERVICES
from textual.reactive import reactive
from textual.widgets import DataTable


@contextlib.contextmanager
def preserve_cursor(table: DataTable) -> Generator[None, None, None]:
    """Context manager that preserves cursor position across a table refresh.

    Saves the current cursor row before the block executes, and
    restores it (clamped to the new row count) afterwards.

    Usage::

        with preserve_cursor(table):
            table.clear()
            for row in new_data:
                table.add_row(...)
    """
    saved_row = table.cursor_row if table.row_count > 0 else 0
    yield
    if table.row_count > 0 and saved_row >= 0:
        restored = min(saved_row, table.row_count - 1)
        table.move_cursor(row=restored)


class AutoRefreshMixin:
    """Adds auto-refresh toggle capability to any Screen.

    The consuming screen must implement a ``refresh_data()`` async method.
    The mixin provides the reactive ``auto_refresh_enabled`` flag and the
    ``action_toggle_auto_refresh()`` action that can be bound to a key.

    Usage::

        class MyScreen(AutoRefreshMixin, Screen):
            BINDINGS = [("a", "toggle_auto_refresh", "Auto-refresh")]
            refresh_interval = 5.0

            async def refresh_data(self) -> None:
                # Fetch and display data
                ...
    """

    auto_refresh_enabled: reactive[bool] = reactive(True)
    refresh_interval: float = AUTO_REFRESH_INTERVAL

    async def refresh_data(self) -> None:
        """Override to define the refresh behaviour.

        This method is called automatically by the application's
        auto-refresh timer (see ``MadsciApp``). Subclasses should
        fetch and update their data here.
        """

    def action_toggle_auto_refresh(self) -> None:
        """Toggle the auto-refresh flag and notify the user."""
        self.auto_refresh_enabled = not self.auto_refresh_enabled
        state = "enabled" if self.auto_refresh_enabled else "disabled"
        if hasattr(self, "notify"):
            self.notify(f"Auto-refresh {state}", timeout=2)

    async def on_unmount(self) -> None:
        """Clean up when screen is unmounted."""
        if hasattr(self, "close_async_clients"):
            await self.close_async_clients()


class ServiceURLMixin:
    """Provides service URL resolution from the application context.

    Looks up service URLs from ``self.app.service_urls`` (set by
    :class:`MadsciApp`) and falls back to hardcoded defaults from
    :data:`DEFAULT_SERVICES`.

    Usage::

        class MyScreen(ServiceURLMixin, Screen):
            async def fetch_data(self):
                url = self.get_service_url("event_manager")
                ...
    """

    _async_clients: ClassVar[dict[str, httpx.AsyncClient]] = {}

    def get_service_url(self, service_name: str) -> str:
        """Get the URL for a named service.

        Resolution order:
        1. ``self.app.service_urls`` (runtime configuration)
        2. :data:`DEFAULT_SERVICES` (compile-time defaults)

        Args:
            service_name: Service key, e.g. ``"event_manager"``.

        Returns:
            Base URL string for the service.
        """
        try:
            return self.app.service_urls.get(
                service_name,
                DEFAULT_SERVICES.get(service_name, "http://localhost:8000/"),
            )
        except Exception:
            return DEFAULT_SERVICES.get(service_name, "http://localhost:8000/")

    def get_async_client(self, service_url: str) -> httpx.AsyncClient:
        """Get or create a cached async HTTP client for a service URL."""
        if service_url not in self._async_clients:
            self._async_clients[service_url] = httpx.AsyncClient(timeout=5.0)
        return self._async_clients[service_url]

    async def close_async_clients(self) -> None:
        """Close all cached async clients."""
        for client in self._async_clients.values():
            await client.aclose()
        self._async_clients.clear()
