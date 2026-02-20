Module madsci.experiment_application.experiment_notebook
========================================================
ExperimentNotebook modality for Jupyter notebook experiments.

This module provides the ExperimentNotebook class, designed for interactive
experiment execution in Jupyter notebooks with rich output and cell-by-cell
execution support.

Classes
-------

`ExperimentNotebook(experiment_design: madsci.common.types.experiment_types.ExperimentDesign | str | pathlib.Path | None = None, experiment: madsci.common.types.experiment_types.Experiment | None = None, config: madsci.experiment_application.experiment_base.ExperimentBaseConfig | None = None, lab_server_url: str | pydantic.networks.AnyUrl | None = None, **kwargs: Any)`
:   Experiment modality for Jupyter notebooks.

    Provides notebook-friendly features like:
    - Rich display of results
    - Cell-based execution (start/end in separate cells)
    - Interactive status updates
    - Context manager support for simple cases

    The recommended pattern for notebooks is:
    1. Create experiment instance in one cell
    2. Call start() to begin the experiment
    3. Execute experiment steps in subsequent cells
    4. Call end() to complete the experiment

    Example (cell-by-cell):
        ```python
        # Cell 1: Setup
        from madsci.common.types.experiment_types import ExperimentDesign
        from madsci.experiment_application import ExperimentNotebook

        class MyExperiment(ExperimentNotebook):
            experiment_design = ExperimentDesign(
                experiment_name="Notebook Experiment"
            )

        exp = MyExperiment(lab_server_url="http://localhost:8000/")

        # Cell 2: Start
        exp.start()

        # Cell 3: Run workflow
        result = exp.run_workflow("synthesis")

        # Cell 4: Display results
        exp.display(result, title="Synthesis Results")

        # Cell 5: End
        exp.end()
        ```

    Example (context manager):
        ```python
        # All in one cell
        with MyExperiment() as exp:
            result = exp.run_workflow("synthesis")
            exp.display(result)
        ```

    Attributes:
        experiment_design: The design template for this experiment
        config: Notebook-specific configuration

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

    `display(self, data: Any, title: str | None = None) ‑> None`
    :   Display data in notebook-friendly format.

        Uses Rich for formatting when available and enabled.

        Args:
            data: Data to display (dict, list, or any object).
            title: Optional title for the display panel.

        Example:
            exp.display({"yield": 0.95, "purity": 0.99}, title="Results")

    `end(self, status: madsci.common.types.experiment_types.ExperimentStatus | None = None) ‑> madsci.experiment_application.experiment_notebook.ExperimentNotebook`
    :   End the experiment.

        Args:
            status: Final status (defaults to COMPLETED).

        Returns:
            Self for method chaining.

    `run_experiment(self, *args: Any, **kwargs: Any) ‑> Any`
    :   Not typically used in notebook modality.

        For notebooks, use the start()/end() pattern with run_workflow()
        calls in between. This method is provided for compatibility but
        notebooks typically don't use it directly.

        If you want to run a complete experiment in one cell, consider
        using ExperimentScript instead.

    `run_workflow(self, workflow_name: str, parameters: dict[str, typing.Any] | None = None, display_result: bool = True) ‑> Any`
    :   Run a workflow and optionally display results.

        Convenience method that wraps workcell_client.run_workflow()
        with notebook-friendly display.

        Args:
            workflow_name: Name of workflow to run.
            parameters: Workflow parameters.
            display_result: Whether to display result in notebook.

        Returns:
            Workflow result.

        Raises:
            RuntimeError: If experiment not started.

        Example:
            result = exp.run_workflow("synthesis", {"temperature": 25})

    `start(self, run_name: str | None = None, run_description: str | None = None) ‑> madsci.experiment_application.experiment_notebook.ExperimentNotebook`
    :   Start the experiment for notebook use.

        Unlike the context manager pattern, this allows cell-by-cell
        execution in notebooks. Call end() when finished.

        Args:
            run_name: Optional name for this run.
            run_description: Optional description for this run.

        Returns:
            Self for method chaining.

        Example:
            exp = MyExperiment()
            exp.start(run_name="Run 1")  # Returns self

`ExperimentNotebookConfig(**kwargs: Any)`
:   Configuration for notebook-based experiments.

    Extends ExperimentBaseConfig with notebook-specific display options.

    Initialize settings, optionally with a settings directory.

    When ``_settings_dir`` is provided (or ``MADSCI_SETTINGS_DIR`` is set),
    configuration file paths are resolved via walk-up discovery from that
    directory instead of the current working directory. Each filename walks
    up independently, so ``node.settings.yaml`` can resolve in the node dir
    while ``settings.yaml`` resolves in the lab root.

    Without either, existing CWD-relative behavior is preserved exactly.

    Args:
        _settings_dir: Starting directory for walk-up file discovery.
        **kwargs: Forwarded to ``BaseSettings.__init__``.

    ### Ancestors (in MRO)

    * madsci.experiment_application.experiment_base.ExperimentBaseConfig
    * madsci.common.types.base_types.MadsciBaseSettings
    * pydantic_settings.main.BaseSettings
    * pydantic.main.BaseModel

    ### Class variables

    `auto_display_results: bool`
    :

    `rich_output: bool`
    :
