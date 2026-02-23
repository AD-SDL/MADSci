Module madsci.client.cli.tui.screens.nodes
==========================================
Node management screen for MADSci TUI.

Provides node discovery, status monitoring, and action display
by querying the Workcell Manager.

Classes
-------

`NodeDetailPanel(**kwargs: Any)`
:   Panel showing details for a selected node.

    Initialize the panel.

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

    ### Methods

    `compose(self) ‑> Iterable[textual.widget.Widget]`
    :   Compose the panel.

    `update_details(self, name: str, data: dict) ‑> None`
    :   Update the detail display.

        Args:
            name: Node name.
            data: Node data dictionary.

`NodesScreen(**kwargs: Any)`
:   Screen showing node management and monitoring.

    Initialize the screen.

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
    :   Go back to the previous screen.

    `action_refresh(self) ‑> None`
    :   Refresh node data.

    `action_toggle_auto_refresh(self) ‑> None`
    :   Toggle auto-refresh on/off.

    `compose(self) ‑> Iterable[textual.widget.Widget]`
    :   Compose the nodes screen layout.

    `on_data_table_row_selected(self, event: textual.widgets._data_table.DataTable.RowSelected) ‑> None`
    :   Handle row selection in the table.

    `on_mount(self) ‑> None`
    :   Handle screen mount - set up table and load data.

    `refresh_data(self) ‑> None`
    :   Refresh node data from workcell manager.
