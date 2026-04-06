Module madsci.client.cli.tui.screens.locations
==============================================
Location management screen for MADSci TUI.

Provides location browsing with search filtering, a detail panel for
selected locations, and an action to view the transfer adjacency graph.

Classes
-------

`LocationsScreen(**kwargs: Any)`
:   Screen showing location inventory and management.
    
    Initialize the screen.

    ### Ancestors (in MRO)

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
    :   Refresh location data.

    `action_show_transfer_graph(self) ‑> None`
    :   Show the transfer graph screen.

    `compose(self) ‑> Iterable[textual.widget.Widget]`
    :   Compose the locations screen layout.

    `on_data_table_row_selected(self, event: textual.widgets._data_table.DataTable.RowSelected) ‑> None`
    :   Handle row selection in the locations table.
        
        Args:
            event: The row selected event.

    `on_filter_bar_filter_changed(self, event: madsci.client.cli.tui.widgets.filter_bar.FilterBar.FilterChanged) ‑> None`
    :   Handle filter changes from the FilterBar.
        
        Args:
            event: The filter changed event with search and filters.

    `on_mount(self) ‑> None`
    :   Handle screen mount - set up table and load data.

    `refresh_data(self) ‑> None`
    :   Refresh location data from the location manager.