Module madsci.experiment_application.experiment_tui
===================================================
ExperimentTUI modality for interactive terminal UI experiments.

This module provides the ExperimentTUI class, designed for interactive
experiment execution with a Textual-based terminal user interface.

Classes
-------

`ExperimentTUI(*args: Any, **kwargs: Any)`
:   Experiment modality with interactive terminal UI.

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

    Initialize with thread-safe pause/cancel events.

    ### Ancestors (in MRO)

    * madsci.experiment_application.experiment_base.ExperimentBase
    * madsci.client.client_mixin.MadsciClientMixin

    ### Instance variables

    `is_pause_requested: bool`
    :   Check if a pause has been requested.

    ### Methods

    `check_experiment_status(self) ‑> None`
    :   Check experiment status using in-process events.

        Overrides the base class to use thread-safe events for direct
        communication between the TUI and the experiment thread, avoiding
        the need for a server round-trip.

        When paused, blocks until resumed or cancelled.

        Raises:
            ExperimentCancelledError: If cancel was requested from the TUI.

    `request_cancel(self) ‑> None`
    :   Request the experiment to cancel (thread-safe, called from TUI).

    `request_pause(self) ‑> None`
    :   Request the experiment to pause (thread-safe, called from TUI).

    `request_resume(self) ‑> None`
    :   Request the experiment to resume (thread-safe, called from TUI).

    `reset_events(self) ‑> None`
    :   Clear pause and cancel events for a fresh experiment run.

    `run(self) ‑> Any`
    :   Alias for run_tui() for consistency with other modalities.

        Returns:
            Experiment results after TUI exits.

    `run_experiment(self, *args: Any, **kwargs: Any) ‑> Any`
    :   Override this method with your experiment logic.

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

    `run_tui(self) ‑> Any`
    :   Launch the TUI for this experiment.

        This starts the Textual application with experiment controls.
        The TUI will handle starting, monitoring, and stopping the experiment.

        Returns:
            Experiment results after TUI exits.

        Raises:
            ImportError: If textual is not installed.

`ExperimentTUIConfig(**kwargs: Any)`
:   Configuration for TUI-based experiments.

    Extends ExperimentBaseConfig with TUI-specific options.

    Initialize settings with walk-up file discovery.

    Configuration file paths (YAML, JSON, TOML, .env) are resolved via
    walk-up discovery from a starting directory. Each filename walks up
    independently, so ``node.settings.yaml`` can resolve in the node dir
    while ``settings.yaml`` resolves in the lab root.

    The starting directory is determined by (in priority order):
    1. ``_settings_dir`` keyword argument
    2. ``MADSCI_SETTINGS_DIR`` environment variable
    3. Current working directory (default)

    Args:
        _settings_dir: Starting directory for walk-up file discovery.
        **kwargs: Forwarded to ``BaseSettings.__init__``.

    ### Ancestors (in MRO)

    * madsci.experiment_application.experiment_base.ExperimentBaseConfig
    * madsci.common.types.base_types.MadsciBaseSettings
    * pydantic_settings.main.BaseSettings
    * pydantic.main.BaseModel

    ### Class variables

    `refresh_interval: float`
    :

    `show_logs: bool`
    :
