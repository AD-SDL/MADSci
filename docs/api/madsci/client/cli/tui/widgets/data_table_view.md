Module madsci.client.cli.tui.widgets.data_table_view
====================================================
DataTableView widget for MADSci TUI.

Enhanced DataTable wrapper with declarative column definitions,
empty state handling, and typed row selection messages.

.. note:: Not yet used by any screen -- designed for future adoption.
   See https://github.com/AD-SDL/MADSci/issues/278

Classes
-------

`ColumnDef(key: ForwardRef('str'), label: ForwardRef('str'), width: ForwardRef('int | None') = None)`
:   Declarative column definition for :class:`DataTableView`.
    
    Attributes:
        key: Data key used to extract cell values from row dicts.
        label: Column header text displayed in the table.
        width: Optional fixed column width. ``None`` for auto-sizing.

    ### Ancestors (in MRO)

    * builtins.tuple

    ### Instance variables

    `key: str`
    :   Alias for field number 0

    `label: str`
    :   Alias for field number 1

    `width: int | None`
    :   Alias for field number 2

`DataTableView(columns: list[ColumnDef], *, empty_message: str = 'No data', **kwargs: Any)`
:   Enhanced DataTable with common patterns.
    
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
    
    Initialize the DataTableView.
    
    Args:
        columns: List of column definitions.
        empty_message: Message to display when the table has no rows.
        **kwargs: Additional keyword arguments forwarded to ``Widget``.

    ### Ancestors (in MRO)

    * textual.widget.Widget
    * textual.dom.DOMNode
    * textual.message_pump.MessagePump

    ### Class variables

    `DEFAULT_CSS`
    :

    `RowSelected`
    :   Posted when a row is selected in the table.
        
        Attributes:
            row_data: Dictionary mapping column keys to their cell values.
            row_index: Zero-based index of the selected row.

    `can_focus`
    :

    `can_focus_children`
    :

    ### Methods

    `clear_and_populate(self, rows: list[dict[str, Any]]) ‑> None`
    :   Clear the table and populate with new data, preserving cursor position.
        
        Args:
            rows: List of row dictionaries. Each dict should have keys
                matching the ``key`` fields of the column definitions.

    `compose(self) ‑> Iterable[textual.widget.Widget]`
    :   Compose the widget.

    `on_data_table_row_selected(self, event: DataTable.RowSelected) ‑> None`
    :   Translate DataTable selection into a typed RowSelected message.

    `on_mount(self) ‑> None`
    :   Set up the table columns on mount.