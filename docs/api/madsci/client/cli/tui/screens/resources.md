Module madsci.client.cli.tui.screens.resources
==============================================
Resource inventory screen for MADSci TUI.

Provides resource browsing with filtering by type and search,
a detail panel for selected resources, and actions for delete,
lock/unlock, and tree visualization.

Classes
-------

`ResourcesScreen(**kwargs: Any)`
:   Screen showing resource inventory and management.
    
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

    `action_delete_resource(self) ‑> None`
    :   Delete the selected resource.

    `action_go_back(self) ‑> None`
    :   Go back to the dashboard.

    `action_new_resource(self) ‑> None`
    :   Notify user to use CLI for resource creation.

    `action_refresh(self) ‑> None`
    :   Refresh resource data.

    `action_show_tree(self) ‑> None`
    :   Show the resource tree for the selected resource.

    `action_toggle_lock(self) ‑> None`
    :   Toggle lock on the selected resource.

    `compose(self) ‑> Iterable[textual.widget.Widget]`
    :   Compose the resources screen layout.

    `on_data_table_row_selected(self, event: textual.widgets._data_table.DataTable.RowSelected) ‑> None`
    :   Handle row selection in the resources table.
        
        Args:
            event: The row selected event.

    `on_filter_bar_filter_changed(self, event: madsci.client.cli.tui.widgets.filter_bar.FilterBar.FilterChanged) ‑> None`
    :   Handle filter changes from the FilterBar.
        
        Args:
            event: The filter changed event with search and filters.

    `on_mount(self) ‑> None`
    :   Handle screen mount - set up table and load data.

    `refresh_data(self) ‑> None`
    :   Refresh resource data from the resource manager.