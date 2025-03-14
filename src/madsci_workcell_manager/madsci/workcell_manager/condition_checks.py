"""Functions for checking conditions on a step"""

from madsci.common.types.condition_types import (
    NoResourceInLocationCondition,
    ResourceInLocationCondition,
)
from madsci.common.types.resource_types import Container
from madsci.common.types.step_types import Step
from madsci.common.types.workflow_types import Workflow
from madsci.workcell_manager.schedulers.default_scheduler import Scheduler


def evaluate_condition_checks(step: Step, wf: Workflow, scheduler: Scheduler) -> None:
    """Check if the specified conditions for the step are met"""
    for condition in step.conditions:
        if isinstance(condition, ResourceInLocationCondition):
            evaluate_resource_in_location_condition(condition, wf, scheduler)
        elif isinstance(condition, NoResourceInLocationCondition):
            evaluate_no_resource_in_location_condition(condition, wf, scheduler)
        else:
            raise ValueError(f"Unknown condition type {condition.condition_type}")


def evaluate_resource_in_location_condition(
    condition: ResourceInLocationCondition, wf: Workflow, scheduler: Scheduler
) -> None:
    """Check if a resource is present in a specified location"""
    location = scheduler.workcell.locations[condition.location]
    if location.resource_id is None:
        wf.scheduler_metadata.ready_to_run = False
        wf.scheduler_metadata.reasons.append(
            f"Location {location.name} cannot provide resource presence information."
        )
    elif scheduler.resource_client is None:
        wf.scheduler_metadata.ready_to_run = False
        wf.scheduler_metadata.reasons.append("Resource client is not available.")
    else:
        container = scheduler.resource_client.get_resource(location.resource_id)
        if not isinstance(container, Container):
            wf.scheduler_metadata.ready_to_run = False
            wf.scheduler_metadata.reasons.append(
                f"Resource {container.resource_id} is not a container."
            )
            return
        if len(container.children) == 0:
            wf.scheduler_metadata.ready_to_run = False
            wf.scheduler_metadata.reasons.append(
                f"Resource {container.resource_id} is empty."
            )
        if condition.key is not None and container.get_child(condition.key) is None:
            wf.scheduler_metadata.ready_to_run = False
            wf.scheduler_metadata.reasons.append(
                f"Resource {container.resource_id} does not contain a child with key {condition.key}."
            )


def evaluate_no_resource_in_location_condition(
    condition: NoResourceInLocationCondition, wf: Workflow, scheduler: Scheduler
) -> None:
    """Check if a resource is not present in a specified location"""
    location = scheduler.workcell.locations[condition.location]
    if location.resource_id is None:
        wf.scheduler_metadata.ready_to_run = False
        wf.scheduler_metadata.reasons.append(
            f"Location {location.name} cannot provide resource presence information."
        )
    elif scheduler.resource_client is None:
        wf.scheduler_metadata.ready_to_run = False
        wf.scheduler_metadata.reasons.append("Resource client is not available.")
    else:
        container = scheduler.resource_client.get_resource(location.resource_id)
        if not isinstance(container, Container):
            wf.scheduler_metadata.ready_to_run = False
            wf.scheduler_metadata.reasons.append(
                f"Resource {container.resource_id} is not a container."
            )
            return
        if len(container.children) > 0:
            wf.scheduler_metadata.ready_to_run = False
            wf.scheduler_metadata.reasons.append(
                f"Resource {container.resource_id} is not empty."
            )
        if condition.key is not None and container.get_child(condition.key) is not None:
            wf.scheduler_metadata.ready_to_run = False
            wf.scheduler_metadata.reasons.append(
                f"Resource {container.resource_id} contains a child with key {condition.key} ({container.get_child(condition.key).resource_id})."
            )
