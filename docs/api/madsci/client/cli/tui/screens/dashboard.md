Module madsci.client.cli.tui.screens.dashboard
==============================================
Dashboard screen for MADSci TUI.

Provides an overview of the lab status including services, nodes,
active workflows, and recent events.

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

    `action_refresh(self) ‑> None`
    :   Refresh dashboard data.

    `compose(self) ‑> Iterable[textual.widget.Widget]`
    :   Compose the dashboard layout.

    `on_mount(self) ‑> None`
    :   Handle screen mount - initial data load.

    `refresh_data(self) ‑> None`
    :   Refresh all dashboard data.

`QuickActionsPanel(content: VisualType = '', *, expand: bool = False, shrink: bool = False, markup: bool = True, name: str | None = None, id: str | None = None, classes: str | None = None, disabled: bool = False)`
:   Panel showing quick action shortcuts.
    
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

    `can_focus`
    :

    `can_focus_children`
    :

    ### Methods

    `compose(self) ‑> Iterable[textual.widget.Widget]`
    :   Compose the panel.

    `on_button_pressed(self, event: textual.widgets._button.Button.Pressed) ‑> None`
    :   Handle quick action button presses.

`RecentEventsPanel(content: VisualType = '', *, expand: bool = False, shrink: bool = False, markup: bool = True, name: str | None = None, id: str | None = None, classes: str | None = None, disabled: bool = False)`
:   Panel showing recent events.
    
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

    `can_focus`
    :

    `can_focus_children`
    :

    ### Methods

    `compose(self) ‑> Iterable[textual.widget.Widget]`
    :   Compose the panel.

    `refresh_data(self) ‑> None`
    :   Refresh recent events.

`ServicesPanel(content: VisualType = '', *, expand: bool = False, shrink: bool = False, markup: bool = True, name: str | None = None, id: str | None = None, classes: str | None = None, disabled: bool = False)`
:   Panel showing all service statuses using StatusBadge widgets.
    
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

    `can_focus`
    :

    `can_focus_children`
    :

    ### Methods

    `compose(self) ‑> Iterable[textual.widget.Widget]`
    :   Compose the panel.

    `refresh_data(self) ‑> None`
    :   Refresh all service statuses using shared health check.