Module madsci.client.cli.tui.screens.nodes
==========================================
Node management screen for MADSci TUI.

Provides node discovery, status monitoring, admin command actions,
enhanced detail display, and action execution by querying the
Workcell Manager and communicating with nodes directly.

Classes
-------

`NodeDetailScreen(node_name: str, node_data: dict, **kwargs: Any)`
:   Screen showing details for a single node, pushed on top of NodesScreen.
    
    Initialize the detail screen.
    
    Args:
        node_name: Name of the node.
        node_data: Node data dictionary.

    ### Ancestors (in MRO)

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
    :   Go back to the nodes list.

    `action_refresh(self) ‑> None`
    :   Refresh node data by re-fetching from workcell manager.

    `compose(self) ‑> Iterable[textual.widget.Widget]`
    :   Compose the detail screen layout.

    `on_mount(self) ‑> None`
    :   Render the detail content on mount.

`NodesScreen(**kwargs: Any)`
:   Screen showing node management and monitoring.
    
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

    `action_execute_action(self) ‑> None`
    :   Open the action executor screen for the selected node.

    `action_go_back(self) ‑> None`
    :   Go back to the previous screen.

    `action_pause_node(self) ‑> None`
    :   Pause the selected node.

    `action_refresh(self) ‑> None`
    :   Refresh node data.

    `action_reset_node(self) ‑> None`
    :   Reset the selected node (clear errors).

    `action_resume_node(self) ‑> None`
    :   Resume the selected node.

    `action_toggle_lock_node(self) ‑> None`
    :   Toggle lock/unlock on the selected node.

    `compose(self) ‑> Iterable[textual.widget.Widget]`
    :   Compose the nodes screen layout.

    `on_action_bar_action_triggered(self, event: madsci.client.cli.tui.widgets.action_bar.ActionBar.ActionTriggered) ‑> None`
    :   Route ActionBar button triggers to screen actions.

    `on_data_table_row_selected(self, event: textual.widgets._data_table.DataTable.RowSelected) ‑> None`
    :   Handle row selection - push detail screen.

    `on_mount(self) ‑> None`
    :   Handle screen mount - set up table and load data.

    `refresh_data(self) ‑> None`
    :   Refresh node data from workcell manager.