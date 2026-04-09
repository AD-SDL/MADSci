Module madsci.client.cli.tui.screens.transfer_graph
===================================================
Transfer graph visualization screen for MADSci TUI.

A pushed screen that shows the transfer adjacency list from the
Location Manager as a DataTable.

Classes
-------

`TransferGraphScreen(location_client: madsci.client.location_client.LocationClient, **kwargs: Any)`
:   Screen showing the transfer adjacency graph.
    
    Initialize the transfer graph screen.
    
    Args:
        location_client: LocationClient instance for fetching data.
        **kwargs: Additional keyword arguments forwarded to Screen.

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
    :   Go back to the locations screen.

    `action_refresh(self) ‑> None`
    :   Refresh the transfer graph.

    `compose(self) ‑> Iterable[textual.widget.Widget]`
    :   Compose the transfer graph screen layout.

    `on_mount(self) ‑> None`
    :   Handle mount - set up table and fetch graph data.