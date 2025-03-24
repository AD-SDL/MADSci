"""Functions for checking conditions on a step"""

from madsci.common.types.condition_types import (
    NoResourceInLocationCondition,
    ResourceInLocationCondition,
)
from madsci.common.types.resource_types import Container
from madsci.common.types.step_types import Step
from madsci.common.types.workflow_types import SchedulerMetadata
from madsci.workcell_manager.schedulers.scheduler import AbstractScheduler


def evaluate_condition_checks(
    step: Step, scheduler: AbstractScheduler, metadata: SchedulerMetadata
) -> SchedulerMetadata:
    """Check if the specified conditions for the step are met"""
    for condition in step.conditions:
        if isinstance(condition, ResourceInLocationCondition):
            metadata = evaluate_resource_in_location_condition(
                condition, scheduler, metadata
            )
        elif isinstance(condition, NoResourceInLocationCondition):
            metadata = evaluate_no_resource_in_location_condition(
                condition, scheduler, metadata
            )
        else:
            raise ValueError(f"Unknown condition type {condition.condition_type}")
    return metadata


def evaluate_resource_in_location_condition(
    condition: ResourceInLocationCondition,
    scheduler: AbstractScheduler,
    metadata: SchedulerMetadata,
) -> SchedulerMetadata:
    """Check if a resource is present in a specified location"""
    location = next(
        (
            loc
            for loc in scheduler.state_handler.get_locations()
            if condition.location in [loc.location_name, loc.location_id]
        ),
        None,
    )
    if location is None:
        metadata.ready_to_run = False
        metadata.reasons.append(f"Location {condition.location} not found.")
    elif location.resource_id is None:
        metadata.ready_to_run = False
        metadata.reasons.append(
            f"Location {location.location_name} does not have an attached container resource."
        )
    elif scheduler.resource_client is None:
        metadata.ready_to_run = False
        metadata.reasons.append("Resource client is not available.")
    else:
        container = scheduler.resource_client.get_resource(location.resource_id)
        if not isinstance(container, Container):
            metadata.ready_to_run = False
            metadata.reasons.append(
                f"Resource {container.resource_id} is not a container."
            )
            return metadata
        if condition.key is None and len(container.children) == 0:
            metadata.ready_to_run = False
            metadata.reasons.append(f"Resource {container.resource_id} is empty.")
        if condition.key is not None and container.get_child(condition.key) is None:
            metadata.ready_to_run = False
            metadata.reasons.append(
                f"Resource {container.resource_id} does not contain a child with key {condition.key}."
            )
    return metadata


def evaluate_no_resource_in_location_condition(
    condition: NoResourceInLocationCondition,
    scheduler: AbstractScheduler,
    metadata: SchedulerMetadata,
) -> SchedulerMetadata:
    """Check if a resource is not present in a specified location"""
    location = next(
        (
            loc
            for loc in scheduler.state_handler.get_locations()
            if condition.location in [loc.location_name, loc.location_id]
        ),
        None,
    )
    if location is None:
        metadata.ready_to_run = False
        metadata.reasons.append(f"Location {condition.location} not found.")
    elif location.resource_id is None:
        metadata.ready_to_run = False
        metadata.reasons.append(
            f"Location {location.location_name} does not have an attached container resource."
        )
    elif scheduler.resource_client is None:
        metadata.ready_to_run = False
        metadata.reasons.append("Resource client is not available.")
    else:
        container = scheduler.resource_client.get_resource(location.resource_id)
        if not isinstance(container, Container):
            metadata.ready_to_run = False
            metadata.reasons.append(
                f"Resource {container.resource_id} is not a container."
            )
            return metadata
        if condition.key is None and len(container.children) > 0:
            metadata.ready_to_run = False
            metadata.reasons.append(f"Resource {container.resource_id} is not empty.")
        if condition.key is not None and container.get_child(condition.key) is not None:
            metadata.ready_to_run = False
            metadata.reasons.append(
                f"Resource {container.resource_id} contains a child with key {condition.key} ({container.get_child(condition.key).resource_id})."
            )
    return metadata
