"""Functions for checking conditions on a step"""

from madsci.common.types.condition_types import (
    Condition,
    NoResourceInLocationCondition,
    ResourceChildFieldCheckCondition,
    ResourceFieldCheckCondition,
    ResourceInLocationCondition,
)
from madsci.common.types.resource_types import ContainerTypeEnum, Resource
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
        elif isinstance(condition, ResourceFieldCheckCondition):
            metadata = evaluate_resource_field_check_condition(
                condition, scheduler, metadata
            )
        elif isinstance(condition, ResourceFieldCheckCondition):
            metadata = evaluate_resource_child_field_check_condition(
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
            if (
                condition.location_name is not None
                and condition.location_name == loc.location_name
            )
            or condition.location_id == loc.location_id
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
        try:
            ContainerTypeEnum(container.base_type)
        except ValueError:
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
            if (
                condition.location_name is not None
                and condition.location_name == loc.location_name
            )
            or condition.location_id == loc.location_id
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
        try:
            ContainerTypeEnum(container.base_type)
        except ValueError:
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


def get_resource_from_condition(
    condition: Condition, scheduler: AbstractScheduler
) -> Resource:
    """gets a resource by the identifiers provided in the condition"""
    resource = None
    if condition.resource_id:
        resource = scheduler.resource_client.get_resource(condition.resource_id)
    elif condition.resource_name:
        resource = scheduler.resource_client.query_resource(
            resource_name=condition.resource_name, multiple=False
        )
    if resource is None:
        raise (Exception("Invalid Identifier for Resource"))
    return resource


def check_resource_field(resource: Resource, condition: Condition) -> bool:
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


def evaluate_resource_field_check_condition(
    condition: ResourceFieldCheckCondition,
    scheduler: AbstractScheduler,
    metadata: SchedulerMetadata,
) -> SchedulerMetadata:
    """evaluates a resource field condition"""
    resource = get_resource_from_condition(condition, scheduler)
    if not check_resource_field(resource, condition):
        metadata.ready_to_run = False
        metadata.reasons.append(
            f"Resource {condition.resource_name} failed field {condition.field} {condition.operator!s} {condition.target_value}"
        )
    return metadata


def evaluate_resource_child_field_check_condition(
    condition: ResourceChildFieldCheckCondition,
    scheduler: AbstractScheduler,
    metadata: SchedulerMetadata,
) -> SchedulerMetadata:
    """evalutates a resource childe field condition"""
    resource = get_resource_from_condition(condition, scheduler)
    resource_child = resource.children[condition.key]
    if not check_resource_field(resource_child, condition):
        metadata.ready_to_run = False
        metadata.reasons.append(
            f"Resource {condition.resource_name} child {resource_child.resource_name} failed field {condition.field} {condition.operator!s} {condition.target_value}"
        )
    return metadata
