"""Provides an ExperimentApplication class that manages the execution of an experiment."""

import argparse
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Optional, Union

from madsci.client.data_client import DataClient
from madsci.client.event_client import EventClient
from madsci.client.experiment_client import ExperimentClient
from madsci.client.resource_client import ResourceClient
from madsci.client.workcell_client import WorkcellClient
from madsci.common.exceptions import ExperimentCancelledError, ExperimentFailedError
from madsci.common.types.base_types import PathLike
from madsci.common.types.condition_types import Condition
from madsci.common.types.context_types import MadsciContext
from madsci.common.types.experiment_types import (
    Experiment,
    ExperimentDesign,
    ExperimentStatus,
)
from madsci.common.types.location_types import Location
from madsci.common.types.resource_types import Resource
from madsci.common.utils import threaded_daemon
from madsci.node_module.rest_node_module import RestNode
from pydantic import AnyUrl
from rich import print
from typing import Callable, TypeVar
from typing_extensions import ParamSpec
from functools import wraps
P = ParamSpec('P')
R = TypeVar('R')
class ExperimentApplication(RestNode):
    """
    An experiment application that helps manage the execution of an experiment.

    You can either use this class as a base class for your own application class, or create an instance of it to manage the execution of an experiment.
    """

    experiment: Optional[Experiment] = None
    """The current experiment being run."""
    experiment_design: Optional[Union[ExperimentDesign, PathLike]] = None
    """The design of the experiment."""
    logger: EventClient
    event_client: EventClient
    """The event logger for the experiment."""
    context: MadsciContext
    """The context for the experiment application."""
    workcell_client: WorkcellClient
    """Client for managing workcells."""
    resource_client: ResourceClient
    """Client for managing resources."""
    data_client: DataClient
    """Client for managing data."""
    experiment_client: ExperimentClient
    """Client for managing experiments."""
    inputs = []
    """inputs to the main function"""
    

    def __init__(
        self,
        experiment_server_url: Optional[AnyUrl] = None,
        experiment_design: Optional[Union[str, Path, ExperimentDesign]] = None,
        experiment: Optional[Experiment] = None,
        *args: Any, 
        **kwargs: Any
    ) -> "ExperimentApplication":
        """Initialize the experiment application. You can provide an experiment design to use for creating new experiments, or an existing experiment to continue."""
        super().__init__(*args, **kwargs)
        self.context = (
            MadsciContext(experiment_server_url=experiment_server_url)
            if experiment_server_url
            else MadsciContext()
        )
        self.logger = self.event_client = EventClient()
        self.experiment_design = experiment_design or self.experiment_design
        if isinstance(self.experiment_design, (str, Path)):
            self.experiment_design = ExperimentDesign.from_yaml(self.experiment_design)

        self.experiment = experiment if experiment else self.experiment
        self.node_info.node_url = self.experiment_design.node_config.node_url
        self.config = self.experiment_design.node_config

        # * Re-initialize expeirment client in-case user provided a different server URL
        self.experiment_client = ExperimentClient(
            experiment_server_url=self.context.experiment_server_url
        )
        self.workcell_client = WorkcellClient()
        self.data_client = DataClient()
        self.resource_client = ResourceClient()
        self.event_client = self.logger = EventClient()

    @classmethod
    def start_new(
        cls,
        experiment_server_url: Optional[AnyUrl] = None,
        experiment_design: Optional[ExperimentDesign] = None,
    ) -> "ExperimentApplication":
        """Create a new experiment application with a new experiment."""
        self = cls(
            experiment_server_url=experiment_server_url,
            experiment_design=experiment_design,
        )
        self.start_experiment_run()
        return self

    @classmethod
    def continue_experiment(
        cls, experiment: Experiment, experiment_server_url: Optional[AnyUrl] = None
    ) -> "ExperimentApplication":
        """Create a new experiment application with an existing experiment."""
        self = cls(experiment_server_url=experiment_server_url, experiment=experiment)
        self.experiment_client.continue_experiment(
            experiment_id=experiment.experiment_id
        )
        return self

    def start_experiment_run(
        self, run_name: Optional[str] = None, run_description: Optional[str] = None
    ) -> None:
        """Sends the ExperimentDesign to the server to register a new experimental run."""

        self.experiment = self.experiment_client.start_experiment(
            experiment_design=self.experiment_design,
            run_name=run_name,
            run_description=run_description,
        )
        self.logger.log_info(
            f"Started run '{self.experiment.run_name}' ({self.experiment.experiment_id}) of experiment '{self.experiment.experiment_design.experiment_name}'"
        )
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
        self.logger.log_info(
            f"Ended run '{self.experiment.run_name}' ({self.experiment.experiment_id}) of experiment '{self.experiment.experiment_design.experiment_name}'"
        )

    def pause_experiment(self) -> None:
        """Pause the experiment."""
        self.experiment = self.experiment_client.pause_experiment(
            experiment_id=self.experiment.experiment_id
        )
        self.logger.log_info(
            f"Paused run '{self.experiment.run_name}' ({self.experiment.experiment_id}) of experiment '{self.experiment.experiment_design.experiment_name}'"
        )

    def cancel_experiment(self) -> None:
        """Cancel the experiment."""
        self.experiment = self.experiment_client.cancel_experiment(
            experiment_id=self.experiment.experiment_id
        )
        self.logger.log_info(
            f"Cancelled run '{self.experiment.run_name}' ({self.experiment.experiment_id}) of experiment '{self.experiment.experiment_design.experiment_name}'"
        )

    def fail_experiment(self) -> None:
        """Mark an experiment as failed."""
        self.experiment = self.experiment_client.end_experiment(
            experiment_id=self.experiment.experiment_id,
            status=ExperimentStatus.FAILED,
        )
        self.logger.log_info(
            f"Failed run '{self.experiment.run_name}' ({self.experiment.experiment_id}) of experiment '{self.experiment.experiment_design.experiment_name}'"
        )
    def handle_exception(self, exception: Exception):
        self.end_experiment(ExperimentStatus.FAILED)
        
    @contextmanager
    def manage_experiment(
        self, run_name: Optional[str] = None, run_description: Optional[str] = None
    ) -> contextmanager:
        """Context manager to start and end an experiment."""
        self.start_experiment_run(run_name=run_name, run_description=run_description)
        try:
            yield
        except Exception as e:
            self.handle_exception(e)
            raise(e)
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
            self.logger.log_warning(
                f"Experiment '{self.experiment.experiment_design.experiment_name}' has been paused."
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
            self.logger.log_error(exception.message)
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
            return getattr(resource, condition.field) < condition.target_value
        return False

    def get_location_from_condition(self, condition: Condition) -> Location:
        """get the location referenced by a condition"""
        location = None
        if condition.location_name:
            location = next(
                location
                for location in self.workcell_client.get_locations()
                if location.location_name == condition.location_name
            )
        elif condition.location_id:
            location = self.workcell_client.get_location(condition.location_id)
        if location is None:
            raise (Exception("Invalid Identifier for Location"))
        return location

    def resource_at_key(self, resource: Resource, condition: Condition) -> bool:
        """return if a resource is in a location at condition.key"""
        if isinstance(resource.children, list):
            if len(resource.children) > int(condition.key):
                if condition.resource_class:
                    return (
                        resource.children[condition.key].resource_class
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
    def run_experiment(self, kwargs):
        pass

    

    def add_experiment_management(self, func: Callable[P, R]) -> Callable[P, R]:
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
    def start_app(self):
        parser = argparse.ArgumentParser(
                    prog='ExperimentApp',
                    description='Runs an experiment application',
                    epilog='Can run in single shot or server mode')
        for value in self.inputs:
            parser.add_argument("--"+value["name"], default=value["default"])
        parser.add_argument("--server_mode", default=False)
        arguments = parser.parse_args()
        if arguments.server_mode:
            
            self._add_action(self.add_experiment_management(self.run_experiment), "run_experiment", "Run the Experiment", blocking=False)
            self.start_node()
        else:
            args_dict = arguments.__dict__
            del args_dict["server_mode"]
            self.run_experiment(**args_dict)