Module madsci.client.cli.tui.screens.workflows
==============================================
Workflow visualization screen for MADSci TUI.

Provides workflow monitoring with step progress visualization,
active/queued workflow display, workflow control actions, filtering,
and step detail inspection.

Classes
-------

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

    `on_action_bar_action_triggered(self, event: madsci.client.cli.tui.widgets.action_bar.ActionBar.ActionTriggered) ‑> None`
    :   Route ActionBar button triggers to screen actions.

    `on_data_table_row_selected(self, event: textual.widgets._data_table.DataTable.RowSelected) ‑> None`
    :   Handle row selection — push workflow detail screen.

    `on_filter_bar_filter_changed(self, event: madsci.client.cli.tui.widgets.filter_bar.FilterBar.FilterChanged) ‑> None`
    :   Handle filter changes from the FilterBar.
        
        Args:
            event: The filter changed event with search and filters.

    `on_mount(self) ‑> None`
    :   Handle screen mount - set up tables and load data.

    `refresh_data(self) ‑> None`
    :   Refresh workflow data from workcell manager.