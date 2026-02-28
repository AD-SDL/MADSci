Module madsci.experiment_application
====================================
Experiment Application framework for MADSci.

This module provides various experiment modalities for running MADSci experiments:

- **ExperimentScript**: Simple run-once experiments (scripts)
- **ExperimentNotebook**: Jupyter notebook-friendly experiments
- **ExperimentTUI**: Interactive terminal UI experiments
- **ExperimentNode**: REST server mode experiments
- **ExperimentBase**: Base class for custom modalities

The legacy ExperimentApplication is deprecated and will be removed in v0.8.0.
Use one of the specific modalities instead.

Example:
    ```python
    from madsci.experiment_application import ExperimentScript
    from madsci.common.types.experiment_types import ExperimentDesign

    class MyExperiment(ExperimentScript):
        experiment_design = ExperimentDesign(
            experiment_name="My Experiment"
        )

        def run_experiment(self):
            result = self.workcell_client.run_workflow("synthesis")
            return result

    if __name__ == "__main__":
        MyExperiment().run()
    ```

Sub-modules
-----------
* madsci.experiment_application.experiment_application
* madsci.experiment_application.experiment_base
* madsci.experiment_application.experiment_node
* madsci.experiment_application.experiment_notebook
* madsci.experiment_application.experiment_script
* madsci.experiment_application.experiment_tui
* madsci.experiment_application.tui

Classes
-------

