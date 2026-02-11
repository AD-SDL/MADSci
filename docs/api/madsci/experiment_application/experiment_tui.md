Module madsci.experiment_application.experiment_tui
===================================================
ExperimentTUI modality for interactive terminal UI experiments.

This module provides the ExperimentTUI class, designed for interactive
experiment execution with a Textual-based terminal user interface.

Classes
-------

`ExperimentTUI(experiment_design: madsci.common.types.experiment_types.ExperimentDesign | str | pathlib.Path | None = None, experiment: madsci.common.types.experiment_types.Experiment | None = None, config: madsci.experiment_application.experiment_base.ExperimentBaseConfig | None = None, lab_server_url: str | pydantic.networks.AnyUrl | None = None, **kwargs: Any)`
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

    Initialize the experiment base.

    Args:
        experiment_design: Design for new experiments. Can be an ExperimentDesign
            instance or a path to a YAML file.
        experiment: Existing experiment to continue (optional).
        config: Configuration settings. If not provided, will be created
            from config_model with any kwargs as overrides.
        lab_server_url: Override for lab server URL. Takes precedence over
            config.lab_server_url.
        **kwargs: Additional configuration overrides passed to config_model.

    ### Ancestors (in MRO)

    * madsci.experiment_application.experiment_base.ExperimentBase
    * madsci.client.client_mixin.MadsciClientMixin

    ### Methods

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

`ExperimentTUIConfig(**values: Any)`
:   Configuration for TUI-based experiments.

    Extends ExperimentBaseConfig with TUI-specific options.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

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
