Module madsci.client.cli.tui.refresh_coordinator
================================================
Screen refresh coordinator for MADSci TUI.

Provides :class:`ScreenRefreshCoordinator`, which guards against concurrent
auto-refresh calls on the same screen.

Classes
-------

`ScreenRefreshCoordinator()`
:   Coordinates auto-refresh calls across TUI screens.
    
    Tracks which screens are currently refreshing to prevent concurrent
    ``refresh_data()`` calls on the same screen when the auto-refresh timer
    fires faster than a screen can complete its refresh.
    
    Usage::
    
        coordinator = ScreenRefreshCoordinator()
        await coordinator.refresh(self.screen)
    
    Initialize the coordinator with an empty set of refreshing screens.

    ### Methods

    `force_refresh(self, screen: object) ‑> None`
    :   Force a refresh of a screen, bypassing the in-progress guard.
        
        Unlike :meth:`refresh`, this method always executes ``refresh_data()``
        and registers the screen as refreshing to prevent concurrent
        auto-refresh calls while it runs. Exceptions are not suppressed.
        
        Args:
            screen: The TUI screen to refresh.

    `refresh(self, screen: object) ‑> None`
    :   Refresh a screen if eligible and not already refreshing.
        
        A screen is eligible if it has ``auto_refresh_enabled`` set to
        ``True`` and a ``refresh_data()`` coroutine method. If a refresh
        is already in progress for this screen, the call is silently
        skipped. Exceptions raised by ``refresh_data()`` are suppressed.
        
        Args:
            screen: The active TUI screen to refresh.