Module madsci.client.cli.tui.widgets
====================================
TUI widgets for MADSci.

Reusable Textual widgets extracted from duplicated patterns across TUI
screens. Each widget has a single responsibility and can be composed
into any screen.

Widgets:
    :class:`StatusBadge` -- Coloured status indicator icon with optional text.
    :class:`DetailPanel` -- Key-value detail display with titled sections.
    :class:`DetailSection` -- Named tuple for DetailPanel sections.
    :class:`ServiceAwareContainer` -- Container gated behind service health checks.
    :class:`DataTableView` -- Enhanced DataTable with declarative columns.
    :class:`ColumnDef` -- Column definition for DataTableView.
    :class:`ActionBar` -- Row of keyboard-bound actions.
    :class:`ActionDef` -- Action definition for ActionBar.
    :class:`FilterBar` -- Search input with dropdown filters.
    :class:`FilterDef` -- Filter definition for FilterBar.
    :class:`LogViewer` -- Rich log viewer with follow mode and deduplication.

Sub-modules
-----------
* madsci.client.cli.tui.widgets.action_bar
* madsci.client.cli.tui.widgets.data_table_view
* madsci.client.cli.tui.widgets.detail_panel
* madsci.client.cli.tui.widgets.filter_bar
* madsci.client.cli.tui.widgets.log_viewer
* madsci.client.cli.tui.widgets.service_aware
* madsci.client.cli.tui.widgets.status_badge

Classes
-------

`ActionBar(actions: list[ActionDef], **kwargs: Any)`
:   Displays a row of clickable action buttons with keyboard hints.
    
    Each button shows ``(key) Label`` and posts :class:`ActionTriggered`
    messages when clicked.
    
    Usage::
    
        yield ActionBar(actions=[
            ActionDef("r", "Refresh", "refresh"),
            ActionDef("p", "Pause", "pause", variant="warning"),
            ActionDef("c", "Cancel", "cancel", variant="error"),
        ])
    
    Initialize the action bar.
    
    Args:
        actions: List of action definitions to display.
        **kwargs: Additional keyword arguments forwarded to ``Widget``.

    ### Ancestors (in MRO)

    * textual.widget.Widget
    * textual.dom.DOMNode
    * textual.message_pump.MessagePump

    ### Class variables

    `ActionTriggered`
    :   Posted when an action is triggered.
        
        Attributes:
            action: The action name from the :class:`ActionDef`.

    `DEFAULT_CSS`
    :

    `can_focus`
    :

    `can_focus_children`
    :

    ### Methods

    `compose(self) ‑> Iterable[textual.widget.Widget]`
    :   Compose the action bar as a row of buttons.

    `on_button_pressed(self, event: Button.Pressed) ‑> None`
    :   Handle button press — post ActionTriggered message.

    `trigger_action(self, action_name: str) ‑> None`
    :   Programmatically trigger a named action.
        
        Posts an :class:`ActionTriggered` message if the action name
        matches a defined action.
        
        Args:
            action_name: Name of the action to trigger.

`ActionDef(key: ForwardRef('str'), label: ForwardRef('str'), action: ForwardRef('str'), variant: ForwardRef('str') = 'default')`
:   Definition for a single action displayed in the :class:`ActionBar`.
    
    Attributes:
        key: Keyboard key label, e.g. ``"r"``.
        label: Human-readable action label, e.g. ``"Refresh"``.
        action: Action name used in :class:`ActionTriggered` messages.
        variant: Visual variant: ``"default"``, ``"primary"``, ``"success"``,
            ``"warning"``, or ``"error"``.

    ### Ancestors (in MRO)

    * builtins.tuple

    ### Instance variables

    `action: str`
    :   Alias for field number 2

    `key: str`
    :   Alias for field number 0

    `label: str`
    :   Alias for field number 1

    `variant: str`
    :   Alias for field number 3

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

`DetailPanel(*, placeholder: str = 'Select an item to view details', **kwargs: object)`
:   Key-value detail display with titled sections.
    
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
    
    Initialize the detail panel.
    
    Args:
        placeholder: Text shown when no content has been set.
        **kwargs: Additional keyword arguments forwarded to ``Static``.

    ### Ancestors (in MRO)

    * textual.widgets._static.Static
    * textual.widget.Widget
    * textual.dom.DOMNode
    * textual.message_pump.MessagePump

    ### Class variables

    `DEFAULT_CSS`
    :

    `can_focus`
    :

    `can_focus_children`
    :

    ### Methods

    `clear_content(self) ‑> None`
    :   Reset the panel to its placeholder state.

    `compose(self) ‑> Iterable[textual.widget.Widget]`
    :   Compose the panel with a content label.

    `update_content(self, title: str, sections: list[DetailSection]) ‑> None`
    :   Update the panel with new content.
        
        Args:
            title: Main title displayed at the top of the panel.
            sections: List of sections to display below the title.

