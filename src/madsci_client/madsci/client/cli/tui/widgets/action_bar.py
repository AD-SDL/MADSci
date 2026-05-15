"""ActionBar widget for MADSci TUI.

Row of action buttons with keyboard binding labels. Provides a
standardised footer-style action display used across TUI screens.
"""

from __future__ import annotations

from typing import Any, NamedTuple

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button

# Variant mapping: ActionDef variant → Textual Button variant
_BUTTON_VARIANTS: dict[str, str] = {
    "default": "default",
    "primary": "primary",
    "success": "success",
    "warning": "warning",
    "error": "error",
}


class ActionDef(NamedTuple):
    """Definition for a single action displayed in the :class:`ActionBar`.

    Attributes:
        key: Keyboard key label, e.g. ``"r"``.
        label: Human-readable action label, e.g. ``"Refresh"``.
        action: Action name used in :class:`ActionTriggered` messages.
        variant: Visual variant: ``"default"``, ``"primary"``, ``"success"``,
            ``"warning"``, or ``"error"``.
    """

    key: str
    label: str
    action: str
    variant: str = "default"


class ActionBar(Widget):
    """Displays a row of clickable action buttons with keyboard hints.

    Each button shows ``(key) Label`` and posts :class:`ActionTriggered`
    messages when clicked.

    Usage::

        yield ActionBar(actions=[
            ActionDef("r", "Refresh", "refresh"),
            ActionDef("p", "Pause", "pause", variant="warning"),
            ActionDef("c", "Cancel", "cancel", variant="error"),
        ])
    """

    DEFAULT_CSS = """
    ActionBar {
        height: auto;
        min-height: 3;
        max-height: 5;
    }
    ActionBar Horizontal {
        height: auto;
    }
    ActionBar Button {
        min-width: 10;
        margin: 0 1 0 0;
    }
    """

    class ActionTriggered(Message):
        """Posted when an action is triggered.

        Attributes:
            action: The action name from the :class:`ActionDef`.
        """

        def __init__(self, action: str) -> None:
            """Initialize the message with the action name."""
            self.action = action
            super().__init__()

    def __init__(
        self,
        actions: list[ActionDef],
        **kwargs: Any,
    ) -> None:
        """Initialize the action bar.

        Args:
            actions: List of action definitions to display.
            **kwargs: Additional keyword arguments forwarded to ``Widget``.
        """
        super().__init__(**kwargs)
        self._actions = list(actions)

    def compose(self) -> ComposeResult:
        """Compose the action bar as a row of buttons."""
        with Horizontal():
            for action_def in self._actions:
                variant = _BUTTON_VARIANTS.get(action_def.variant, "default")
                yield Button(
                    f"({action_def.key}) {action_def.label}",
                    id=f"action-btn-{action_def.action}",
                    variant=variant,
                )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press — post ActionTriggered message."""
        button_id = event.button.id or ""
        prefix = "action-btn-"
        if button_id.startswith(prefix):
            action_name = button_id[len(prefix) :]
            self.post_message(self.ActionTriggered(action_name))

    def trigger_action(self, action_name: str) -> None:
        """Programmatically trigger a named action.

        Posts an :class:`ActionTriggered` message if the action name
        matches a defined action.

        Args:
            action_name: Name of the action to trigger.
        """
        for action_def in self._actions:
            if action_def.action == action_name:
                self.post_message(self.ActionTriggered(action_name))
                return
