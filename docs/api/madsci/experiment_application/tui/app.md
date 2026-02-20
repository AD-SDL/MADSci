Module madsci.experiment_application.tui.app
============================================
Textual TUI application for running experiments.

This module provides the ExperimentTUIApp class, a Textual application
for interactive experiment control.

Note: This module requires the `textual` package to be installed.
Install with: `pip install madsci[tui]` or `pip install textual`

Classes
-------

`ExperimentTUIApp(experiment: ExperimentTUI, *args: Any, **kwargs: Any)`
:   Textual application for experiment control.

    Provides an interactive TUI for:
    - Starting/stopping experiments
    - Viewing experiment status
    - Monitoring logs
    - Pausing/resuming experiments

    This is a basic implementation. Advanced features will be added
    in future releases.

    Initialize the TUI application.

    Args:
        experiment: The ExperimentTUI instance to control.
        *args: Additional arguments for Textual App.
        **kwargs: Additional keyword arguments for Textual App.

    ### Ancestors (in MRO)

    * textual.app.App
    * typing.Generic
    * textual.dom.DOMNode
    * textual.message_pump.MessagePump

    ### Class variables

    `BINDINGS: ClassVar[list]`
    :

    `CSS`
    :

    ### Methods

    `action_cancel(self) ‑> None`
    :   Cancel the experiment.

    `action_pause(self) ‑> None`
    :   Pause or resume the experiment.

    `action_refresh(self) ‑> None`
    :   Refresh the status display.

    `action_start(self) ‑> None`
    :   Start the experiment.

        Launches the experiment as a background task so the TUI remains
        responsive to pause/cancel/quit interactions while it runs.

    `compose(self) ‑> Iterable[textual.widget.Widget]`
    :   Compose the TUI layout.

    `on_button_pressed(self, event: Any) ‑> None`
    :   Handle button presses.
