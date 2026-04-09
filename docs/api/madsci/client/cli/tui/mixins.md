Module madsci.client.cli.tui.mixins
===================================
Screen mixins for MADSci TUI.

Provides reusable behaviours that can be mixed into any
:class:`~textual.screen.Screen` subclass.

Functions
---------

`preserve_cursor(table: DataTable) ‑> Generator[None, None, None]`
:   Context manager that preserves cursor position across a table refresh.
    
    Saves the current cursor row before the block executes, and
    restores it (clamped to the new row count) afterwards.
    
    Usage::
    
        with preserve_cursor(table):
            table.clear()
            for row in new_data:
                table.add_row(...)

Classes
-------

`ActionBarMixin()`
:   Mixin that dispatches ActionBar.ActionTriggered events to an action map.
    
    Subclasses should define a ``_get_action_map()`` method returning
    ``dict[str, Callable]`` mapping action IDs to handlers.
    
    Usage::
    
        class MyScreen(ActionBarMixin, AutoRefreshMixin, Screen):
            def _get_action_map(self) -> dict:
                return {
                    "refresh": self.action_refresh,
                    "toggle_auto_refresh": self.action_toggle_auto_refresh,
                }

    ### Descendants

    * madsci.client.cli.tui.screens.data_browser.DataBrowserScreen
    * madsci.client.cli.tui.screens.experiments.ExperimentsScreen
    * madsci.client.cli.tui.screens.locations.LocationsScreen
    * madsci.client.cli.tui.screens.nodes.NodesScreen
    * madsci.client.cli.tui.screens.resources.ResourcesScreen
    * madsci.client.cli.tui.screens.workflow_detail.WorkflowDetailScreen
    * madsci.client.cli.tui.screens.workflows.WorkflowsScreen

    ### Methods

    `on_action_bar_action_triggered(self, event: ActionBar.ActionTriggered) ‑> None`
    :   Dispatch an action bar event to the appropriate handler.

`AutoRefreshMixin()`
:   Adds auto-refresh toggle capability to any Screen.
    
    The consuming screen must implement a ``refresh_data()`` async method.
    The mixin provides the reactive ``auto_refresh_enabled`` flag and the
    ``action_toggle_auto_refresh()`` action that can be bound to a key.
    
    Usage::
    
        class MyScreen(AutoRefreshMixin, Screen):
            BINDINGS = [("a", "toggle_auto_refresh", "Auto-refresh")]
            refresh_interval = 5.0
    
            async def refresh_data(self) -> None:
                # Fetch and display data
                ...

    ### Descendants

    * madsci.client.cli.tui.screens.dashboard.DashboardScreen
    * madsci.client.cli.tui.screens.data_browser.DataBrowserScreen
    * madsci.client.cli.tui.screens.experiments.ExperimentsScreen
    * madsci.client.cli.tui.screens.locations.LocationsScreen
    * madsci.client.cli.tui.screens.logs.LogsScreen
    * madsci.client.cli.tui.screens.nodes.NodesScreen
    * madsci.client.cli.tui.screens.resources.ResourcesScreen
    * madsci.client.cli.tui.screens.status.StatusScreen
    * madsci.client.cli.tui.screens.workflows.WorkflowsScreen

    ### Class variables

    `refresh_interval: float`
    :

    ### Instance variables

    `auto_refresh_enabled: textual.reactive.reactive[bool]`
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

    `action_toggle_auto_refresh(self) ‑> None`
    :   Toggle the auto-refresh flag and notify the user.

    `on_unmount(self) ‑> None`
    :   Clean up when screen is unmounted.

    `refresh_data(self) ‑> None`
    :   Override to define the refresh behaviour.
        
        This method is called automatically by the application's
        auto-refresh timer (see ``MadsciApp``). Subclasses should
        fetch and update their data here.

`ServiceURLMixin()`
:   Provides service URL resolution from the application context.
    
    Looks up service URLs from ``self.app.service_urls`` (set by
    :class:`MadsciApp`) and falls back to hardcoded defaults from
    :data:`DEFAULT_SERVICES`.
    
    Usage::
    
        class MyScreen(ServiceURLMixin, Screen):
            async def fetch_data(self):
                url = self.get_service_url("event_manager")
                client = MyClient(server_url=url)
                data = await client.async_get_data()

    ### Descendants

    * madsci.client.cli.tui.screens.dashboard.DashboardScreen
    * madsci.client.cli.tui.screens.data_browser.DataBrowserScreen
    * madsci.client.cli.tui.screens.experiments.ExperimentsScreen
    * madsci.client.cli.tui.screens.locations.LocationsScreen
    * madsci.client.cli.tui.screens.logs.LogsScreen
    * madsci.client.cli.tui.screens.nodes.NodesScreen
    * madsci.client.cli.tui.screens.resources.ResourcesScreen
    * madsci.client.cli.tui.screens.status.StatusScreen
    * madsci.client.cli.tui.screens.workflow_detail.WorkflowDetailScreen
    * madsci.client.cli.tui.screens.workflows.WorkflowsScreen

    ### Methods

    `get_service_url(self, service_name: str) ‑> str`
    :   Get the URL for a named service.
        
        Resolution order:
        1. ``self.app.service_urls`` (runtime configuration)
        2. :data:`DEFAULT_SERVICES` (compile-time defaults)
        
        Args:
            service_name: Service key, e.g. ``"event_manager"``.
        
        Returns:
            Base URL string for the service.