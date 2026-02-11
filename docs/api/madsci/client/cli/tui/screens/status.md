Module madsci.client.cli.tui.screens.status
===========================================
Status screen for MADSci TUI.

Provides detailed service status with health information.

Classes
-------

`ServiceDetailPanel(**kwargs: Any)`
:   Panel showing details for a selected service.

    Initialize the panel.

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

    `compose(self) ‑> Iterable[textual.widget.Widget]`
    :   Compose the panel.

    `update_details(self, name: str, data: dict) ‑> None`
    :   Update the detail display.

        Args:
            name: Service name.
            data: Service data dictionary.

`StatusScreen(**kwargs: Any)`
:   Screen showing detailed service status.

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
    :   Refresh status data.

    `compose(self) ‑> Iterable[textual.widget.Widget]`
    :   Compose the status screen layout.

    `on_data_table_row_selected(self, event: textual.widgets._data_table.DataTable.RowSelected) ‑> None`
    :   Handle row selection in the table.

    `on_mount(self) ‑> None`
    :   Handle screen mount - set up tables and load data.

    `refresh_data(self) ‑> None`
    :   Refresh all service statuses.
