Module madsci.client.cli.tui.screens.logs
=========================================
Logs screen for MADSci TUI.

Provides real-time log viewing with filtering capabilities.

Classes
-------

`FilterPanel(content: VisualType = '', *, expand: bool = False, shrink: bool = False, markup: bool = True, name: str | None = None, id: str | None = None, classes: str | None = None, disabled: bool = False)`
:   Panel with log filters.

    Initialize a Widget.

    Args:
        *children: Child widgets.
        name: The name of the widget.
        id: The ID of the widget in the DOM.
        classes: The CSS classes for the widget.
        disabled: Whether the widget is disabled or not.
        markup: Enable content markup?

    ### Ancestors (in MRO)

    * textual.widgets._static.Static
    * textual.widget.Widget
    * textual.dom.DOMNode
    * textual.message_pump.MessagePump

    ### Class variables

    `DEFAULT_CSS`
    :

    `can_focus`
    :

    `can_focus_children`
    :

    ### Methods

    `compose(self) ‑> Iterable[textual.widget.Widget]`
    :   Compose the filter panel.

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