`ExperimentApplication(lab_server_url: str | pydantic.networks.AnyUrl | None = None, experiment_design: madsci.common.types.experiment_types.ExperimentDesign | str | pathlib.Path | None = None, experiment: madsci.common.types.experiment_types.Experiment | None = None, *args: Any, **kwargs: Any)`
:   An experiment application that helps manage the execution of an experiment.

    You can either use this class as a base class for your own application class,
    or create an instance of it to manage the execution of an experiment.

    This class extends AbstractNode (via RestNode) and inherits client management
    from MadsciClientMixin. In addition to the standard node clients (event, resource, data),
    it also uses experiment, workcell, location, and optionally lab clients.

    Initialize the experiment application.

    .. deprecated:: 0.7.0
        ExperimentApplication is deprecated. Use ExperimentScript,
        ExperimentNotebook, ExperimentTUI, or ExperimentNode instead.

    You can provide an experiment design to use for creating new experiments,
    or an existing experiment to continue.

    Note: Client initialization is handled by the parent AbstractNode class
    via MadsciClientMixin. All manager clients (experiment, workcell, location,
    data, resource) are available as properties and will be lazily initialized
    when first accessed.

    ### Ancestors (in MRO)

    * madsci.node_module.rest_node_module.RestNode
    * madsci.node_module.abstract_node_module.AbstractNode
    * madsci.client.client_mixin.MadsciClientMixin

    ### Class variables

    `OPTIONAL_CLIENTS: ClassVar[list[str]]`
    :

    `experiment: madsci.common.types.experiment_types.Experiment | None`
    :   The current experiment being run.

    `experiment_design: madsci.common.types.experiment_types.ExperimentDesign | str | pathlib.Path | None`
    :   The design of the experiment.

    ### Static methods

    `continue_experiment(experiment: madsci.common.types.experiment_types.Experiment, lab_server_url: str | pydantic.networks.AnyUrl | None = None) ‑> madsci.experiment_application.experiment_application.ExperimentApplication`
    :   Create a new experiment application with an existing experiment.

    `start_new(lab_server_url: str | pydantic.networks.AnyUrl | None = None, experiment_design: madsci.common.types.experiment_types.ExperimentDesign | None = None) ‑> madsci.experiment_application.experiment_application.ExperimentApplication`
    :   Create a new experiment application with a new experiment.

    ### Methods

    `add_experiment_management(self, func: Callable[~P, ~R]) ‑> Callable[~P, ~R]`
    :   wraps the run experiment function while preserving arguments

    `cancel_experiment(self) ‑> None`
    :   Cancel the experiment.

    `check_experiment_status(self) ‑> None`
    :   Update and check the status of the current experiment.

        Raises an exception if the experiment has been cancelled or failed.
        If the experiment has been paused, this function will wait until the experiment is resumed.

        Raises:
            ExperimentCancelledError: If the experiment has been cancelled.
            ExperimentFailedError: If the experiment has failed.

    `check_resource_field(self, resource: madsci.common.types.resource_types.Resource, condition: madsci.common.types.condition_types.Condition) ‑> bool`
    :   check if a resource meets a condition

    `end_experiment(self, status: madsci.common.types.experiment_types.ExperimentStatus | None = None) ‑> None`
    :   End the experiment.

    `evaluate_condition(self, condition: madsci.common.types.condition_types.Condition) ‑> bool`
    :   evaluate a condition

    `fail_experiment(self) ‑> None`
    :   Mark an experiment as failed.

    `get_location_from_condition(self, condition: madsci.common.types.condition_types.Condition) ‑> madsci.common.types.location_types.Location`
    :   get the location referenced by a condition

    `get_resource_from_condition(self, condition: madsci.common.types.condition_types.Condition) ‑> madsci.common.types.resource_types.Resource | None`
    :   gets a resource from a condition

    `handle_exception(self, exception: Exception) ‑> None`
    :   Exception handler that makes experiment fail by default, can be overwritten

    `loop(self) ‑> None`
    :   Function that runs the experimental loop. This should be overridden by subclasses.

    `manage_experiment(self, run_name: str | None = None, run_description: str | None = None) ‑> Generator[None, None, None]`
    :   Context manager to start and end an experiment with full context propagation.

        All logging within this experiment run will include the experiment
        context, enabling hierarchical log filtering and analysis.

    `pause_experiment(self) ‑> None`
    :   Pause the experiment.

    `resource_at_key(self, resource: madsci.common.types.resource_types.Resource, condition: madsci.common.types.condition_types.Condition) ‑> bool`
    :   return if a resource is in a location at condition.key

    `run_experiment(self, *args: Any, **kwargs: Any) ‑> Any`
    :   The main experiment function, overwrite for each app

    `start_app(self) ‑> None`
    :   Starts the application, either as a node or in single run mode

    `start_experiment_run(self, run_name: str | None = None, run_description: str | None = None) ‑> None`
    :   Sends the ExperimentDesign to the server to register a new experimental run.

`ExperimentApplicationConfig(**kwargs: Any)`
:   Configuration for the ExperimentApplication.

    This class is used to define the configuration for the ExperimentApplication node.
    It can be extended to add custom configurations.

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

    * madsci.common.types.node_types.RestNodeConfig
    * madsci.common.types.node_types.NodeConfig
    * madsci.common.types.base_types.MadsciBaseSettings
    * pydantic_settings.main.BaseSettings
    * pydantic.main.BaseModel

    ### Class variables

    `lab_server_url: str | pydantic.networks.AnyUrl | None`
    :   The URL of the lab server to connect to.

    `run_args: list[typing.Any]`
    :   Arguments to pass to the run_experiment function when not running in server mode.

    `run_kwargs: dict[str, typing.Any]`
    :   Keyword arguments to pass to the run_experiment function when not running in server mode.

    `server_mode: bool`
    :   Whether the application should start a REST Server acting as a MADSci node or not.

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

    `config: madsci.experiment_application.experiment_base.ExperimentBaseConfig | None`
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

`ExperimentBaseConfig(**kwargs: Any)`
:   Base configuration for all experiment modalities.

    Contains only experiment-relevant settings, not server/node settings.
    This is intentionally simpler than the full RestNodeConfig used by
    the legacy ExperimentApplication.

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

    `max_pause_wait: float | None`
    :

    `resource_server_url: pydantic.networks.AnyUrl | None`
    :

    `workcell_server_url: pydantic.networks.AnyUrl | None`
    :

