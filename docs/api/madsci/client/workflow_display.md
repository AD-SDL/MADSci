Module madsci.client.workflow_display
=====================================
Rich workflow status display for terminal, Jupyter, and plain text environments.

Provides a WorkflowDisplay class that renders workflow progress with automatic
environment detection and in-place updates.

Classes
-------

`WorkflowDisplay(mode: DisplayMode = 'auto')`
:   Renders workflow progress with Rich Live, Jupyter HTML, or plain text.
    
    Parameters
    ----------
    mode : DisplayMode
        Display backend. "auto" detects the environment automatically.
    
    Initialize the display with the given mode.

    ### Instance variables

    `mode: Literal['rich', 'jupyter', 'plain']`
    :   The resolved display mode.

    ### Methods

    `format_error_prompt(self, wf: Workflow) ‑> str`
    :   Build a formatted error prompt string for user input.

    `start(self) ‑> None`
    :   Begin the live display (Rich) or prepare the display handle (Jupyter).

    `stop(self, wf: Workflow) ‑> None`
    :   Finalize the display and clean up resources.

    `update(self, wf: Workflow) ‑> None`
    :   Update the display with the current workflow state.