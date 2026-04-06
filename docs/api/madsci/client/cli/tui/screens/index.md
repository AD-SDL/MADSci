Module madsci.client.cli.tui.screens
====================================
TUI screens for MADSci.

This module contains the screen implementations for the MADSci TUI.

Sub-modules
-----------
* madsci.client.cli.tui.screens.action_executor
* madsci.client.cli.tui.screens.dashboard
* madsci.client.cli.tui.screens.data_browser
* madsci.client.cli.tui.screens.event_analytics
* madsci.client.cli.tui.screens.experiments
* madsci.client.cli.tui.screens.locations
* madsci.client.cli.tui.screens.logs
* madsci.client.cli.tui.screens.new_wizard
* madsci.client.cli.tui.screens.nodes
* madsci.client.cli.tui.screens.resource_tree
* madsci.client.cli.tui.screens.resources
* madsci.client.cli.tui.screens.status
* madsci.client.cli.tui.screens.step_detail
* madsci.client.cli.tui.screens.transfer_graph
* madsci.client.cli.tui.screens.workflows

Classes
-------

`ActionExecutorScreen(node_name: str, node_url: str, actions: dict[str, typing.Any], **kwargs: Any)`
:   Interactive action execution on a node.
    
    Allows the user to select an action from a dropdown, provide JSON
    arguments, execute the action, and view the result in a detail panel.
    
    Initialize the action executor screen.
    
    Args:
        node_name: Name of the target node.
        node_url: Base URL of the target node.
        actions: Dict mapping action names to action definitions.
        **kwargs: Additional keyword arguments forwarded to Screen.

    ### Ancestors (in MRO)

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

    `action_go_back(self) ‑> None`
    :   Go back to the nodes screen.

    `compose(self) ‑> Iterable[textual.widget.Widget]`
    :   Compose the action executor layout.

    `on_button_pressed(self, event: textual.widgets._button.Button.Pressed) ‑> None`
    :   Handle button press events.
        
        Args:
            event: The button pressed event.

    `on_select_changed(self, event: textual.widgets._select.Select.Changed) ‑> None`
    :   Update description when action selection changes.
        
        Args:
            event: The select changed event.

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

`DataBrowserScreen(**kwargs: Any)`
:   Screen showing data browser with type-aware detail display.
    
    Initialize the screen.

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

    `action_go_back(self) ‑> None`
    :   Go back to the dashboard.

    `action_refresh(self) ‑> None`
    :   Refresh data.

    `compose(self) ‑> Iterable[textual.widget.Widget]`
    :   Compose the data browser screen layout.

    `on_data_table_row_selected(self, event: textual.widgets._data_table.DataTable.RowSelected) ‑> None`
    :   Handle row selection in the data table.
        
        Args:
            event: The row selected event.

    `on_filter_bar_filter_changed(self, event: madsci.client.cli.tui.widgets.filter_bar.FilterBar.FilterChanged) ‑> None`
    :   Handle filter changes from the FilterBar.
        
        Args:
            event: The filter changed event with search and filters.

    `on_mount(self) ‑> None`
    :   Handle screen mount - set up table and load data.

    `refresh_data(self) ‑> None`
    :   Refresh datapoint data from the data manager.

`EventAnalyticsScreen(**kwargs: Any)`
:   Screen showing event analytics and utilization summaries.
    
    Initialize the screen.

    ### Ancestors (in MRO)

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

    `action_go_back(self) ‑> None`
    :   Go back to the dashboard.

    `action_refresh(self) ‑> None`
    :   Refresh analytics data.

    `compose(self) ‑> Iterable[textual.widget.Widget]`
    :   Compose the event analytics screen layout.

    `on_mount(self) ‑> None`
    :   Handle screen mount - set up tables and load data.

    `refresh_data(self) ‑> None`
    :   Refresh analytics data from the event manager.

`ExperimentsScreen(**kwargs: Any)`
:   Screen showing experiment management and monitoring.
    
    Initialize the screen.

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

    `action_cancel_experiment(self) ‑> None`
    :   Cancel the selected experiment.

    `action_continue_experiment(self) ‑> None`
    :   Continue the selected experiment.

    `action_go_back(self) ‑> None`
    :   Go back to the dashboard.

    `action_pause_experiment(self) ‑> None`
    :   Pause the selected experiment.

    `action_refresh(self) ‑> None`
    :   Refresh experiment data.

    `compose(self) ‑> Iterable[textual.widget.Widget]`
    :   Compose the experiments screen layout.

    `on_data_table_row_selected(self, event: textual.widgets._data_table.DataTable.RowSelected) ‑> None`
    :   Handle row selection in the experiments table.
        
        Args:
            event: The row selected event.

    `on_filter_bar_filter_changed(self, event: madsci.client.cli.tui.widgets.filter_bar.FilterBar.FilterChanged) ‑> None`
    :   Handle filter changes from the FilterBar.
        
        Args:
            event: The filter changed event with search and filters.

    `on_mount(self) ‑> None`
    :   Handle screen mount - set up table and load data.

    `refresh_data(self) ‑> None`
    :   Refresh experiment data from the experiment manager.