`ExperimentNode(experiment_design: madsci.common.types.experiment_types.ExperimentDesign | str | pathlib.Path | None = None, experiment: madsci.common.types.experiment_types.Experiment | None = None, config: madsci.experiment_application.experiment_node.ExperimentNodeConfig | None = None, lab_server_url: str | pydantic.networks.AnyUrl | None = None, **kwargs: Any)`
:   Experiment modality that runs as a REST node.

    This modality exposes the experiment as a REST API, allowing it to be
    controlled by the workcell manager like any other node. This is useful
    for experiments that need to be triggered remotely or integrated into
    automated workflows.

    The experiment's run_experiment() method is exposed as a node action
    that can be called via the REST API.

    Example:
        ```python
        from madsci.common.types.experiment_types import ExperimentDesign
        from madsci.experiment_application import ExperimentNode

        class MyExperiment(ExperimentNode):
            experiment_design = ExperimentDesign(
                experiment_name="Server Experiment"
            )

            def run_experiment(self, sample_id: str, temperature: float = 25.0):
                # Called via REST API: POST /actions/run_experiment
                result = self.workcell_client.run_workflow(
                    "process_sample",
                    parameters={"sample_id": sample_id, "temp": temperature}
                )
                return result

        if __name__ == "__main__":
            MyExperiment().start_server()
        ```

    Attributes:
        experiment_design: The design template for this experiment
        config: Node-specific configuration

    Initialize the experiment node.

    Args:
        experiment_design: Design for new experiments.
        experiment: Existing experiment to continue.
        config: Configuration settings.
        lab_server_url: Override for lab server URL.
        **kwargs: Additional configuration overrides.

    ### Ancestors (in MRO)

    * madsci.experiment_application.experiment_base.ExperimentBase
    * madsci.client.client_mixin.MadsciClientMixin

    ### Methods

    `run(self) ‑> None`
    :   Alias for start_server() for consistency with other modalities.

    `run_experiment(self, *args: Any, **kwargs: Any) ‑> Any`
    :   Override this method with your experiment logic.

        This method is exposed as a REST API action. When called via
        the API, the experiment lifecycle is automatically managed:
        - Experiment is started before run_experiment executes
        - Experiment is ended after run_experiment completes
        - Exceptions are logged and experiment marked as failed

        The method signature (parameters) will be exposed in the API,
        so clients can pass parameters as JSON in the request body.

        Args:
            *args: Positional arguments from API request.
            **kwargs: Keyword arguments from API request.

        Returns:
            Experiment results (will be serialized to JSON in response).

        Example:
            ```python
            def run_experiment(
                self,
                sample_id: str,
                temperature: float = 25.0,
                cycles: int = 1
            ) -> dict:
                results = []
                for i in range(cycles):
                    result = self.workcell_client.run_workflow(
                        "process_sample",
                        parameters={
                            "sample_id": sample_id,
                            "temperature": temperature,
                            "cycle": i
                        }
                    )
                    results.append(result)
                return {
                    "sample_id": sample_id,
                    "cycles_completed": cycles,
                    "results": results
                }
            ```

    `start_server(self) ‑> None`
    :   Start the REST server for this experiment.

        The server exposes run_experiment as an action that can be
        called by the workcell manager or any HTTP client.

        The server runs until interrupted (Ctrl+C) or shut down.

`ExperimentNodeConfig(**kwargs: Any)`
:   Configuration for node-based experiments (server mode).

    Extends ExperimentBaseConfig with REST server settings.

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

    `cors_enabled: bool`
    :

    `cors_origins: list[str]`
    :

    `node_name: str | None`
    :

    `server_host: str`
    :

    `server_port: int`
    :

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

    `auto_display_results: bool`
    :

    `rich_output: bool`
    :

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
