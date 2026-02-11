Module madsci.experiment_application.experiment_base
====================================================
Base class for all experiment modalities.

This module provides the ExperimentBase class, which contains the core
experiment lifecycle management functionality shared across all experiment
modalities (Script, Notebook, TUI, Node).

The key design principle is composition over inheritance: ExperimentBase
uses MadsciClientMixin for client management rather than inheriting from
RestNode, making it lighter weight for non-server use cases.

Classes
-------

`ExperimentBase(experiment_design: madsci.common.types.experiment_types.ExperimentDesign | str | pathlib.Path | None = None, experiment: madsci.common.types.experiment_types.Experiment | None = None, config: madsci.experiment_application.experiment_base.ExperimentBaseConfig | None = None, lab_server_url: str | pydantic.networks.AnyUrl | None = None, **kwargs: Any)`
:   Base class for all experiment modalities.

    Provides core experiment lifecycle management using composition rather
    than inheritance from RestNode. All manager clients are available via
    the MadsciClientMixin.

    This is the foundation class that ExperimentScript, ExperimentNotebook,
    ExperimentTUI, and ExperimentNode all inherit from.

    Subclasses should:
    1. Set `experiment_design` class attribute or pass in __init__
    2. Override `run_experiment()` with experiment logic
    3. Use `manage_experiment()` context manager for automatic lifecycle

    Example:
        class MyExperiment(ExperimentBase):
            experiment_design = ExperimentDesign(
                experiment_name="My Experiment",
                experiment_description="A simple experiment"
            )

            def run_experiment(self):
                with self.manage_experiment():
                    result = self.workcell_client.run_workflow("my_workflow")
                    return result

    Attributes:
        experiment_design: The design template for this experiment
        experiment: The current experiment instance (set after start_experiment_run)
        config: Configuration settings for this experiment

    Client Properties (inherited from MadsciClientMixin):
        event_client: EventClient for logging
        experiment_client: ExperimentClient for experiment management
        workcell_client: WorkcellClient for workflow execution
        data_client: DataClient for data storage
        resource_client: ResourceClient for inventory
        location_client: LocationClient for locations
        lab_client: LabClient for lab configuration

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

    * madsci.client.client_mixin.MadsciClientMixin

    ### Descendants

    * madsci.experiment_application.experiment_node.ExperimentNode
    * madsci.experiment_application.experiment_notebook.ExperimentNotebook
    * madsci.experiment_application.experiment_script.ExperimentScript
    * madsci.experiment_application.experiment_tui.ExperimentTUI

    ### Class variables

    `OPTIONAL_CLIENTS: ClassVar[list[str]]`
    :

    `config: madsci.experiment_application.experiment_base.ExperimentBaseConfig`
    :   Configuration for this experiment.

    `config_model: ClassVar[type[madsci.experiment_application.experiment_base.ExperimentBaseConfig]]`
    :   The Pydantic model class for configuration.

    `experiment: madsci.common.types.experiment_types.Experiment | None`
    :   The current experiment instance (populated after start_experiment_run).

    `experiment_design: madsci.common.types.experiment_types.ExperimentDesign | str | pathlib.Path | None`
    :   The design template for this experiment.

    ### Static methods

    `continue_experiment(experiment: madsci.common.types.experiment_types.Experiment, lab_server_url: str | pydantic.networks.AnyUrl | None = None, **kwargs: Any) ‑> madsci.experiment_application.experiment_base.ExperimentBase`
    :   Create an instance to continue an existing experiment.

        Args:
            experiment: The existing Experiment to continue.
            lab_server_url: URL of the lab server.
            **kwargs: Additional arguments passed to __init__.

        Returns:
            A new ExperimentBase instance attached to the existing experiment.

    `start_new(experiment_design: madsci.common.types.experiment_types.ExperimentDesign | None = None, lab_server_url: str | pydantic.networks.AnyUrl | None = None, **kwargs: Any) ‑> madsci.experiment_application.experiment_base.ExperimentBase`
    :   Create a new experiment instance and start a run.

        Convenience class method that creates an instance and immediately
        starts an experiment run.

        Args:
            experiment_design: The experiment design to use.
            lab_server_url: URL of the lab server.
            **kwargs: Additional arguments passed to __init__.

        Returns:
            A new ExperimentBase instance with an active experiment run.

    ### Instance variables

    `is_running: bool`
    :   Check if an experiment is currently running.

        Returns:
            True if an experiment is active and in progress.

    `logger: madsci.client.event_client.EventClient`
    :   Alias for event_client for logging convenience.

        Returns:
            The EventClient instance for logging.

    ### Methods

    `cancel_experiment(self) ‑> madsci.common.types.experiment_types.Experiment | None`
    :   Cancel the current experiment.

        Returns:
            The updated Experiment object, or None if no experiment is active.

    `check_experiment_status(self) ‑> None`
    :   Check current experiment status and handle state changes.

        This method polls the experiment manager for the current status
        and handles various states:
        - PAUSED: Waits until resumed
        - CANCELLED: Raises ExperimentCancelledError
        - FAILED: Raises ExperimentFailedError

        Call this periodically in long-running experiments to respond
        to external status changes (e.g., user cancellation via UI).

        Raises:
            ExperimentCancelledError: If the experiment was cancelled externally.
            ExperimentFailedError: If the experiment failed externally.

    `end_experiment(self, status: madsci.common.types.experiment_types.ExperimentStatus | None = None) ‑> madsci.common.types.experiment_types.Experiment | None`
    :   End the current experiment run.

        Args:
            status: Final status for the experiment. Defaults to COMPLETED.

        Returns:
            The updated Experiment object, or None if no experiment is active.

    `fail_experiment(self) ‑> madsci.common.types.experiment_types.Experiment | None`
    :   Mark the current experiment as failed.

        Returns:
            The updated Experiment object, or None if no experiment is active.

    `handle_exception(self, exception: Exception) ‑> None`
    :   Handle an exception during experiment execution.

        This method is called when an exception occurs within
        manage_experiment(). Override this method for custom exception
        handling behavior.

        The default implementation logs the error and marks the experiment
        as failed.

        Args:
            exception: The exception that occurred.

    `manage_experiment(self, run_name: str | None = None, run_description: str | None = None) ‑> Generator[madsci.experiment_application.experiment_base.ExperimentBase, None, None]`
    :   Context manager for experiment lifecycle.

        Automatically starts the experiment run on entry and ends it on exit.
        Exceptions are caught, logged, and the experiment is marked as failed.

        This is the recommended way to run experiments as it ensures proper
        lifecycle management and context propagation for logging.

        Args:
            run_name: Optional name for this run.
            run_description: Optional description for this run.

        Yields:
            Self, for method chaining within the context.

        Example:
            with self.manage_experiment(run_name="Run 1") as exp:
                result = exp.workcell_client.run_workflow("synthesis")
                # Experiment automatically ends on exit

    `pause_experiment(self) ‑> madsci.common.types.experiment_types.Experiment | None`
    :   Pause the current experiment.

        Returns:
            The updated Experiment object, or None if no experiment is active.

    `run_experiment(self, *args: Any, **kwargs: Any) ‑> Any`
    :   Override this method with experiment logic.

        This method should contain the core experiment implementation.
        It will be called by modality-specific entry points.

        Args:
            *args: Positional arguments (modality-specific).
            **kwargs: Keyword arguments (modality-specific).

        Returns:
            Experiment results (format depends on experiment).

        Raises:
            NotImplementedError: If not overridden by subclass.

    `start_experiment_run(self, run_name: str | None = None, run_description: str | None = None) ‑> madsci.common.types.experiment_types.Experiment`
    :   Start a new experiment run.

        Registers the experiment with the Experiment Manager and returns
        the created Experiment object. This sets self.experiment to the
        newly created experiment.

        Args:
            run_name: Optional name for this specific run.
            run_description: Optional description for this run.

        Returns:
            The created Experiment object.

        Raises:
            ValueError: If experiment_design is not set.
            TypeError: If experiment_design is not an ExperimentDesign instance.

`ExperimentBaseConfig(**values: Any)`
:   Base configuration for all experiment modalities.

    Contains only experiment-relevant settings, not server/node settings.
    This is intentionally simpler than the full RestNodeConfig used by
    the legacy ExperimentApplication.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseSettings
    * pydantic_settings.main.BaseSettings
    * pydantic.main.BaseModel

    ### Descendants

    * madsci.experiment_application.experiment_node.ExperimentNodeConfig
    * madsci.experiment_application.experiment_notebook.ExperimentNotebookConfig
    * madsci.experiment_application.experiment_script.ExperimentScriptConfig
    * madsci.experiment_application.experiment_tui.ExperimentTUIConfig

    ### Class variables

    `data_server_url: pydantic.networks.AnyUrl | None`
    :

    `event_server_url: pydantic.networks.AnyUrl | None`
    :

    `experiment_server_url: pydantic.networks.AnyUrl | None`
    :

    `lab_server_url: pydantic.networks.AnyUrl | None`
    :

    `location_server_url: pydantic.networks.AnyUrl | None`
    :

    `resource_server_url: pydantic.networks.AnyUrl | None`
    :

    `workcell_server_url: pydantic.networks.AnyUrl | None`
    :
