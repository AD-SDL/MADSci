"""DataTableView widget for MADSci TUI.

Enhanced DataTable wrapper with declarative column definitions,
empty state handling, and typed row selection messages.
"""

from __future__ import annotations

from typing import Any, NamedTuple

from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.widgets import DataTable, Label


class ColumnDef(NamedTuple):
    """Declarative column definition for :class:`DataTableView`.

    Attributes:
        key: Data key used to extract cell values from row dicts.
        label: Column header text displayed in the table.
        width: Optional fixed column width. ``None`` for auto-sizing.
    """

    key: str
    label: str
    width: int | None = None


class DataTableView(Widget):
    """Enhanced DataTable with common patterns.

    Provides:
    - Declarative column definition via :class:`ColumnDef`
    - Empty state message when no rows are present
    - Atomic ``clear_and_populate()`` for refresh cycles
    - Typed row selection via :class:`RowSelected` message

    Usage::

        table = DataTableView(
            columns=[
                ColumnDef("status", "Status"),
                ColumnDef("name", "Name"),
                ColumnDef("url", "URL", width=30),
            ],
            empty_message="No services found",
        )
        table.clear_and_populate([
            {"status": "[green]OK[/green]", "name": "event", "url": "http://..."},
        ])
    """

    DEFAULT_CSS = """
    DataTableView {
        height: auto;
        min-height: 4;
    }
    DataTableView DataTable {
        height: auto;
    }
    DataTableView .dtv-empty {
        text-align: center;
        color: $text-muted;
        padding: 1 2;
    }
    """

    class RowSelected(Message):
        """Posted when a row is selected in the table.

        Attributes:
            row_data: Dictionary mapping column keys to their cell values.
            row_index: Zero-based index of the selected row.
        """

        def __init__(self, row_data: dict[str, Any], row_index: int) -> None:
            """Initialize the message with row data and index."""
            self.row_data = row_data
            self.row_index = row_index
            super().__init__()

    def __init__(
        self,
        columns: list[ColumnDef],
        *,
        empty_message: str = "No data",
        **kwargs: Any,
    ) -> None:
        """Initialize the DataTableView.

        Args:
            columns: List of column definitions.
            empty_message: Message to display when the table has no rows.
            **kwargs: Additional keyword arguments forwarded to ``Widget``.
        """
        super().__init__(**kwargs)
        self._columns = columns
        self._empty_message = empty_message
        self._rows: list[dict[str, Any]] = []

    def compose(self) -> ComposeResult:
        """Compose the widget."""
        yield DataTable(id="dtv-table")
        yield Label(
            f"[dim]{self._empty_message}[/dim]",
            id="dtv-empty-label",
            classes="dtv-empty",
        )

    def on_mount(self) -> None:
        """Set up the table columns on mount."""
        table = self.query_one("#dtv-table", DataTable)
        for col in self._columns:
            if col.width is not None:
                table.add_column(col.label, key=col.key, width=col.width)
            else:
                table.add_column(col.label, key=col.key)
        table.cursor_type = "row"
        # Show empty label initially
        self._update_empty_state()

    def clear_and_populate(self, rows: list[dict[str, Any]]) -> None:
        """Clear the table and populate with new data atomically.

        Args:
            rows: List of row dictionaries. Each dict should have keys
                matching the ``key`` fields of the column definitions.
        """
        self._rows = list(rows)
        table = self.query_one("#dtv-table", DataTable)
        table.clear()

        for row in self._rows:
            cells = [str(row.get(col.key, "")) for col in self._columns]
            table.add_row(*cells)

        self._update_empty_state()

    def _update_empty_state(self) -> None:
        """Toggle empty label visibility based on row count."""
        table = self.query_one("#dtv-table", DataTable)
        empty_label = self.query_one("#dtv-empty-label", Label)
        has_rows = len(self._rows) > 0
        table.display = has_rows
        empty_label.display = not has_rows

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Translate DataTable selection into a typed RowSelected message."""
        if event.data_table.id != "dtv-table":
            return

        # Find the row index from the cursor coordinate
        row_index = event.cursor_row
        if 0 <= row_index < len(self._rows):
            self.post_message(
                self.RowSelected(
                    row_data=dict(self._rows[row_index]),
                    row_index=row_index,
                )
            )
