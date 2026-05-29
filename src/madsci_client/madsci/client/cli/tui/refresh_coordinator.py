"""Screen refresh coordinator for MADSci TUI.

Provides :class:`ScreenRefreshCoordinator`, which guards against concurrent
auto-refresh calls on the same screen.
"""

from __future__ import annotations

import contextlib


class ScreenRefreshCoordinator:
    """Coordinates auto-refresh calls across TUI screens.

    Tracks which screens are currently refreshing to prevent concurrent
    ``refresh_data()`` calls on the same screen when the auto-refresh timer
    fires faster than a screen can complete its refresh.

    Usage::

        coordinator = ScreenRefreshCoordinator()
        await coordinator.refresh(self.screen)
    """

    def __init__(self) -> None:
        """Initialize the coordinator with an empty set of refreshing screens."""
        self._refreshing_screens: set[int] = set()

    async def force_refresh(self, screen: object) -> None:
        """Force a refresh of a screen, bypassing the in-progress guard.

        Unlike :meth:`refresh`, this method always executes ``refresh_data()``
        and registers the screen as refreshing to prevent concurrent
        auto-refresh calls while it runs. Exceptions are not suppressed.

        Args:
            screen: The TUI screen to refresh.
        """
        if not hasattr(screen, "refresh_data"):
            return
        screen_id = id(screen)
        self._refreshing_screens.add(screen_id)
        try:
            await screen.refresh_data()
        finally:
            self._refreshing_screens.discard(screen_id)

    async def refresh(self, screen: object) -> None:
        """Refresh a screen if eligible and not already refreshing.

        A screen is eligible if it has ``auto_refresh_enabled`` set to
        ``True`` and a ``refresh_data()`` coroutine method. If a refresh
        is already in progress for this screen, the call is silently
        skipped. Exceptions raised by ``refresh_data()`` are suppressed.

        Args:
            screen: The active TUI screen to refresh.
        """
        if not (
            getattr(screen, "auto_refresh_enabled", False)
            and hasattr(screen, "refresh_data")
        ):
            return
        screen_id = id(screen)
        if screen_id in self._refreshing_screens:
            return
        self._refreshing_screens.add(screen_id)
        try:
            with contextlib.suppress(Exception):
                await screen.refresh_data()
        finally:
            self._refreshing_screens.discard(screen_id)