`DetailSection(title: ForwardRef('str'), fields: ForwardRef('dict[str, str]'))`
:   A titled section containing key-value pairs.
    
    Attributes:
        title: Section heading text.
        fields: Mapping of field labels to their formatted display values.
            Values may contain Rich markup for coloured output.

    ### Ancestors (in MRO)

    * builtins.tuple

    ### Instance variables

    `fields: dict[str, str]`
    :   Alias for field number 1

    `title: str`
    :   Alias for field number 0

`FilterBar(*, search_placeholder: str = 'Search...', filters: list[FilterDef] | None = None, **kwargs: Any)`
:   Search input with optional dropdown filters.
    
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
    
    Initialize the filter bar.
    
    Args:
        search_placeholder: Placeholder text for the search input.
        filters: Optional list of dropdown filter definitions.
        **kwargs: Additional keyword arguments forwarded to ``Widget``.

    ### Ancestors (in MRO)

    * textual.widget.Widget
    * textual.dom.DOMNode
    * textual.message_pump.MessagePump

    ### Class variables

    `DEFAULT_CSS`
    :

    `FilterChanged`
    :   Posted when any filter value changes.
        
        Attributes:
            search: Current search text.
            filters: Mapping of filter names to their selected values.

    `can_focus`
    :

    `can_focus_children`
    :

    ### Methods

    `compose(self) ‑> Iterable[textual.widget.Widget]`
    :   Compose the filter bar layout.

    `get_filter_values(self) ‑> dict[str, typing.Any]`
    :   Get the current values of all dropdown filters.
        
        Returns:
            Mapping of filter names to selected values.

    `get_search_text(self) ‑> str`
    :   Get the current search input text.
        
        Returns:
            Current text in the search input.

    `on_input_submitted(self, _event: Input.Submitted) ‑> None`
    :   Handle search text submission.

    `on_select_changed(self, _event: Select.Changed) ‑> None`
    :   Handle dropdown filter changes.

`FilterDef(name: ForwardRef('str'), label: ForwardRef('str'), options: ForwardRef('list[tuple[str, str]]'), default: ForwardRef('str') = '')`
:   Definition for a dropdown filter in the :class:`FilterBar`.
    
    Attributes:
        name: Internal name used as key in the filters dict.
        label: Display label for the dropdown (used as the first
            option when ``default`` is empty).
        options: List of ``(value, display_text)`` tuples.
        default: Default selected value. Empty string means no selection.

    ### Ancestors (in MRO)

    * builtins.tuple

    ### Instance variables

    `default: str`
    :   Alias for field number 3

    `label: str`
    :   Alias for field number 1

    `name: str`
    :   Alias for field number 0

    `options: list[tuple[str, str]]`
    :   Alias for field number 2

`LogViewer(*, max_seen: int = 10000, **kwargs: Any)`
:   Rich log viewer with follow mode and deduplication.
    
    Features:
    - Level-based colouring via a pluggable formatter.
    - Follow mode: auto-scroll to the latest entry.
    - Deduplication: bounded ``OrderedDict`` of seen IDs (default 10k).
    - Pluggable formatter via :meth:`set_formatter`.
    
    Usage::
    
        viewer = LogViewer()
        count = viewer.append_entries(entries, id_key="event_id")
        viewer.follow_mode = True
        viewer.clear()
    
    Initialize the log viewer.
    
    Args:
        max_seen: Maximum number of entry IDs to track for
            deduplication. Oldest entries are evicted when this
            limit is reached.
        **kwargs: Additional keyword arguments forwarded to ``Widget``.

    ### Ancestors (in MRO)

    * textual.widget.Widget
    * textual.dom.DOMNode
    * textual.message_pump.MessagePump

    ### Class variables

    `DEFAULT_CSS`
    :

    `can_focus`
    :

    `can_focus_children`
    :

    ### Instance variables

    `follow_mode: Reactive[ReactiveType] | ReactiveType`
    :   Create a reactive attribute.
        
        Args:
            default: A default value or callable that returns a default.
            layout: Perform a layout on change.
            repaint: Perform a repaint on change.
            init: Call watchers on initialize (post mount).
            always_update: Call watchers even when the new value equals the old value.
            recompose: Compose the widget again when the attribute changes.
            bindings: Refresh bindings when the reactive changes.
            toggle_class: An optional TCSS classname(s) to toggle based on the truthiness of the value.

    ### Methods

    `append_entries(self, entries: list[dict[str, Any]], id_key: str = 'event_id') ‑> int`
    :   Append new log entries with deduplication.
        
        Args:
            entries: List of log entry dictionaries.
            id_key: Key used to extract unique IDs from entries. Falls
                back to ``"_id"`` then ``hash(str(entry))`` if the key
                is missing.
        
        Returns:
            Number of *new* (non-duplicate) entries that were appended.

    `clear(self) ‑> None`
    :   Clear all displayed log entries and the dedup cache.

    `compose(self) ‑> Iterable[textual.widget.Widget]`
    :   Compose the log viewer.

    `set_formatter(self, formatter: Callable[[dict[str, Any]], str]) ‑> None`
    :   Set a custom entry formatter.
        
        Args:
            formatter: Callable that takes an entry dict and returns a
                Rich-formatted string.

    `watch_follow_mode(self, value: bool) ‑> None`
    :   Scroll to end when follow mode is enabled.

