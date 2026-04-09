Module madsci.client.cli.tui.screens.status
===========================================
Status screen for MADSci TUI.

Provides detailed service status with health information.

Classes
-------

`StatusScreen(**kwargs: Any)`
:   Screen showing detailed service status.
    
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

    `BINDINGS: ClassVar[list[BindingType]]`
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

    `on_data_table_row_selected(self, event: DataTable.RowSelected) ‑> None`
    :   Handle row selection in the table.

    `on_mount(self) ‑> None`
    :   Handle screen mount - set up tables and load data.

    `refresh_data(self) ‑> None`
    :   Refresh all service statuses.