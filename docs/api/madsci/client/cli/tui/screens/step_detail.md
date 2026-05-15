Module madsci.client.cli.tui.screens.step_detail
================================================
Step detail screen for MADSci TUI.

Provides a detailed view of a single workflow step, pushed on top of
the WorkflowsScreen when a step row is selected.

Classes
-------

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