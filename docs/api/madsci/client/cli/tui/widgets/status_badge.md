Module madsci.client.cli.tui.widgets.status_badge
=================================================
StatusBadge widget for MADSci TUI.

Displays a colored status indicator icon with optional text label.
Uses the centralised STATUS_STYLES from formatting utilities to ensure
consistent styling across the TUI.

Classes
-------

`StatusBadge(status: str = 'unknown', *, show_text: bool = True, **kwargs: object)`
:   Displays a colored status indicator icon with optional text.
    
    The badge automatically updates when the ``status`` reactive property
    changes. Styling is derived from :func:`get_status_style` which
    provides a consistent ``(icon, colour)`` mapping across the TUI.
    
    Usage::
    
        yield StatusBadge("healthy")
        yield StatusBadge("running", show_text=True)
        badge.status = "failed"  # reactive update
    
    Initialize the status badge.
    
    Args:
        status: Initial status string (e.g. ``"healthy"``, ``"running"``).
        show_text: Whether to display the status text alongside the icon.
        **kwargs: Additional keyword arguments forwarded to ``Static``.

    ### Ancestors (in MRO)

    * textual.widgets._static.Static
    * textual.widget.Widget
    * textual.dom.DOMNode
    * textual.message_pump.MessagePump

    ### Class variables

    `can_focus`
    :

    `can_focus_children`
    :

    ### Instance variables

    `show_text: Reactive[ReactiveType] | ReactiveType`
    :   Create a reactive attribute.
        
        Args:
            default: A default value or callable that returns a default.
            layout: Perform a layout on change.
            repaint: Perform a repaint on change.
            init: Call watchers on initialize (post mount).
            always_update: Call watchers even when the new value equals the old value.
            recompose: Compose the widget again when the attribute changes.
            bindings: Refresh bindings when the reactive changes.
            toggle_class: An optional TCSS classname(s) to toggle based on the truthiness of the value.

    `status: Reactive[ReactiveType] | ReactiveType`
    :   Create a reactive attribute.
        
        Args:
            default: A default value or callable that returns a default.
            layout: Perform a layout on change.
            repaint: Perform a repaint on change.
            init: Call watchers on initialize (post mount).
            always_update: Call watchers even when the new value equals the old value.
            recompose: Compose the widget again when the attribute changes.
            bindings: Refresh bindings when the reactive changes.
            toggle_class: An optional TCSS classname(s) to toggle based on the truthiness of the value.

    ### Methods

    `render(self) ‑> str`
    :   Render the badge as Rich markup.
        
        Returns:
            Rich-formatted string with coloured icon and optional text.

    `watch_show_text(self, _value: bool) ‑> None`
    :   React to show_text changes by refreshing the display.

    `watch_status(self, _value: str) ‑> None`
    :   React to status changes by refreshing the display.