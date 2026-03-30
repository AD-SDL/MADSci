"""Provides an ExperimentApplication class that manages the execution of an experiment.

.. deprecated:: 0.7.0
    ExperimentApplication is deprecated. Use ExperimentScript, ExperimentNotebook,
    ExperimentTUI, or ExperimentNode instead depending on your use case.
    ExperimentApplication will be removed in v0.8.0.

    Migration guide:
    - For simple scripts: Use ExperimentScript
    - For Jupyter notebooks: Use ExperimentNotebook
    - For interactive terminal: Use ExperimentTUI
    - For server mode: Use ExperimentNode

    See https://ad-sdl.github.io/MADSci/migration/experiment-modalities for details.
"""

import time
import warnings
from contextlib import contextmanager
from functools import wraps
from pathlib import Path
from typing import Any, Callable, ClassVar, Generator, Optional, TypeVar, Union

from madsci.common.context import (
    event_client_context,
    set_current_madsci_context,
)
from madsci.common.exceptions import ExperimentCancelledError, ExperimentFailedError
from madsci.common.ownership import ownership_context
from madsci.common.types.base_types import PathLike
from madsci.common.types.condition_types import Condition
from madsci.common.types.event_types import EventType
from madsci.common.types.experiment_types import (
    Experiment,
    ExperimentDesign,
    ExperimentStatus,
)
from madsci.common.types.location_types import Location
from madsci.common.types.node_types import RestNodeConfig
from madsci.common.types.resource_types import Resource
from madsci.common.utils import threaded_daemon
from madsci.experiment_application.experiment_base import (
    _EXPERIMENT_OWNERSHIP_FIELDS,
    clear_experiment_ownership,
    set_experiment_ownership,
)
from madsci.node_module.rest_node_module import RestNode
from pydantic import AnyUrl, Field
from rich import print
from typing_extensions import ParamSpec  # type: ignore

P = ParamSpec("P")
R = TypeVar("R")


class ExperimentApplicationConfig(
    RestNodeConfig,
    env_file=(".env", "experiment.env"),
    toml_file=("settings.toml", "experiment.settings.toml"),
    yaml_file=("settings.yaml", "experiment.settings.yaml"),
    json_file=("settings.json", "experiment.settings.json"),
    env_prefix="EXPERIMENT_",
):
    """
    Configuration for the ExperimentApplication.

    This class is used to define the configuration for the ExperimentApplication node.
    It can be extended to add custom configurations.
    """

    server_mode: bool = False
    """Whether the application should start a REST Server acting as a MADSci node or not."""
    lab_server_url: Optional[Union[str, AnyUrl]] = None
    """The URL of the lab server to connect to."""
    run_args: list[Any] = Field(default_factory=list)
    """Arguments to pass to the run_experiment function when not running in server mode."""
    run_kwargs: dict[str, Any] = Field(default_factory=dict)
    """Keyword arguments to pass to the run_experiment function when not running in server mode."""


