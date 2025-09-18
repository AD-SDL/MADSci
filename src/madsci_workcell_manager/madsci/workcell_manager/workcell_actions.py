"""Built-in actions for the Workcell Manager, which don't require a node to be specified."""

import time
from typing import Optional, Union

import httpx
from madsci.common.context import get_current_madsci_context
from madsci.common.types.action_types import ActionFailed, ActionResult, ActionSucceeded
from madsci.common.types.context_types import MadsciContext


def wait(seconds: int) -> ActionResult:
    """Waits for a specified number of seconds"""
    time.sleep(seconds)
    return ActionSucceeded()


def transfer_resource(resource_id: str, destination_location_id: str) -> ActionResult:
    """
    Transfer a specific resource to a destination location.

    The system will:
    1. Query the resource manager to find the resource's current location
    2. Identify the parent container and associated location
    3. Plan transfer from current location to destination
    4. Execute the transfer workflow

    Args:
        resource_id: ID of the resource to transfer
        destination_location_id: Destination location ID

    Returns:
        ActionResult: Success if transfer completed, failure otherwise
    """
    try:
        context = get_current_madsci_context()

        # Validate context configuration
        validation_result = _validate_transfer_context(
            context, require_resource_server=True
        )
        if validation_result is not None:
            return validation_result

        # Find the resource's current location
        source_location_result = _find_resource_location(resource_id, context)
        if isinstance(source_location_result, ActionResult):
            return source_location_result

        source_location_id = source_location_result

        # Execute transfer
        return _execute_transfer(
            source_location_id, destination_location_id, resource_id, context
        )

    except Exception as e:
        return ActionFailed(errors=[f"Unexpected error in transfer_resource: {e}"])


def transfer_location_contents(
    source_location_id: str, destination_location_id: str
) -> ActionResult:
    """
    Transfer all contents from source location to destination location.

    The system will:
    1. Query the location manager to identify resources at source location
    2. Plan transfer workflow from source to destination
    3. Execute transfer for all resources found

    Args:
        source_location_id: Source location ID
        destination_location_id: Destination location ID

    Returns:
        ActionResult: Success if transfer completed, failure otherwise
    """
    try:
        context = get_current_madsci_context()

        # Validate context configuration
        validation_result = _validate_transfer_context(
            context, require_resource_server=False
        )
        if validation_result is not None:
            return validation_result

        # Check if source location has resources
        resources_result = _get_location_resources(source_location_id, context)
        if isinstance(resources_result, ActionResult):
            return resources_result

        resource_ids = resources_result
        if not resource_ids:
            return ActionSucceeded(
                data={"message": f"No resources found at location {source_location_id}"}
            )

        # Execute transfer for all resources
        return _execute_transfer(
            source_location_id, destination_location_id, None, context
        )

    except Exception as e:
        return ActionFailed(
            errors=[f"Unexpected error in transfer_location_contents: {e}"]
        )


def _validate_transfer_context(
    context: MadsciContext, require_resource_server: bool = False
) -> Optional[ActionResult]:
    """Validate that required server URLs are configured in context."""
    if not context.location_server_url:
        return ActionFailed(
            errors=[
                "Location server URL not configured. Set location_server_url in context."
            ]
        )

    if require_resource_server and not context.resource_server_url:
        return ActionFailed(
            errors=[
                "Resource server URL not configured. Set resource_server_url in context."
            ]
        )

    return None


def _find_resource_location(
    resource_id: str, context: MadsciContext
) -> Union[str, ActionResult]:
    """Find the location containing a specific resource."""
    # Get resource information
    parent_result = _get_resource_parent(resource_id, context)
    if isinstance(parent_result, ActionResult):
        return parent_result

    parent_id = parent_result

    # Find location containing the parent resource
    return _find_location_by_resource(resource_id, parent_id, context)


def _get_resource_parent(
    resource_id: str, context: MadsciContext
) -> Union[str, ActionResult]:
    """Get the parent resource ID for a given resource."""
    try:
        with httpx.Client() as client:
            resource_response = client.get(
                f"{context.resource_server_url}resource/{resource_id}", timeout=10.0
            )

            if resource_response.status_code == 404:
                return ActionFailed(
                    errors=[f"Resource {resource_id} not found in resource manager"]
                )
            if resource_response.status_code != 200:
                return ActionFailed(
                    errors=[
                        f"Failed to query resource manager: {resource_response.status_code} - {resource_response.text}"
                    ]
                )

            resource_data = resource_response.json()
            parent_id = resource_data.get("parent_id")
            if not parent_id:
                return ActionFailed(
                    errors=[
                        f"Resource {resource_id} has no parent container to determine location"
                    ]
                )

            return parent_id

    except httpx.RequestError as e:
        return ActionFailed(errors=[f"Failed to connect to resource manager: {e}"])


