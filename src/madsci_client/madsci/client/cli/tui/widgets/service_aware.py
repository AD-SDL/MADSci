"""ServiceAwareContainer widget for MADSci TUI.

Container that gates children behind a service health check. Shows
children when the service is available, and an "unavailable" panel
with a retry button when it is not.

.. note:: Not yet used by any screen -- designed for future adoption.
   See https://github.com/AD-SDL/MADSci/issues/278
"""

from __future__ import annotations

from typing import Any

from madsci.client.cli.utils.service_health import check_service_health_async
from textual.app import ComposeResult
from textual.containers import Container
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button, Label, Static


class ServiceAwareContainer(Widget):
    """Container that gates children behind a service health check.

    Shows children when the service is available. Shows an "unavailable"
    panel with a retry button when the service is unreachable.
    Uses :func:`check_service_health_async` for health checking.

    Posts :class:`ServiceAvailable` and :class:`ServiceUnavailable`
    messages when the service state changes.

    Usage::

        yield ServiceAwareContainer(
            service_url="http://localhost:8001/",
            service_name="Event Manager",
        )
    """

    is_available: reactive[bool] = reactive(False)

    class ServiceAvailable(Message):
        """Posted when the service becomes available."""

        def __init__(self, service_name: str, service_url: str) -> None:
            """Initialize with service name and URL."""
            self.service_name = service_name
            self.service_url = service_url
            super().__init__()

    class ServiceUnavailable(Message):
        """Posted when the service becomes unavailable."""

        def __init__(
            self, service_name: str, service_url: str, error: str | None = None
        ) -> None:
            """Initialize with service name, URL, and optional error."""
            self.service_name = service_name
            self.service_url = service_url
            self.error = error
            super().__init__()

    DEFAULT_CSS = """
    ServiceAwareContainer {
        height: auto;
    }
    ServiceAwareContainer .service-unavailable {
        height: auto;
        padding: 1 2;
        text-align: center;
    }
    ServiceAwareContainer .service-content {
        height: auto;
    }
    """

    def __init__(
        self,
        service_url: str,
        service_name: str,
        *,
        check_interval: float = 5.0,
        **kwargs: Any,
    ) -> None:
        """Initialize the container.

        Args:
            service_url: Base URL of the service to check.
            service_name: Human-readable service name for display.
            check_interval: Interval in seconds between health checks.
            **kwargs: Additional keyword arguments forwarded to ``Widget``.
        """
        super().__init__(**kwargs)
        self._service_url = service_url
        self._service_name = service_name
        self._check_interval = check_interval
        self._last_error: str | None = None

    async def check_health(self) -> bool:
        """Perform a health check against the service.

        Returns:
            ``True`` if the service is available, ``False`` otherwise.
        """
        result = await check_service_health_async(
            name=self._service_name,
            url=self._service_url,
        )
        self._last_error = result.error
        self.is_available = result.is_available
        return result.is_available

    def compose(self) -> ComposeResult:
        """Compose the container layout."""
        with Container(classes="service-unavailable") as unavailable:
            unavailable.id = "service-unavailable-panel"
            yield Label(
                f"[bold red]Service Unavailable[/bold red]\n\n"
                f"[dim]{self._service_name} at {self._service_url} "
                f"is not reachable.[/dim]",
                id="service-unavailable-label",
            )
            yield Button("Retry", id="service-retry-btn", variant="primary")
        with Container(classes="service-content") as content:
            content.id = "service-content-panel"
            content.display = False
            yield Static("", id="service-content-placeholder")

    async def on_mount(self) -> None:
        """Start periodic health checks on mount."""
        await self.check_health()
        self.set_interval(self._check_interval, self.check_health)

    def watch_is_available(self, value: bool) -> None:
        """React to availability changes by toggling panels."""
        try:
            unavailable = self.query_one("#service-unavailable-panel")
            content = self.query_one("#service-content-panel")
        except Exception:
            return

        if value:
            unavailable.display = False
            content.display = True
            self.post_message(
                self.ServiceAvailable(self._service_name, self._service_url)
            )
        else:
            unavailable.display = True
            content.display = False
            # Update the label with the latest error
            try:
                label = self.query_one("#service-unavailable-label", Label)
                error_text = (
                    f"\n[red]{self._last_error}[/red]" if self._last_error else ""
                )
                label.update(
                    f"[bold red]Service Unavailable[/bold red]\n\n"
                    f"[dim]{self._service_name} at {self._service_url} "
                    f"is not reachable.[/dim]{error_text}"
                )
            except Exception:  # noqa: S110
                pass  # Label may not be mounted yet
            self.post_message(
                self.ServiceUnavailable(
                    self._service_name, self._service_url, self._last_error
                )
            )

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle retry button press."""
        if event.button.id == "service-retry-btn":
            await self.check_health()
