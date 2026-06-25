"""DetailPanel widget for MADSci TUI.

Key-value detail display with titled sections. Replaces the duplicated
ServiceDetailPanel, WorkflowDetailPanel, and node detail rendering patterns
found across the existing TUI screens.
"""

from __future__ import annotations

from typing import NamedTuple

from textual.app import ComposeResult
from textual.widgets import Label, Static


class DetailSection(NamedTuple):
    """A titled section containing key-value pairs.

    Attributes:
        title: Section heading text.
        fields: Mapping of field labels to their formatted display values.
            Values may contain Rich markup for coloured output.
    """

    title: str
    fields: dict[str, str]


class DetailPanel(Static):
    """Key-value detail display with titled sections.

    Provides a standard pattern for detail panels throughout the TUI:
    a title, followed by one or more sections each containing indented
    key-value pairs.

    Usage::

        panel = DetailPanel()
        panel.update_content(
            title="Node: robot_arm",
            sections=[
                DetailSection("General", {
                    "URL": "http://localhost:2000/",
                    "Status": "[green]connected[/green]",
                }),
                DetailSection("Actions", {
                    "pick": "Pick up an item",
                    "place": "Place an item",
                }),
            ],
        )
        panel.clear_content()
    """

    DEFAULT_CSS = """
    DetailPanel {
        height: auto;
        min-height: 4;
    }
    """

    def __init__(
        self,
        *,
        placeholder: str = "Select an item to view details",
        **kwargs: object,
    ) -> None:
        """Initialize the detail panel.

        Args:
            placeholder: Text shown when no content has been set.
            **kwargs: Additional keyword arguments forwarded to ``Static``.
        """
        super().__init__(**kwargs)
        self._placeholder = placeholder

    def compose(self) -> ComposeResult:
        """Compose the panel with a content label."""
        yield Label(
            f"[dim]{self._placeholder}[/dim]",
            id="detail-panel-content",
        )

    def update_content(
        self,
        title: str,
        sections: list[DetailSection],
    ) -> None:
        """Update the panel with new content.

        Args:
            title: Main title displayed at the top of the panel.
            sections: List of sections to display below the title.
        """
        lines: list[str] = [f"[bold]{title}[/bold]"]

        for section in sections:
            lines.append("")
            lines.append(f"  [bold]{section.title}[/bold]")
            if section.fields:
                # Calculate max key length for alignment
                max_key_len = max(len(k) for k in section.fields)
                for key, value in section.fields.items():
                    lines.append(f"    {key:<{max_key_len}}  {value}")
            else:
                lines.append("    [dim]No data[/dim]")

        content = self.query_one("#detail-panel-content", Label)
        content.update("\n".join(lines))

    def clear_content(self) -> None:
        """Reset the panel to its placeholder state."""
        content = self.query_one("#detail-panel-content", Label)
        content.update(f"[dim]{self._placeholder}[/dim]")
