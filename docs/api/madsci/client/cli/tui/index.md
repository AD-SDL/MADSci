Module madsci.client.cli.tui
============================
MADSci Terminal User Interface.

This module provides an interactive terminal UI for managing and
monitoring MADSci labs.

Sub-modules
-----------
* madsci.client.cli.tui.app
* madsci.client.cli.tui.constants
* madsci.client.cli.tui.screens
* madsci.client.cli.tui.styles
* madsci.client.cli.tui.widgets

Classes
-------

`MadsciApp(lab_url: str = 'http://localhost:8000/', initial_screen: str = 'dashboard', context: MadsciContext | None = None)`
:   MADSci Terminal User Interface Application.

    Provides an interactive terminal interface for managing and
    monitoring MADSci labs.

    Initialize the MADSci TUI application.

    Args:
        lab_url: URL of the Lab Manager.
        initial_screen: Name of the screen to show on launch.
        context: Optional MadsciContext for service URLs.

    ### Ancestors (in MRO)

    * textual.app.App
    * typing.Generic
    * textual.dom.DOMNode
    * textual.message_pump.MessagePump

    ### Class variables

    `BINDINGS: ClassVar[list[Binding]]`
    :

    `CSS_PATH`
    :

    `SCREENS: ClassVar[dict[str, type[Screen]]]`
    :

    `SUB_TITLE`
    :

    `TITLE`
    :

    ### Methods

    `action_command_palette(self) ‑> None`
    :   Exit TUI and launch Trogon command palette.

    `action_refresh(self) ‑> None`
    :   Refresh the current screen.

    `action_show_help(self) ‑> None`
    :   Show help information.

    `action_switch_screen(self, screen: str) ‑> None`
    :   Switch to a named screen.

        Args:
            screen: Name of the screen to switch to.

    `compose(self) ‑> Iterable[textual.widget.Widget]`
    :   Compose the application layout.

    `on_mount(self) ‑> None`
    :   Handle application mount event.