class ExperimentApplication(RestNode):
    """
    An experiment application that helps manage the execution of an experiment.

    You can either use this class as a base class for your own application class,
    or create an instance of it to manage the execution of an experiment.

    This class extends AbstractNode (via RestNode) and inherits client management
    from MadsciClientMixin. In addition to the standard node clients (event, resource, data),
    it also uses experiment, workcell, location, and optionally lab clients.
    """

    # Extend the required clients from AbstractNode to include experiment-specific clients
    OPTIONAL_CLIENTS: ClassVar[list[str]] = [
        "experiment",
        "workcell",
        "location",
        "lab",
    ]

    # Experiment-specific attributes
    experiment: Optional[Experiment] = None
    """The current experiment being run."""
    experiment_design: Optional[Union[ExperimentDesign, PathLike]] = None
    """The design of the experiment."""

    # Configuration
    config: ExperimentApplicationConfig = ExperimentApplicationConfig()
    """Configuration for the ExperimentApplication."""
    config_model = ExperimentApplicationConfig
    """The Pydantic model for the configuration of the ExperimentApplication."""

    # Note: All client properties (event_client, experiment_client, workcell_client,
    # location_client, data_client, resource_client, lab_client, logger) are inherited
    # from AbstractNode via MadsciClientMixin and are available as properties with
    # lazy initialization. They do not need to be redeclared here.

    def __init__(
        self,
        lab_server_url: Optional[Union[str, AnyUrl]] = None,
        experiment_design: Optional[Union[str, Path, ExperimentDesign]] = None,
        experiment: Optional[Experiment] = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """
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
        """
        warnings.warn(
            "ExperimentApplication is deprecated and will be removed in v0.8.0. "
            "Use ExperimentScript (for scripts), ExperimentNotebook (for notebooks), "
            "ExperimentTUI (for interactive TUI), or ExperimentNode (for server mode) instead. "
            "See https://ad-sdl.github.io/MADSci/migration/experiment-modalities for migration guide.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(*args, **kwargs)

        # Setup lab client and context if provided
        lab_server_url = lab_server_url or self.config.lab_server_url
        if lab_server_url:
            self.lab_server_url = lab_server_url
            set_current_madsci_context(self.lab_client.get_lab_context())
            self.setup_clients()

        # Setup experiment design
        self.experiment_design = experiment_design or self.experiment_design
        if isinstance(self.experiment_design, (str, Path)):
            self.experiment_design = ExperimentDesign.from_yaml(self.experiment_design)

        self.experiment = experiment or self.experiment

        # Note: All clients (experiment_client, workcell_client, location_client,
        # data_client, resource_client, event_client) are inherited from AbstractNode
        # via MadsciClientMixin and will be initialized lazily when accessed

    @classmethod
    def start_new(
        cls,
        lab_server_url: Optional[Union[str, AnyUrl]] = None,
        experiment_design: Optional[ExperimentDesign] = None,
    ) -> "ExperimentApplication":
        """Create a new experiment application with a new experiment."""
        self = cls(
            lab_server_url=lab_server_url,
            experiment_design=experiment_design,
        )
        self.start_experiment_run()
        return self

    @classmethod
    def continue_experiment(
        cls,
        experiment: Experiment,
        lab_server_url: Optional[Union[str, AnyUrl]] = None,
    ) -> "ExperimentApplication":
        """Create a new experiment application with an existing experiment."""
        self = cls(lab_server_url=lab_server_url, experiment=experiment)
        self.experiment_client.continue_experiment(
            experiment_id=experiment.experiment_id
        )
        return self

    def start_experiment_run(
        self, run_name: Optional[str] = None, run_description: Optional[str] = None
    ) -> None:
        """Sends the ExperimentDesign to the server to register a new experimental run."""

        if self.experiment_design is None:
            raise ValueError(
                "experiment_design is required to start a new experiment run"
            )

        if not isinstance(self.experiment_design, ExperimentDesign):
            raise TypeError(
                "experiment_design must be an ExperimentDesign instance (or a path/string that can be loaded to one)"
            )

        self.experiment = self.experiment_client.start_experiment(
            experiment_design=self.experiment_design,
            run_name=run_name,
            run_description=run_description,
        )
        self.logger.info(
            "Experiment run started",
            event_type=EventType.EXPERIMENT_START,
            experiment_id=self.experiment.experiment_id,
            run_name=self.experiment.run_name,
            experiment_name=self.experiment.experiment_design.experiment_name,
        )
        set_experiment_ownership(self.experiment)

        passed_checks = False
        while not passed_checks:
            passed_checks = True
            for condition in self.experiment_design.resource_conditions:
                passed = self.evaluate_condition(condition)
                passed_checks = passed_checks and passed
                print(f"Check {condition.condition_name}: {passed}")
            if not passed_checks:
                val = input("Check failed, retry?")
                if val == "n":
                    break

    def end_experiment(self, status: Optional[ExperimentStatus] = None) -> None:
        """End the experiment."""
        self.experiment = self.experiment_client.end_experiment(
            experiment_id=self.experiment.experiment_id,
            status=status,
        )
        event_type = (
            EventType.EXPERIMENT_COMPLETE
            if status in {None, ExperimentStatus.COMPLETED}
            else EventType.EXPERIMENT_FAILED
            if status == ExperimentStatus.FAILED
            else EventType.EXPERIMENT_COMPLETE
        )
        self.logger.info(
            "Experiment run ended",
            event_type=event_type,
            experiment_id=self.experiment.experiment_id,
            run_name=self.experiment.run_name,
            experiment_name=self.experiment.experiment_design.experiment_name,
            status=str(status) if status is not None else None,
        )

        clear_experiment_ownership()

    def pause_experiment(self) -> None:
        """Pause the experiment."""
        self.experiment = self.experiment_client.pause_experiment(
            experiment_id=self.experiment.experiment_id
        )
        self.logger.info(
            "Experiment run paused",
            event_type=EventType.EXPERIMENT_PAUSE,
            experiment_id=self.experiment.experiment_id,
            run_name=self.experiment.run_name,
            experiment_name=self.experiment.experiment_design.experiment_name,
        )

    def cancel_experiment(self) -> None:
        """Cancel the experiment."""
        self.experiment = self.experiment_client.cancel_experiment(
            experiment_id=self.experiment.experiment_id
        )
        self.logger.info(
            "Experiment run cancelled",
            event_type=EventType.EXPERIMENT_CANCELLED,
            experiment_id=self.experiment.experiment_id,
            run_name=self.experiment.run_name,
            experiment_name=self.experiment.experiment_design.experiment_name,
        )

    def fail_experiment(self) -> None:
        """Mark an experiment as failed."""
        self.experiment = self.experiment_client.end_experiment(
            experiment_id=self.experiment.experiment_id,
            status=ExperimentStatus.FAILED,
        )
        self.logger.info(
            "Experiment run failed",
            event_type=EventType.EXPERIMENT_FAILED,
            experiment_id=self.experiment.experiment_id,
            run_name=self.experiment.run_name,
            experiment_name=self.experiment.experiment_design.experiment_name,
        )

    def handle_exception(self, exception: Exception) -> None:
        """Exception handler that makes experiment fail by default, can be overwritten"""
        self.logger.error(
            "Experiment run raised exception",
            event_type=EventType.EXPERIMENT_FAILED,
            experiment_id=self.experiment.experiment_id if self.experiment else None,
            run_name=self.experiment.run_name if self.experiment else None,
            experiment_name=(
                self.experiment.experiment_design.experiment_name
                if self.experiment
                else None
            ),
            error=str(exception),
        )
        self.end_experiment(ExperimentStatus.FAILED)

    @contextmanager
    def manage_experiment(
        self, run_name: Optional[str] = None, run_description: Optional[str] = None
    ) -> Generator[None, None, None]:
        """
        Context manager to start and end an experiment with full context propagation.

        All logging within this experiment run will include the experiment
        context, enabling hierarchical log filtering and analysis.
        """
        self.start_experiment_run(run_name=run_name, run_description=run_description)

        # Establish experiment context for hierarchical logging and ownership tracking
        experiment_id = self.experiment.experiment_id if self.experiment else None
        experiment_name = (
            self.experiment.experiment_design.experiment_name
            if self.experiment and self.experiment.experiment_design
            else None
        )

        # Build ownership overrides from the experiment's ownership info,
        # restricted to experiment-level fields only
        ownership_overrides: dict = {}
        if experiment_id:
            ownership_overrides["experiment_id"] = experiment_id
        if self.experiment and self.experiment.ownership_info:
            for field in _EXPERIMENT_OWNERSHIP_FIELDS:
                value = getattr(self.experiment.ownership_info, field, None)
                if value is not None and field not in ownership_overrides:
                    ownership_overrides[field] = value

        with (
            ownership_context(**ownership_overrides),
            event_client_context(
                name="experiment",
                experiment_id=experiment_id,
                experiment_name=experiment_name,
                run_name=run_name,
                experiment_type=self.__class__.__name__,
            ),
        ):
            try:
                yield
            except Exception as e:
                self.handle_exception(e)
                raise (e)
            else:
                self.end_experiment()

    @threaded_daemon
    def loop(self) -> None:
        """Function that runs the experimental loop. This should be overridden by subclasses."""
        raise NotImplementedError

    def check_experiment_status(self) -> None:
        """
        Update and check the status of the current experiment.

        Raises an exception if the experiment has been cancelled or failed.
        If the experiment has been paused, this function will wait until the experiment is resumed.

        Raises:
            ExperimentCancelledError: If the experiment has been cancelled.
            ExperimentFailedError: If the experiment has failed.
        """
        self.experiment = self.experiment_client.get_experiment(
            experiment_id=self.experiment.experiment_id
        )
        exception = None
        if self.experiment.status == ExperimentStatus.PAUSED:
            self.logger.warning(
                "Experiment run paused; waiting for resume",
                event_type=EventType.EXPERIMENT_PAUSE,
                experiment_id=self.experiment.experiment_id,
                experiment_name=self.experiment.experiment_design.experiment_name,
            )
            while True:
                time.sleep(5)
                self.experiment = self.experiment_client.get_experiment(
                    experiment_id=self.experiment.experiment_id
                )
                if self.experiment.status != ExperimentStatus.PAUSED:
                    break
        if self.experiment.status == ExperimentStatus.CANCELLED:
            exception = ExperimentCancelledError(
                "Experiment manager reports that the experiment has been cancelled."
            )
        elif self.experiment.status == ExperimentStatus.FAILED:
            exception = ExperimentFailedError(
                "Experiment manager reports that the experiment has failed."
            )

        if exception:
            self.logger.error(
                "Experiment run terminated",
                event_type=(
                    EventType.EXPERIMENT_CANCELLED
                    if isinstance(exception, ExperimentCancelledError)
                    else EventType.EXPERIMENT_FAILED
                ),
                experiment_id=self.experiment.experiment_id,
                experiment_name=self.experiment.experiment_design.experiment_name,
                error=exception.message,
            )
            raise exception

    def get_resource_from_condition(self, condition: Condition) -> Optional[Resource]:
        """gets a resource from a condition"""
        resource = None
        if condition.resource_id:
            resource = self.resource_client.get_resource(condition.resource_id)
        elif condition.resource_name:
            resource = self.resource_client.query_resource(
                resource_name=condition.resource_name, multiple=False
            )
        if resource is None:
            raise (Exception("Invalid Identifier for Resource"))
        return resource

    def check_resource_field(self, resource: Resource, condition: Condition) -> bool:
        """check if a resource meets a condition"""
        if condition.operator == "is_greater_than":
            return getattr(resource, condition.field) > condition.target_value
        if condition.operator == "is_less_than":
            return getattr(resource, condition.field) < condition.target_value
        if condition.operator == "is_equal_to":
            return getattr(resource, condition.field) == condition.target_value
        if condition.operator == "is_greater_than_or_equal_to":
            return getattr(resource, condition.field) >= condition.target_value
        if condition.operator == "is_less_than_or_equal_to":
            return getattr(resource, condition.field) <= condition.target_value
        return False

    def get_location_from_condition(self, condition: Condition) -> Location:
        """get the location referenced by a condition"""
        location = None
        if condition.location_name:
            locations = self.location_client.get_locations()
            location = next(
                (
                    location
                    for location in locations
                    if location.name == condition.location_name
                ),
                None,
            )
        elif condition.location_id:
            location = self.location_client.get_location(condition.location_id)
        if location is None:
            raise (Exception("Invalid Identifier for Location"))
        return location

    def resource_at_key(self, resource: Resource, condition: Condition) -> bool:
        """return if a resource is in a location at condition.key"""
        if isinstance(resource.children, list):
            if len(resource.children) > int(condition.key):
                if condition.resource_class:
                    return (
                        resource.children[int(condition.key)].resource_class
                        == condition.resource_class
                    )
                return True
            return False
        if str(condition.key) in resource.children:
            if condition.resource_class:
                return (
                    resource.children[str(condition.key)].resource_class
                    == condition.resource_class
                )
            return True
        return False

    def run_experiment(self, *args: Any, **kwargs: Any) -> Any:  # noqa: ARG002
        """The main experiment function, overwrite for each app"""
        return None

    def add_experiment_management(self, func: Callable[P, R]) -> Callable[P, R]:
        """wraps the run experiment function while preserving arguments"""

        @wraps(func)
        def run_experiment(*args: P.args, **kwargs: P.kwargs) -> R:
            with self.manage_experiment():
                return func(*args, **kwargs)

        return run_experiment

    def evaluate_condition(self, condition: Condition) -> bool:
        """evaluate a condition"""
        if condition.condition_type == "resource_present":
            location = self.get_location_from_condition(condition)
            resource = self.resource_client.get_resource(location.resource_id)
            return self.resource_at_key(resource, condition)
        if condition.condition_type == "no_resource_present":
            location = self.get_location_from_condition(condition)
            resource = self.resource_client.get_resource(location.resource_id)
            return not self.resource_at_key(resource, condition)

        if condition.condition_type == "resource_field_check":
            resource = self.get_resource_from_condition(condition)
            return self.check_resource_field(resource, condition)

        if condition.condition_type == "resource_child_field_check":
            resource = self.get_resource_from_condition(condition)
            if isinstance(resource.children, list):
                if len(resource.children) > int(condition.key):
                    resource_child = resource.children[int(condition.key)]
                else:
                    raise (Exception("Invalid Key for Resource Child"))
            elif condition.key not in resource.children:
                raise (Exception("Invalid Key for Resource Child"))
            else:
                resource_child = resource.children[condition.key]
            return self.check_resource_field(resource_child, condition)
        return False

    def start_app(self) -> None:
        """Starts the application, either as a node or in single run mode"""
        if self.config.server_mode:
            self._add_action(
                self.add_experiment_management(self.run_experiment),
                "run_experiment",
                "Run the Experiment",
                blocking=False,
            )
            self.start_node()
        else:
            self.run_experiment(*self.config.run_args, **self.config.run_kwargs)
