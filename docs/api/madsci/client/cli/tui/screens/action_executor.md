Module madsci.client.cli.tui.screens.action_executor
====================================================
Action executor screen for MADSci TUI.

Provides an interactive screen for selecting and executing actions on
a MADSci node, with JSON argument input and result display.

Classes
-------

`ActionExecutorScreen(node_name: str, node_url: str, actions: dict[str, typing.Any], **kwargs: Any)`
:   Interactive action execution on a node.
    
    Allows the user to select an action from a dropdown, provide JSON
    arguments, execute the action, and view the result in a detail panel.
    
    Initialize the action executor screen.
    
    Args:
        node_name: Name of the target node.
        node_url: Base URL of the target node.
        actions: Dict mapping action names to action definitions.
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
    :   Go back to the nodes screen.

    `compose(self) ‑> Iterable[textual.widget.Widget]`
    :   Compose the action executor layout.

    `on_button_pressed(self, event: textual.widgets._button.Button.Pressed) ‑> None`
    :   Handle button press events.
        
        Args:
            event: The button pressed event.

    `on_select_changed(self, event: textual.widgets._select.Select.Changed) ‑> None`
    :   Update description when action selection changes.
        
        Args:
            event: The select changed event.

    `on_unmount(self) ‑> None`
    :   Clean up client connections when screen is unmounted.