`LocationsScreen(**kwargs: Any)`
:   Screen showing location inventory and management.
    
    Initialize the screen.

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

    `action_go_back(self) ‑> None`
    :   Go back to the dashboard.

    `action_refresh(self) ‑> None`
    :   Refresh location data.

    `action_show_transfer_graph(self) ‑> None`
    :   Show the transfer graph screen.

    `compose(self) ‑> Iterable[textual.widget.Widget]`
    :   Compose the locations screen layout.

    `on_data_table_row_selected(self, event: textual.widgets._data_table.DataTable.RowSelected) ‑> None`
    :   Handle row selection in the locations table.
        
        Args:
            event: The row selected event.

    `on_filter_bar_filter_changed(self, event: madsci.client.cli.tui.widgets.filter_bar.FilterBar.FilterChanged) ‑> None`
    :   Handle filter changes from the FilterBar.
        
        Args:
            event: The filter changed event with search and filters.

    `on_mount(self) ‑> None`
    :   Handle screen mount - set up table and load data.

    `refresh_data(self) ‑> None`
    :   Refresh location data from the location manager.

`LogsScreen(**kwargs: Any)`
:   Screen for viewing logs.
    
    Initialize the screen.

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

    `on_filter_bar_filter_changed(self, event: madsci.client.cli.tui.widgets.filter_bar.FilterBar.FilterChanged) ‑> None`
    :   Handle filter changes from FilterBar.

    `on_mount(self) ‑> None`
    :   Handle screen mount - load initial logs.

    `refresh_data(self) ‑> None`
    :   Fetch and display logs.

`NodesScreen(**kwargs: Any)`
:   Screen showing node management and monitoring.
    
    Initialize the screen.

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

    `action_execute_action(self) ‑> None`
    :   Open the action executor screen for the selected node.

    `action_go_back(self) ‑> None`
    :   Go back to the previous screen.

    `action_pause_node(self) ‑> None`
    :   Pause the selected node.

    `action_refresh(self) ‑> None`
    :   Refresh node data.

    `action_reset_node(self) ‑> None`
    :   Reset the selected node (clear errors).

    `action_resume_node(self) ‑> None`
    :   Resume the selected node.

    `action_toggle_lock_node(self) ‑> None`
    :   Toggle lock/unlock on the selected node.

    `compose(self) ‑> Iterable[textual.widget.Widget]`
    :   Compose the nodes screen layout.

    `on_data_table_row_selected(self, event: textual.widgets._data_table.DataTable.RowSelected) ‑> None`
    :   Handle row selection - push detail screen.

    `on_mount(self) ‑> None`
    :   Handle screen mount - set up table and load data.

    `refresh_data(self) ‑> None`
    :   Refresh node data from workcell manager.

`ResourceTreeScreen(resource_id: str, resource_url: str, **kwargs: Any)`
:   Screen showing the resource hierarchy as a tree.
    
    Initialize the resource tree screen.
    
    Args:
        resource_id: ID of the resource to display hierarchy for.
        resource_url: Base URL of the resource manager.
        **kwargs: Additional keyword arguments forwarded to Screen.

    ### Ancestors (in MRO)

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

    `action_go_back(self) ‑> None`
    :   Go back to the resources screen.

    `compose(self) ‑> Iterable[textual.widget.Widget]`
    :   Compose the tree screen layout.

    `on_mount(self) ‑> None`
    :   Handle mount - fetch hierarchy and build tree.

