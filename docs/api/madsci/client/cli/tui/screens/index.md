Module madsci.client.cli.tui.screens
====================================
TUI screens for MADSci.

This module contains the screen implementations for the MADSci TUI.

Sub-modules
-----------
* madsci.client.cli.tui.screens.dashboard
* madsci.client.cli.tui.screens.logs
* madsci.client.cli.tui.screens.status

Classes
-------

`DashboardScreen(name: str | None = None, id: str | None = None, classes: str | None = None)`
:   Main dashboard screen showing lab overview.

    Initialize the screen.

    Args:
        name: The name of the screen.
        id: The ID of the screen in the DOM.
        classes: The CSS classes for the screen.

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

    `action_refresh(self) ‑> None`
    :   Refresh dashboard data.

    `compose(self) ‑> Iterable[textual.widget.Widget]`
    :   Compose the dashboard layout.

    `on_mount(self) ‑> None`
    :   Handle screen mount - initial data load.

    `refresh_data(self) ‑> None`
    :   Refresh all dashboard data.

`LogsScreen(**kwargs: Any)`
:   Screen for viewing logs.

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

    `DEFAULT_CSS`
    :

    `can_focus`
    :

    `can_focus_children`
    :

    ### Methods

    `action_clear(self) ‑> None`
    :   Clear the log view.

    `action_go_back(self) ‑> None`
    :   Go back to the previous screen.

    `action_refresh(self) ‑> None`
    :   Refresh logs.

    `action_toggle_follow(self) ‑> None`
    :   Toggle follow mode.

    `compose(self) ‑> Iterable[textual.widget.Widget]`
    :   Compose the logs screen layout.

    `on_input_submitted(self, event: textual.widgets._input.Input.Submitted) ‑> None`
    :   Handle search input submission.

    `on_mount(self) ‑> None`
    :   Handle screen mount - load initial logs.

    `on_select_changed(self, event: textual.widgets._select.Select.Changed) ‑> None`
    :   Handle filter changes.

    `refresh_data(self) ‑> None`
    :   Fetch and display logs.

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
