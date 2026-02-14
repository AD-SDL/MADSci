Module madsci.client.cli.tui.screens.workflows
==============================================
Workflow visualization screen for MADSci TUI.

Provides workflow monitoring with step progress visualization,
active/queued workflow display, and workflow control actions.

Classes
-------

`WorkflowDetailPanel(**kwargs: Any)`
:   Panel showing details for a selected workflow.

    Initialize the panel.

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

    `update_details(self, workflow_id: str, data: dict) ‑> None`
    :   Update the detail display.

        Args:
            workflow_id: Workflow ID.
            data: Workflow data dictionary.

`WorkflowsScreen(**kwargs: Any)`
:   Screen showing workflow visualization and management.

    Initialize the screen.

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

    `action_cancel_workflow(self) ‑> None`
    :   Cancel the selected workflow.

    `action_go_back(self) ‑> None`
    :   Go back to the previous screen.

    `action_pause_workflow(self) ‑> None`
    :   Pause the selected workflow.

    `action_refresh(self) ‑> None`
    :   Refresh workflow data.

    `action_resume_workflow(self) ‑> None`
    :   Resume the selected workflow.

    `action_toggle_auto_refresh(self) ‑> None`
    :   Toggle auto-refresh on/off.

    `compose(self) ‑> Iterable[textual.widget.Widget]`
    :   Compose the workflows screen layout.

    `on_data_table_row_selected(self, event: textual.widgets._data_table.DataTable.RowSelected) ‑> None`
    :   Handle row selection in the workflows table.

    `on_mount(self) ‑> None`
    :   Handle screen mount - set up tables and load data.

    `refresh_data(self) ‑> None`
    :   Refresh workflow data from workcell manager.
