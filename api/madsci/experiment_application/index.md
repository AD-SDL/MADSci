Module madsci.experiment_application
====================================
Experiment Application framework for MADSci.

Sub-modules
-----------
* madsci.experiment_application.experiment_application

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

    `manage_experiment(self, run_name: str | None = None, run_description: str | None = None) ‑> <function contextmanager at 0x7ffbaf9dd800>`
    :   Context manager to start and end an experiment.

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

`ExperimentApplicationConfig(**values: Any)`
:   Configuration for the ExperimentApplication.

    This class is used to define the configuration for the ExperimentApplication node.
    It can be extended to add custom configurations.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

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
