Module madsci.client.cli.tui.screens.resource_tree
==================================================
Resource hierarchy tree screen for MADSci TUI.

A pushed screen that visualises the parent-child hierarchy of
a resource using Textual's Tree widget.

Classes
-------

`ResourceTreeScreen(resource_id: str, resource_url: str, **kwargs: Any)`
:   Screen showing the resource hierarchy as a tree.
    
    Initialize the resource tree screen.
    
    Args:
        resource_id: ID of the resource to display hierarchy for.
        resource_url: Base URL of the resource manager.
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
    :   Go back to the resources screen.

    `compose(self) ‑> Iterable[textual.widget.Widget]`
    :   Compose the tree screen layout.

    `on_mount(self) ‑> None`
    :   Handle mount - fetch hierarchy and build tree.