`ServiceAwareContainer(service_url: str, service_name: str, *, check_interval: float = 5.0, **kwargs: Any)`
:   Container that gates children behind a service health check.
    
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
    
    Initialize the container.
    
    Args:
        service_url: Base URL of the service to check.
        service_name: Human-readable service name for display.
        check_interval: Interval in seconds between health checks.
        **kwargs: Additional keyword arguments forwarded to ``Widget``.

    ### Ancestors (in MRO)

    * textual.widget.Widget
    * textual.dom.DOMNode
    * textual.message_pump.MessagePump

    ### Class variables

    `DEFAULT_CSS`
    :

    `ServiceAvailable`
    :   Posted when the service becomes available.

    `ServiceUnavailable`
    :   Posted when the service becomes unavailable.

    `can_focus`
    :

    `can_focus_children`
    :

    ### Instance variables

    `is_available: Reactive[ReactiveType] | ReactiveType`
    :   Create a reactive attribute.
        
        Args:
            default: A default value or callable that returns a default.
            layout: Perform a layout on change.
            repaint: Perform a repaint on change.
            init: Call watchers on initialize (post mount).
            always_update: Call watchers even when the new value equals the old value.
            recompose: Compose the widget again when the attribute changes.
            bindings: Refresh bindings when the reactive changes.
            toggle_class: An optional TCSS classname(s) to toggle based on the truthiness of the value.

    ### Methods

    `check_health(self) ‑> bool`
    :   Perform a health check against the service.
        
        Returns:
            ``True`` if the service is available, ``False`` otherwise.

    `compose(self) ‑> Iterable[textual.widget.Widget]`
    :   Compose the container layout.

    `on_button_pressed(self, event: Button.Pressed) ‑> None`
    :   Handle retry button press.

    `on_mount(self) ‑> None`
    :   Start periodic health checks on mount.

    `watch_is_available(self, value: bool) ‑> None`
    :   React to availability changes by toggling panels.

`StatusBadge(status: str = 'unknown', *, show_text: bool = True, **kwargs: object)`
:   Displays a colored status indicator icon with optional text.
    
    The badge automatically updates when the ``status`` reactive property
    changes. Styling is derived from :func:`get_status_style` which
    provides a consistent ``(icon, colour)`` mapping across the TUI.
    
    Usage::
    
        yield StatusBadge("healthy")
        yield StatusBadge("running", show_text=True)
        badge.status = "failed"  # reactive update
    
    Initialize the status badge.
    
    Args:
        status: Initial status string (e.g. ``"healthy"``, ``"running"``).
        show_text: Whether to display the status text alongside the icon.
        **kwargs: Additional keyword arguments forwarded to ``Static``.

    ### Ancestors (in MRO)

    * textual.widgets._static.Static
    * textual.widget.Widget
    * textual.dom.DOMNode
    * textual.message_pump.MessagePump

    ### Class variables

    `can_focus`
    :

    `can_focus_children`
    :

    ### Instance variables

    `show_text: Reactive[ReactiveType] | ReactiveType`
    :   Create a reactive attribute.
        
        Args:
            default: A default value or callable that returns a default.
            layout: Perform a layout on change.
            repaint: Perform a repaint on change.
            init: Call watchers on initialize (post mount).
            always_update: Call watchers even when the new value equals the old value.
            recompose: Compose the widget again when the attribute changes.
            bindings: Refresh bindings when the reactive changes.
            toggle_class: An optional TCSS classname(s) to toggle based on the truthiness of the value.

    `status: Reactive[ReactiveType] | ReactiveType`
    :   Create a reactive attribute.
        
        Args:
            default: A default value or callable that returns a default.
            layout: Perform a layout on change.
            repaint: Perform a repaint on change.
            init: Call watchers on initialize (post mount).
            always_update: Call watchers even when the new value equals the old value.
            recompose: Compose the widget again when the attribute changes.
            bindings: Refresh bindings when the reactive changes.
            toggle_class: An optional TCSS classname(s) to toggle based on the truthiness of the value.

    ### Methods

    `render(self) ‑> str`
    :   Render the badge as Rich markup.
        
        Returns:
            Rich-formatted string with coloured icon and optional text.

    `watch_show_text(self, _value: bool) ‑> None`
    :   React to show_text changes by refreshing the display.

    `watch_status(self, _value: str) ‑> None`
    :   React to status changes by refreshing the display.