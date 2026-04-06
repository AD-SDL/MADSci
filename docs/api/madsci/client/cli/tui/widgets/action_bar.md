Module madsci.client.cli.tui.widgets.action_bar
===============================================
ActionBar widget for MADSci TUI.

Row of action buttons with keyboard binding labels. Provides a
standardised footer-style action display used across TUI screens.

Classes
-------

`ActionBar(actions: list[ActionDef], **kwargs: object)`
:   Displays a row of keyboard-bound actions.
    
    Renders each action as ``[key] Label`` with variant-based colouring.
    Posts :class:`ActionTriggered` messages when actions are invoked
    programmatically.
    
    Usage::
    
        yield ActionBar(actions=[
            ActionDef("r", "Refresh", "refresh"),
            ActionDef("p", "Pause", "pause", variant="warning"),
            ActionDef("c", "Cancel", "cancel", variant="error"),
        ])
    
    Initialize the action bar.
    
    Args:
        actions: List of action definitions to display.
        **kwargs: Additional keyword arguments forwarded to ``Static``.

    ### Ancestors (in MRO)

    * textual.widgets._static.Static
    * textual.widget.Widget
    * textual.dom.DOMNode
    * textual.message_pump.MessagePump

    ### Class variables

    `ActionTriggered`
    :   Posted when an action is triggered.
        
        Attributes:
            action: The action name from the :class:`ActionDef`.

    `can_focus`
    :

    `can_focus_children`
    :

    ### Methods

    `render(self) ‑> str`
    :   Render the action bar as Rich markup.
        
        Returns:
            Formatted string with all action entries.

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