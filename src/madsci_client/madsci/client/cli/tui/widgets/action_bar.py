"""ActionBar widget for MADSci TUI.

Row of action buttons with keyboard binding labels. Provides a
standardised footer-style action display used across TUI screens.
"""

from __future__ import annotations

from typing import NamedTuple

from textual.message import Message
from textual.widgets import Static

# Variant -> Rich colour mapping for rendering
_VARIANT_COLOURS: dict[str, str] = {
    "default": "dim",
    "primary": "blue",
    "success": "green",
    "warning": "yellow",
    "error": "red",
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


class ActionBar(Static):
    """Displays a row of keyboard-bound actions.

    Renders each action as ``[key] Label`` with variant-based colouring.
    Posts :class:`ActionTriggered` messages when actions are invoked
    programmatically.

    Usage::

        yield ActionBar(actions=[
            ActionDef("r", "Refresh", "refresh"),
            ActionDef("p", "Pause", "pause", variant="warning"),
            ActionDef("c", "Cancel", "cancel", variant="error"),
        ])
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
        **kwargs: object,
    ) -> None:
        """Initialize the action bar.

        Args:
            actions: List of action definitions to display.
            **kwargs: Additional keyword arguments forwarded to ``Static``.
        """
        super().__init__(**kwargs)
        self._actions = list(actions)

    def render(self) -> str:
        """Render the action bar as Rich markup.

        Returns:
            Formatted string with all action entries.
        """
        parts: list[str] = []
        for action_def in self._actions:
            colour = _VARIANT_COLOURS.get(action_def.variant, "dim")
            parts.append(f"[{colour}][{action_def.key}][/{colour}] {action_def.label}")
        return "  ".join(parts)

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