`ResourcesScreen(**kwargs: Any)`
:   Screen showing resource inventory and management.
    
    Initialize the screen.

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

    `action_delete_resource(self) ‑> None`
    :   Delete the selected resource.

    `action_go_back(self) ‑> None`
    :   Go back to the dashboard.

    `action_new_resource(self) ‑> None`
    :   Notify user to use CLI for resource creation.

    `action_refresh(self) ‑> None`
    :   Refresh resource data.

    `action_show_tree(self) ‑> None`
    :   Show the resource tree for the selected resource.

    `action_toggle_lock(self) ‑> None`
    :   Toggle lock on the selected resource.

    `compose(self) ‑> Iterable[textual.widget.Widget]`
    :   Compose the resources screen layout.

    `on_data_table_row_selected(self, event: textual.widgets._data_table.DataTable.RowSelected) ‑> None`
    :   Handle row selection in the resources table.
        
        Args:
            event: The row selected event.

    `on_filter_bar_filter_changed(self, event: madsci.client.cli.tui.widgets.filter_bar.FilterBar.FilterChanged) ‑> None`
    :   Handle filter changes from the FilterBar.
        
        Args:
            event: The filter changed event with search and filters.

    `on_mount(self) ‑> None`
    :   Handle screen mount - set up table and load data.

    `refresh_data(self) ‑> None`
    :   Refresh resource data from the resource manager.

`StatusScreen(**kwargs: Any)`
:   Screen showing detailed service status.
    
    Initialize the screen.

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

    `action_go_back(self) ‑> None`
    :   Go back to the previous screen.

    `action_refresh(self) ‑> None`
    :   Refresh status data.

    `compose(self) ‑> Iterable[textual.widget.Widget]`
    :   Compose the status screen layout.

    `on_data_table_row_selected(self, event: textual.widgets._data_table.DataTable.RowSelected) ‑> None`
    :   Handle row selection in the table.

    `on_mount(self) ‑> None`
    :   Handle screen mount - set up tables and load data.

    `refresh_data(self) ‑> None`
    :   Refresh all service statuses.

`StepDetailScreen(workflow_id: str, step_data: dict, step_index: int, **kwargs: Any)`
:   Detailed view of a single workflow step.
    
    Initialize the step detail screen.
    
    Args:
        workflow_id: Parent workflow ID.
        step_data: Step data dictionary.
        step_index: Zero-based index of this step within the workflow.
        **kwargs: Additional keyword arguments forwarded to Screen.

    ### Ancestors (in MRO)

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

    `action_go_back(self) ‑> None`
    :   Go back to the workflows screen.

    `compose(self) ‑> Iterable[textual.widget.Widget]`
    :   Compose the step detail screen layout.

    `on_mount(self) ‑> None`
    :   Render the step detail content on mount.

`TransferGraphScreen(location_url: str, **kwargs: Any)`
:   Screen showing the transfer adjacency graph.
    
    Initialize the transfer graph screen.
    
    Args:
        location_url: Base URL of the location manager.
        **kwargs: Additional keyword arguments forwarded to Screen.

    ### Ancestors (in MRO)

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

    `action_go_back(self) ‑> None`
    :   Go back to the locations screen.

    `action_refresh(self) ‑> None`
    :   Refresh the transfer graph.

    `compose(self) ‑> Iterable[textual.widget.Widget]`
    :   Compose the transfer graph screen layout.

    `on_mount(self) ‑> None`
    :   Handle mount - set up table and fetch graph data.

`WorkflowsScreen(**kwargs: Any)`
:   Screen showing workflow visualization and management.
    
    Initialize the screen.

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

    `action_cancel_workflow(self) ‑> None`
    :   Cancel the selected workflow.

    `action_go_back(self) ‑> None`
    :   Go back to the previous screen.

    `action_pause_workflow(self) ‑> None`
    :   Pause the selected workflow.

    `action_refresh(self) ‑> None`
    :   Refresh workflow data.

    `action_resubmit_workflow(self) ‑> None`
    :   Resubmit the selected workflow as a new run.

    `action_resume_workflow(self) ‑> None`
    :   Resume the selected workflow.

    `action_retry_workflow(self) ‑> None`
    :   Retry the selected workflow from the beginning.

    `compose(self) ‑> Iterable[textual.widget.Widget]`
    :   Compose the workflows screen layout.

    `on_data_table_row_selected(self, event: textual.widgets._data_table.DataTable.RowSelected) ‑> None`
    :   Handle row selection in the workflows or steps table.

    `on_filter_bar_filter_changed(self, event: madsci.client.cli.tui.widgets.filter_bar.FilterBar.FilterChanged) ‑> None`
    :   Handle filter changes from the FilterBar.
        
        Args:
            event: The filter changed event with search and filters.

    `on_mount(self) ‑> None`
    :   Handle screen mount - set up tables and load data.

    `refresh_data(self) ‑> None`
    :   Refresh workflow data from workcell manager.