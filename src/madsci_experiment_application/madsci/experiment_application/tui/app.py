"""Textual TUI application for running experiments.

This module provides the ExperimentTUIApp class, a Textual application
for interactive experiment control.

Note: This module requires the `textual` package to be installed.
Install with: `pip install madsci[tui]` or `pip install textual`
"""

import asyncio
from typing import TYPE_CHECKING, Any, ClassVar, Optional

from madsci.common.exceptions import ExperimentCancelledError

try:
    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.containers import Container, Horizontal
    from textual.widgets import Button, Footer, Header, Log, Static

    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False
    # Provide stubs for type checking
    App = object  # type: ignore[misc, assignment]
    ComposeResult = Any  # type: ignore[misc, assignment]

if TYPE_CHECKING:
    from madsci.experiment_application.experiment_tui import ExperimentTUI


class ExperimentTUIApp(App if TEXTUAL_AVAILABLE else object):  # type: ignore[misc]
    """Textual application for experiment control.

    Provides an interactive TUI for:
    - Starting/stopping experiments
    - Viewing experiment status
    - Monitoring logs
    - Pausing/resuming experiments

    This is a basic implementation. Advanced features will be added
    in future releases.
    """

    CSS = """
    Screen {
        layout: grid;
        grid-size: 2;
        grid-gutter: 1 2;
    }

    #status-panel {
        column-span: 2;
        height: 8;
        border: solid green;
        padding: 1 2;
    }

    #log-panel {
        column-span: 2;
        height: 1fr;
        border: solid blue;
    }

    #control-panel {
        column-span: 2;
        height: 5;
        layout: horizontal;
        padding: 1;
    }

    Button {
        margin: 0 1;
    }
    """

    BINDINGS: ClassVar[list] = [
        Binding("q", "quit", "Quit"),
        Binding("s", "start", "Start"),
        Binding("p", "pause", "Pause/Resume"),
        Binding("c", "cancel", "Cancel"),
        Binding("r", "refresh", "Refresh"),
    ]

    def __init__(
        self,
        experiment: "ExperimentTUI",
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Initialize the TUI application.

        Args:
            experiment: The ExperimentTUI instance to control.
            *args: Additional arguments for Textual App.
            **kwargs: Additional keyword arguments for Textual App.
        """
        if not TEXTUAL_AVAILABLE:
            raise ImportError(
                "textual is required for TUI support. "
                "Install with: pip install madsci[tui] or pip install textual"
            )

        super().__init__(*args, **kwargs)
        self.experiment = experiment
        self._is_running = False
        self._is_cancelled = False
        self._result: Optional[Any] = None
        self._status_timer: Optional[Any] = None
        self._experiment_task: Optional[asyncio.Task] = None

    def compose(self) -> ComposeResult:
        """Compose the TUI layout."""
        yield Header()

        # Status panel
        yield Container(
            Static(self._get_status_text(), id="status-text"),
            id="status-panel",
        )

        # Log panel
        yield Container(
            Log(id="log-widget"),
            id="log-panel",
        )

        # Control panel
        yield Container(
            Horizontal(
                Button("Start", id="start-btn", variant="success"),
                Button("Pause", id="pause-btn", variant="warning"),
                Button("Cancel", id="cancel-btn", variant="error"),
                Button("Quit", id="quit-btn"),
            ),
            id="control-panel",
        )

        yield Footer()

    def _get_status_text(self) -> str:
        """Get current status text."""
        experiment_name = (
            self.experiment.experiment_design.experiment_name
            if self.experiment.experiment_design
            else "Unknown"
        )
        status = "Not Started"
        if self._is_cancelled:
            status = "Cancelled"
        elif self._is_running and self.experiment.is_pause_requested:
            status = "Paused"
        elif self._is_running:
            status = "Running"
        elif self.experiment.experiment:
            status = self.experiment.experiment.status.value

        experiment_id = (
            self.experiment.experiment.experiment_id
            if self.experiment.experiment
            else "N/A"
        )

        return f"Experiment: {experiment_name}\nStatus: {status}\nID: {experiment_id}"

    def _log(self, message: str) -> None:
        """Add a message to the log."""
        log_widget = self.query_one("#log-widget", Log)
        log_widget.write_line(message)

    def _update_status(self) -> None:
        """Update the status display and button labels."""
        status_text = self.query_one("#status-text", Static)
        status_text.update(self._get_status_text())
        pause_btn = self.query_one("#pause-btn", Button)
        pause_btn.label = "Resume" if self.experiment.is_pause_requested else "Pause"

    async def action_start(self) -> None:
        """Start the experiment.

        Launches the experiment as a background task so the TUI remains
        responsive to pause/cancel/quit interactions while it runs.
        """
        if self._is_running:
            self._log("Experiment already running")
            return

        # Reset pause/cancel events from any previous run
        self.experiment.reset_events()
        self._is_cancelled = False

        self._is_running = True
        self._update_status()
        self._log("Starting experiment...")

        # Periodically refresh status while running so the ID and status
        # are visible as soon as the experiment manager assigns them.
        refresh_interval = getattr(self.experiment.config, "refresh_interval", 1.0)
        self._status_timer = self.set_interval(refresh_interval, self._update_status)

        # Launch experiment as a background task so this handler returns
        # immediately and the TUI stays responsive to other actions.
        self._experiment_task = asyncio.create_task(self._run_experiment_task())

    async def _run_experiment_task(self) -> None:
        """Background task that runs the experiment and updates the TUI on completion."""
        try:
            self._result = await self._run_experiment_in_thread()
            self._log("Experiment completed successfully")
        except asyncio.CancelledError:
            self._log("Experiment cancelled")
        except ExperimentCancelledError:
            self._log("Experiment cancelled")
        except Exception as e:
            self._log(f"Experiment failed: {e}")
        finally:
            self._is_running = False
            if self._status_timer is not None:
                self._status_timer.stop()
                self._status_timer = None
            self._update_status()

    async def _run_experiment_in_thread(self) -> Any:
        """Run the experiment in a thread to avoid blocking the event loop."""
        loop = asyncio.get_event_loop()

        def run_sync() -> Any:
            with self.experiment.manage_experiment():
                return self.experiment.run_experiment()

        return await loop.run_in_executor(None, run_sync)

    async def action_pause(self) -> None:
        """Pause or resume the experiment."""
        if not self._is_running:
            self._log("No experiment running")
            return

        if self.experiment.is_pause_requested:
            self._log("Resuming experiment...")
            self.experiment.request_resume()
        else:
            self._log("Pausing experiment...")
            self.experiment.request_pause()
        self._update_status()

    async def action_cancel(self) -> None:
        """Cancel the experiment."""
        if not self._is_running:
            self._log("No experiment running")
            return

        self._log("Cancelling experiment...")
        self._is_cancelled = True
        # Set the cancel event so the experiment thread exits at the next
        # check_experiment_status() call.
        self.experiment.request_cancel()
        # Also cancel the asyncio task so the TUI stops waiting immediately,
        # even if the thread is blocked in a long-running call.
        if self._experiment_task is not None:
            self._experiment_task.cancel()

    def action_refresh(self) -> None:
        """Refresh the status display."""
        self._update_status()
        self._log("Status refreshed")

    async def on_button_pressed(self, event: Any) -> None:
        """Handle button presses."""
        button_id = event.button.id
        if button_id == "start-btn":
            await self.action_start()
        elif button_id == "pause-btn":
            await self.action_pause()
        elif button_id == "cancel-btn":
            await self.action_cancel()
        elif button_id == "quit-btn":
            self.exit(self._result)
