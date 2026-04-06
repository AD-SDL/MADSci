Module madsci.client.cli.tui.screens.event_analytics
====================================================
Event analytics screen for MADSci TUI.

Provides a read-only analytics dashboard with utilization summary
data and a recent events table. Displays daily utilization periods
and the last 10 events for quick operational overview.

Classes
-------

`EventAnalyticsScreen(**kwargs: Any)`
:   Screen showing event analytics and utilization summaries.
    
    Initialize the screen.

    ### Ancestors (in MRO)

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
    :   Refresh analytics data.

    `compose(self) ‑> Iterable[textual.widget.Widget]`
    :   Compose the event analytics screen layout.

    `on_mount(self) ‑> None`
    :   Handle screen mount - set up tables and load data.

    `refresh_data(self) ‑> None`
    :   Refresh analytics data from the event manager.