def _find_location_by_resource(
    resource_id: str, parent_id: str, context: MadsciContext
) -> Union[str, ActionResult]:
    """Find the location containing a specific resource."""
    try:
        with httpx.Client() as client:
            locations_response = client.get(
                f"{context.location_server_url}locations", timeout=10.0
            )

            if locations_response.status_code != 200:
                return ActionFailed(
                    errors=[
                        f"Failed to query location manager: {locations_response.status_code} - {locations_response.text}"
                    ]
                )

            locations = locations_response.json()
            for location in locations:
                if location.get("resource_id") == parent_id:
                    return location["location_id"]

            return ActionFailed(
                errors=[
                    f"Could not find location containing resource {resource_id} (parent: {parent_id})"
                ]
            )

    except httpx.RequestError as e:
        return ActionFailed(errors=[f"Failed to connect to location manager: {e}"])


def _get_location_resources(
    source_location_id: str, context: MadsciContext
) -> Union[list, ActionResult]:
    """Get all resources at a specific location."""
    try:
        with httpx.Client() as client:
            # Query location manager for resources at source location
            # Note: This endpoint doesn't exist yet - we'll add it in Phase 2
            resources_response = client.get(
                f"{context.location_server_url}location/{source_location_id}/resources",
                timeout=10.0,
            )

            if resources_response.status_code == 404:
                return ActionFailed(
                    errors=[f"Source location {source_location_id} not found"]
                )
            if resources_response.status_code != 200:
                return ActionFailed(
                    errors=[
                        f"Failed to query location resources: {resources_response.status_code} - {resources_response.text}"
                    ]
                )

            return resources_response.json()

    except httpx.RequestError as e:
        return ActionFailed(errors=[f"Failed to connect to location manager: {e}"])


def _execute_transfer(
    source_location_id: str,
    destination_location_id: str,
    resource_id: Optional[str],
    context: MadsciContext,
) -> ActionResult:
    """
    Execute the actual transfer by calling the location manager's transfer planning API.

    Args:
        source_location_id: Source location ID
        destination_location_id: Destination location ID
        resource_id: Optional resource ID for tracking
        context: MADSci context with server URLs

    Returns:
        ActionResult: Success if transfer workflow was planned and executed
    """
    try:
        with httpx.Client() as client:
            # Call location manager's transfer planning endpoint
            # Note: This endpoint doesn't exist yet - we'll add it in Phase 2
            transfer_request = {
                "source_location_id": source_location_id,
                "destination_location_id": destination_location_id,
            }
            if resource_id:
                transfer_request["resource_id"] = resource_id

            plan_response = client.post(
                f"{context.location_server_url}transfer/plan",
                json=transfer_request,
                timeout=30.0,
            )

            if plan_response.status_code == 404:
                return ActionFailed(
                    errors=[
                        f"No transfer path exists between {source_location_id} and {destination_location_id}"
                    ]
                )
            if plan_response.status_code != 200:
                return ActionFailed(
                    errors=[
                        f"Failed to plan transfer: {plan_response.status_code} - {plan_response.text}"
                    ]
                )

            # Get the workflow definition from the response
            workflow_def = plan_response.json()

            # For now, return success with the workflow definition
            # In Phase 2, we'll actually execute this workflow
            return ActionSucceeded(
                data={
                    "message": f"Transfer planned from {source_location_id} to {destination_location_id}",
                    "workflow_definition": workflow_def,
                    "resource_id": resource_id,
                }
            )

    except httpx.RequestError as e:
        return ActionFailed(
            errors=[f"Failed to connect to location manager for transfer planning: {e}"]
        )
    except Exception as e:
        return ActionFailed(errors=[f"Unexpected error in transfer execution: {e}"])


workcell_action_dict = {
    "wait": wait,
    "transfer_resource": transfer_resource,
    "transfer_location_contents": transfer_location_contents,
}
