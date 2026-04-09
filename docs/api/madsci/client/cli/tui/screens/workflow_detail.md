Module madsci.client.cli.tui.screens.workflow_detail
====================================================
Workflow detail screen for MADSci TUI.

Pushed screen showing workflow details, step progress, and control actions.
Opened when a workflow row is selected in :class:`WorkflowsScreen`.

Classes
-------

`WorkflowDetailScreen(workflow_id: str, workflow_data: Workflow, **kwargs: Any)`
:   Screen showing details for a single workflow, pushed on top of WorkflowsScreen.
    
    Initialize the detail screen.
    
    Args:
        workflow_id: Workflow ID.
        workflow_data: Workflow model instance.

    ### Ancestors (in MRO)

    * madsci.client.cli.tui.mixins.ActionBarMixin
    * madsci.client.cli.tui.mixins.ServiceURLMixin
    * textual.screen.Screen
    * typing.Generic
    * textual.widget.Widget
    * textual.dom.DOMNode
    * textual.message_pump.MessagePump

    ### Class variables

    `BINDINGS: ClassVar[list[BindingType]]`
    :

    `can_focus`
    :

    `can_focus_children`
    :

    ### Methods

    `action_cancel_workflow(self) ‑> None`
    :   Cancel this workflow.

    `action_go_back(self) ‑> None`
    :   Go back to the workflows list.

    `action_pause_workflow(self) ‑> None`
    :   Pause this workflow.

    `action_refresh(self) ‑> None`
    :   Re-fetch workflow data and re-render.

    `action_resubmit_workflow(self) ‑> None`
    :   Resubmit this workflow.

    `action_resume_workflow(self) ‑> None`
    :   Resume this workflow.

    `action_retry_workflow(self) ‑> None`
    :   Retry this workflow.

    `compose(self) ‑> Iterable[textual.widget.Widget]`
    :   Compose the detail screen layout.

    `on_data_table_row_selected(self, event: DataTable.RowSelected) ‑> None`
    :   Handle step row selection -- push step detail screen.

    `on_mount(self) ‑> None`
    :   Set up the steps table and render content.