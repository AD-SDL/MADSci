Module madsci.client.cli.tui.widgets.action_bar
===============================================
ActionBar widget for MADSci TUI.

Row of action buttons with keyboard binding labels. Provides a
standardised footer-style action display used across TUI screens.

Classes
-------

`ActionBar(actions: list[ActionDef], **kwargs: Any)`
:   Displays a row of clickable action buttons with keyboard hints.
    
    Each button shows ``(key) Label`` and posts :class:`ActionTriggered`
    messages when clicked.
    
    Usage::
    
        yield ActionBar(actions=[
            ActionDef("r", "Refresh", "refresh"),
            ActionDef("p", "Pause", "pause", variant="warning"),
            ActionDef("c", "Cancel", "cancel", variant="error"),
        ])
    
    Initialize the action bar.
    
    Args:
        actions: List of action definitions to display.
        **kwargs: Additional keyword arguments forwarded to ``Widget``.

    ### Ancestors (in MRO)

    * textual.widget.Widget
    * textual.dom.DOMNode
    * textual.message_pump.MessagePump

    ### Class variables

    `ActionTriggered`
    :   Posted when an action is triggered.
        
        Attributes:
            action: The action name from the :class:`ActionDef`.

    `DEFAULT_CSS`
    :

    `can_focus`
    :

    `can_focus_children`
    :

    ### Methods

    `compose(self) ‑> Iterable[textual.widget.Widget]`
    :   Compose the action bar as a row of buttons.

    `on_button_pressed(self, event: Button.Pressed) ‑> None`
    :   Handle button press — post ActionTriggered message.

    `trigger_action(self, action_name: str) ‑> None`
    :   Programmatically trigger a named action.
        
        Posts an :class:`ActionTriggered` message if the action name
        matches a defined action.
        
        Args:
            action_name: Name of the action to trigger.

`ActionDef(key: ForwardRef('str'), label: ForwardRef('str'), action: ForwardRef('str'), variant: ForwardRef('str') = 'default')`
:   Definition for a single action displayed in the :class:`ActionBar`.
    
    Attributes:
        key: Keyboard key label, e.g. ``"r"``.
        label: Human-readable action label, e.g. ``"Refresh"``.
        action: Action name used in :class:`ActionTriggered` messages.
        variant: Visual variant: ``"default"``, ``"primary"``, ``"success"``,
            ``"warning"``, or ``"error"``.

    ### Ancestors (in MRO)

    * builtins.tuple

    ### Instance variables

    `action: str`
    :   Alias for field number 2

    `key: str`
    :   Alias for field number 0

    `label: str`
    :   Alias for field number 1

    `variant: str`
    :   Alias for field number 3