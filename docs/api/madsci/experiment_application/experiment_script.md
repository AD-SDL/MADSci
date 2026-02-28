Module madsci.experiment_application.experiment_script
======================================================
ExperimentScript modality for simple run-once experiments.

This module provides the ExperimentScript class, the simplest experiment
modality designed for experiments that run once from start to finish
without user interaction.

Classes
-------

`ExperimentScript(experiment_design: madsci.common.types.experiment_types.ExperimentDesign | str | pathlib.Path | None = None, experiment: madsci.common.types.experiment_types.Experiment | None = None, config: madsci.experiment_application.experiment_base.ExperimentBaseConfig | None = None, lab_server_url: str | pydantic.networks.AnyUrl | None = None, **kwargs: Any)`
:   Experiment modality for simple run-once scripts.

    This is the simplest experiment modality, designed for experiments
    that run once from start to finish without interaction. It provides
    a clean, minimal API for running experiments.

    The recommended pattern is to:
    1. Subclass ExperimentScript
    2. Set experiment_design as a class attribute
    3. Override run_experiment() with your experiment logic
    4. Call run() or main() to execute

    Example:
        ```python
        from madsci.common.types.experiment_types import ExperimentDesign
        from madsci.experiment_application import ExperimentScript

        class MyExperiment(ExperimentScript):
            experiment_design = ExperimentDesign(
                experiment_name="My Synthesis Experiment",
                experiment_description="Synthesize compound X"
            )

            def run_experiment(self):
                # Your experiment logic here
                result = self.workcell_client.run_workflow("synthesis")
                return {"yield": result.get("product_mass", 0)}

        if __name__ == "__main__":
            MyExperiment().run()
        ```

    Alternative using run_experiment directly:
        ```python
        class MyExperiment(ExperimentScript):
            experiment_design = ExperimentDesign(
                experiment_name="Parameterized Experiment"
            )

            def run_experiment(self, temperature: float, duration: int):
                # Parameterized experiment
                return self.workcell_client.run_workflow(
                    "synthesis",
                    parameters={"temp": temperature, "time": duration}
                )

        if __name__ == "__main__":
            # Pass parameters via run()
            MyExperiment().run(temperature=25.0, duration=60)

            # Or via config
            config = ExperimentScriptConfig(
                run_kwargs={"temperature": 25.0, "duration": 60}
            )
            MyExperiment(config=config).run()
        ```

    Attributes:
        experiment_design: The design template for this experiment
        config: Script-specific configuration

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

    ### Static methods

    `main(experiment_design: madsci.common.types.experiment_types.ExperimentDesign | None = None, lab_server_url: str | pydantic.networks.AnyUrl | None = None, *args: Any, **kwargs: Any) ‑> Any`
    :   Class method entry point for scripts.

        Convenience method for running experiments from __main__.
        Creates an instance and immediately runs the experiment.

        Args:
            experiment_design: Optional experiment design override.
            lab_server_url: Optional lab server URL override.
            *args: Positional arguments passed to run_experiment().
            **kwargs: Keyword arguments passed to run_experiment().

        Returns:
            Results from run_experiment().

        Example:
            ```python
            if __name__ == "__main__":
                MyExperiment.main()

            # With parameters
            if __name__ == "__main__":
                MyExperiment.main(sample_id="ABC123")
            ```

    ### Methods

    `run(self, *args: Any, **kwargs: Any) ‑> Any`
    :   Execute the experiment.

        This is the main entry point for script-based experiments.
        It wraps run_experiment() with automatic lifecycle management
        using the manage_experiment() context manager.

        Arguments passed to run() are merged with config.run_args and
        config.run_kwargs, with directly passed arguments taking precedence.

        Args:
            *args: Positional arguments passed to run_experiment().
            **kwargs: Keyword arguments passed to run_experiment().

        Returns:
            Results from run_experiment().

        Example:
            # Simple execution
            result = MyExperiment().run()

            # With parameters
            result = MyExperiment().run(sample_id="ABC123", cycles=5)

    `run_experiment(self, *args: Any, **kwargs: Any) ‑> Any`
    :   Override this method with your experiment logic.

        This method should contain the core experiment implementation.
        It is called within the manage_experiment() context, so:
        - The experiment is automatically started before this runs
        - The experiment is automatically ended after this completes
        - Exceptions are logged and the experiment marked as failed

        Args:
            *args: Positional arguments (from config.run_args or run()).
            **kwargs: Keyword arguments (from config.run_kwargs or run()).

        Returns:
            Experiment results. The format is up to you, but returning
            a dictionary is recommended for easy serialization.

        Example:
            ```python
            def run_experiment(self, sample_id: str, cycles: int = 1):
                results = []
                for i in range(cycles):
                    result = self.workcell_client.run_workflow(
                        "process_sample",
                        parameters={"sample_id": sample_id, "cycle": i}
                    )
                    results.append(result)
                return {"sample_id": sample_id, "results": results}
            ```

`ExperimentScriptConfig(**kwargs: Any)`
:   Configuration for script-based experiments.

    Extends ExperimentBaseConfig with options for passing arguments
    to the run_experiment method.

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

    `run_args: list[typing.Any]`
    :

    `run_kwargs: dict[str, typing.Any]`
    :
