"""ExperimentTUI modality for interactive terminal UI experiments.

This module provides the ExperimentTUI class, designed for interactive
experiment execution with a Textual-based terminal user interface.
"""

import threading
import time
from typing import Any, ClassVar

from madsci.experiment_application.experiment_base import (
    ExperimentBase,
    ExperimentBaseConfig,
    ExperimentCancelledError,
)
from pydantic import Field


class ExperimentTUIConfig(ExperimentBaseConfig):
    """Configuration for TUI-based experiments.

    Extends ExperimentBaseConfig with TUI-specific options.
    """

    refresh_interval: float = Field(
        default=1.0,
        title="Refresh Interval",
        description="Status refresh interval in seconds.",
    )
    show_logs: bool = Field(
        default=True,
        title="Show Logs",
        description="Show log panel in TUI.",
    )


class ExperimentTUI(ExperimentBase):
    """Experiment modality with interactive terminal UI.

    Provides a Textual-based TUI for experiment control with:
    - Status display
    - Log viewer
    - Action controls
    - Real-time updates

    Note: This modality requires the `textual` package to be installed.
    Install with: `pip install madsci[tui]` or `pip install textual`

    Example:
        ```python
        from madsci.common.types.experiment_types import ExperimentDesign
        from madsci.experiment_application import ExperimentTUI

        class MyExperiment(ExperimentTUI):
            experiment_design = ExperimentDesign(
                experiment_name="Interactive Experiment"
            )

            def run_experiment(self):
                # Your experiment logic
                for step in range(10):
                    self.check_experiment_status()  # Allow pause/cancel
                    result = self.workcell_client.run_workflow(
                        "step",
                        parameters={"step_num": step}
                    )
                return {"steps_completed": 10}

        if __name__ == "__main__":
            MyExperiment().run_tui()
        ```

    Attributes:
        experiment_design: The design template for this experiment
        config: TUI-specific configuration
    """

    config: ExperimentTUIConfig  # type: ignore[assignment]
    config_model: ClassVar[type[ExperimentTUIConfig]] = ExperimentTUIConfig

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize with thread-safe pause/cancel events."""
        super().__init__(*args, **kwargs)
        self._pause_event = threading.Event()
        self._cancel_event = threading.Event()

    def request_pause(self) -> None:
        """Request the experiment to pause (thread-safe, called from TUI)."""
        self._pause_event.set()

    def request_resume(self) -> None:
        """Request the experiment to resume (thread-safe, called from TUI)."""
        self._pause_event.clear()

    def request_cancel(self) -> None:
        """Request the experiment to cancel (thread-safe, called from TUI)."""
        self._cancel_event.set()

    def reset_events(self) -> None:
        """Clear pause and cancel events for a fresh experiment run."""
        self._pause_event.clear()
        self._cancel_event.clear()

    @property
    def is_pause_requested(self) -> bool:
        """Check if a pause has been requested."""
        return self._pause_event.is_set()

    def check_experiment_status(self) -> None:
        """Check experiment status using in-process events.

        Overrides the base class to use thread-safe events for direct
        communication between the TUI and the experiment thread, avoiding
        the need for a server round-trip.

        When paused, blocks until resumed or cancelled.

        Raises:
            ExperimentCancelledError: If cancel was requested from the TUI.
        """
        if self._cancel_event.is_set():
            raise ExperimentCancelledError("Experiment cancelled from TUI.")

        while self._pause_event.is_set():
            if self._cancel_event.is_set():
                raise ExperimentCancelledError(
                    "Experiment cancelled from TUI while paused."
                )
            time.sleep(0.5)

    def run_tui(self) -> Any:
        """Launch the TUI for this experiment.

        This starts the Textual application with experiment controls.
        The TUI will handle starting, monitoring, and stopping the experiment.

        Returns:
            Experiment results after TUI exits.

        Raises:
            ImportError: If textual is not installed.
        """
        try:
            # Textual is an optional dependency - import locally
            from madsci.experiment_application.tui import (  # noqa: PLC0415
                ExperimentTUIApp,
            )
        except ImportError as e:
            raise ImportError(
                "TUI support requires textual. "
                "Install with: pip install madsci[tui] or pip install textual"
            ) from e

        app = ExperimentTUIApp(experiment=self)
        return app.run()

    def run(self) -> Any:
        """Alias for run_tui() for consistency with other modalities.

        Returns:
            Experiment results after TUI exits.
        """
        return self.run_tui()

    def run_experiment(self, *args: Any, **kwargs: Any) -> Any:
        """Override this method with your experiment logic.

        This method is called by the TUI when the user starts the experiment.
        It should contain the core experiment implementation.

        For long-running experiments, call check_experiment_status()
        periodically to respond to user pause/cancel requests.

        Args:
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
            Experiment results.

        Example:
            ```python
            def run_experiment(self):
                results = []
                for i in range(100):
                    self.check_experiment_status()  # Handle pause/cancel
                    result = self.workcell_client.run_workflow("step")
                    results.append(result)
                return {"iterations": len(results), "results": results}
            ```
        """
        raise NotImplementedError(
            "Subclasses must implement run_experiment() with experiment logic"
        )
