"""FilterBar widget for MADSci TUI.

Search input with optional dropdown filters. Emits :class:`FilterChanged`
messages when any filter value changes.
"""

from __future__ import annotations

from typing import Any, NamedTuple

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Input, Select


class FilterDef(NamedTuple):
    """Definition for a dropdown filter in the :class:`FilterBar`.

    Attributes:
        name: Internal name used as key in the filters dict.
        label: Display label for the dropdown (used as the first
            option when ``default`` is empty).
        options: List of ``(value, display_text)`` tuples.
        default: Default selected value. Empty string means no selection.
    """

    name: str
    label: str
    options: list[tuple[str, str]]
    default: str = ""


class FilterBar(Widget):
    """Search input with optional dropdown filters.

    Emits :class:`FilterChanged` whenever the search text is submitted
    or any dropdown selection changes.

    Usage::

        yield FilterBar(
            search_placeholder="Search events...",
            filters=[
                FilterDef(
                    name="level",
                    label="Level",
                    options=[("all", "All"), ("info", "Info"), ("error", "Error")],
                    default="all",
                ),
            ],
        )
    """

    DEFAULT_CSS = """
    FilterBar {
        height: auto;
        min-height: 3;
        max-height: 5;
    }
    FilterBar Horizontal {
        height: 3;
    }
    FilterBar Input {
        width: 1fr;
        min-width: 20;
    }
    FilterBar Select {
        width: 20;
        margin-right: 1;
    }
    """

    class FilterChanged(Message):
        """Posted when any filter value changes.

        Attributes:
            search: Current search text.
            filters: Mapping of filter names to their selected values.
        """

        def __init__(self, search: str, filters: dict[str, Any]) -> None:
            """Initialize the message with search text and filter values."""
            self.search = search
            self.filters = filters
            super().__init__()

    def __init__(
        self,
        *,
        search_placeholder: str = "Search...",
        filters: list[FilterDef] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the filter bar.

        Args:
            search_placeholder: Placeholder text for the search input.
            filters: Optional list of dropdown filter definitions.
            **kwargs: Additional keyword arguments forwarded to ``Widget``.
        """
        super().__init__(**kwargs)
        self._search_placeholder = search_placeholder
        self._filters = filters or []

    def compose(self) -> ComposeResult:
        """Compose the filter bar layout."""
        with Horizontal():
            for filter_def in self._filters:
                options = [(display, value) for value, display in filter_def.options]
                yield Select(
                    options,
                    id=f"filter-{filter_def.name}",
                    value=filter_def.default or Select.BLANK,
                )
            yield Input(
                placeholder=self._search_placeholder,
                id="filter-search",
            )

    def get_filter_values(self) -> dict[str, Any]:
        """Get the current values of all dropdown filters.

        Returns:
            Mapping of filter names to selected values.
        """
        values: dict[str, Any] = {}
        for filter_def in self._filters:
            try:
                select = self.query_one(f"#filter-{filter_def.name}", Select)
                val = select.value
                values[filter_def.name] = str(val) if val is not Select.BLANK else ""
            except Exception:
                values[filter_def.name] = filter_def.default
        return values

    def get_search_text(self) -> str:
        """Get the current search input text.

        Returns:
            Current text in the search input.
        """
        try:
            return self.query_one("#filter-search", Input).value
        except Exception:
            return ""

    def _emit_filter_changed(self) -> None:
        """Post a FilterChanged message with current values."""
        self.post_message(
            self.FilterChanged(
                search=self.get_search_text(),
                filters=self.get_filter_values(),
            )
        )

    def on_select_changed(self, _event: Select.Changed) -> None:
        """Handle dropdown filter changes."""
        self._emit_filter_changed()

    def on_input_submitted(self, _event: Input.Submitted) -> None:
        """Handle search text submission."""
        self._emit_filter_changed()
