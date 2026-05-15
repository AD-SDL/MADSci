"""StatusBadge widget for MADSci TUI.

Displays a colored status indicator icon with optional text label.
Uses the centralised STATUS_STYLES from formatting utilities to ensure
consistent styling across the TUI.
"""

from __future__ import annotations

from madsci.client.cli.utils.formatting import get_status_style
from textual.reactive import reactive
from textual.widgets import Static


class StatusBadge(Static):
    """Displays a colored status indicator icon with optional text.

    The badge automatically updates when the ``status`` reactive property
    changes. Styling is derived from :func:`get_status_style` which
    provides a consistent ``(icon, colour)`` mapping across the TUI.

    Usage::

        yield StatusBadge("healthy")
        yield StatusBadge("running", show_text=True)
        badge.status = "failed"  # reactive update
    """

    status: reactive[str] = reactive("unknown")
    show_text: reactive[bool] = reactive(True)

    def __init__(
        self,
        status: str = "unknown",
        *,
        show_text: bool = True,
        **kwargs: object,
    ) -> None:
        """Initialize the status badge.

        Args:
            status: Initial status string (e.g. ``"healthy"``, ``"running"``).
            show_text: Whether to display the status text alongside the icon.
            **kwargs: Additional keyword arguments forwarded to ``Static``.
        """
        super().__init__(**kwargs)
        self.show_text = show_text
        self.status = status

    def render(self) -> str:
        """Render the badge as Rich markup.

        Returns:
            Rich-formatted string with coloured icon and optional text.
        """
        icon, colour = get_status_style(self.status)
        if self.show_text:
            return f"[{colour}]{icon} {self.status}[/{colour}]"
        return f"[{colour}]{icon}[/{colour}]"

    def watch_status(self, _value: str) -> None:
        """React to status changes by refreshing the display."""
        self.refresh()

    def watch_show_text(self, _value: bool) -> None:
        """React to show_text changes by refreshing the display."""
        self.refresh()
