Module madsci.client.cli.tui.screens.data_browser
=================================================
Data browser screen for MADSci TUI.

Provides datapoint browsing with filtering by label and data type,
a type-aware detail panel for selected datapoints, and preview
information for JSON, file, and object storage types.

Classes
-------

`DataBrowserScreen(**kwargs: Any)`
:   Screen showing data browser with type-aware detail display.
    
    Initialize the screen.

    ### Ancestors (in MRO)

    * madsci.client.cli.tui.mixins.ActionBarMixin
    * madsci.client.cli.tui.mixins.AutoRefreshMixin
    * madsci.client.cli.tui.mixins.ServiceURLMixin
    * textual.screen.Screen
    * typing.Generic
    * textual.widget.Widget
    * textual.dom.DOMNode
    * textual.message_pump.MessagePump

    ### Class variables

    `BINDINGS: ClassVar[list['Binding | tuple[str, str] | tuple[str, str, str]']]`
    :

    `can_focus`
    :

    `can_focus_children`
    :

    ### Methods

    `action_go_back(self) ‑> None`
    :   Go back to the dashboard.

    `action_refresh(self) ‑> None`
    :   Refresh data.

    `compose(self) ‑> Iterable[textual.widget.Widget]`
    :   Compose the data browser screen layout.

    `on_data_table_row_selected(self, event: textual.widgets._data_table.DataTable.RowSelected) ‑> None`
    :   Handle row selection in the data table.
        
        Args:
            event: The row selected event.

    `on_filter_bar_filter_changed(self, event: madsci.client.cli.tui.widgets.filter_bar.FilterBar.FilterChanged) ‑> None`
    :   Handle filter changes from the FilterBar.
        
        Args:
            event: The filter changed event with search and filters.

    `on_mount(self) ‑> None`
    :   Handle screen mount - set up table and load data.

    `refresh_data(self) ‑> None`
    :   Refresh datapoint data from the data manager.