Module madsci.client.cli.tui.screens.logs
=========================================
Logs screen for MADSci TUI.

Provides real-time log viewing with filtering capabilities.

Classes
-------

`LogsScreen(**kwargs: Any)`
:   Screen for viewing logs.
    
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

    `on_filter_bar_filter_changed(self, event: madsci.client.cli.tui.widgets.filter_bar.FilterBar.FilterChanged) ‑> None`
    :   Handle filter changes from FilterBar.

    `on_mount(self) ‑> None`
    :   Handle screen mount - load initial logs.

    `refresh_data(self) ‑> None`
    :   Fetch and display logs.