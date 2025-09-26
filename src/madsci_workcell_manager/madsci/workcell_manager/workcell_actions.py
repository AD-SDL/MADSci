"""Built-in actions for the Workcell Manager, which don't require a node to be specified."""

import time
from typing import Any, Union

from madsci.client.location_client import LocationClient
from madsci.client.resource_client import ResourceClient
from madsci.client.workcell_client import WorkcellClient
from madsci.common.context import get_current_madsci_context
from madsci.common.exceptions import (
    LocationNotFoundError,
    WorkflowCanceledError,
    WorkflowFailedError,
)
from madsci.common.types.action_types import (
    ActionFailed,
    ActionJSON,
    ActionResult,
    ActionSucceeded,
)


def wait(seconds: Union[int, float]) -> None:
    """Waits for a specified number of seconds"""
    time.sleep(seconds)


class WorkcellTransferJSON(ActionJSON):
    """JSON response model for transfer action"""

    message: str
    """A message describing the result of the transfer."""
    workflow_id: str
    """The ID of the workflow that was executed."""
    source_location_id: str
    """The ID of the source location."""
    target_location_id: str
    """The ID of the target location."""
    execution_time: float | None = None
    """The time taken to execute the transfer, in seconds. Only present if await_completion is True."""


def transfer(  # noqa: C901
    source: str, target: str, await_completion: bool = True
) -> ActionJSON:
    """
    Transfer a single discrete object between locations.

    This action takes a source and target (either location name or ID),
    asks the location manager to generate a workflow to accomplish the transfer,
    submits that workflow to the workcell manager, and optionally waits for completion.

    Args:
        source: Source location name or ID
        target: Target location name or ID
        await_completion: Whether to block until the transfer workflow completes

    Returns:
        ActionResult: Success if transfer workflow was executed successfully, failure otherwise
    """
    try:
        context = get_current_madsci_context()

        # Validate context configuration
        if not context.location_server_url:
            return ActionFailed(
                errors=[
                    "Location server URL not configured. Set location_server_url in context."
                ]
            )

        if not context.workcell_server_url:
            return ActionFailed(
                errors=[
                    "Workcell server URL not configured. Set workcell_server_url in context."
                ]
            )

        # Get location client
        location_client = LocationClient(str(context.location_server_url))

        # Resolve location names to IDs if needed
        source_location_id = _resolve_location_identifier(source, location_client)
        target_location_id = _resolve_location_identifier(target, location_client)

        # Plan the transfer using the location client
        workflow_definition = location_client.plan_transfer(
            source_location_id=source_location_id,
            target_location_id=target_location_id,
        )

        # Submit workflow to workcell manager
        try:
            workcell_client = WorkcellClient(str(context.workcell_server_url))
            workflow = workcell_client.start_workflow(
                workflow_definition=workflow_definition,
                await_completion=await_completion,
            )
        except WorkflowFailedError as e:
            result = ActionFailed(
                errors=[f"Transfer workflow failed during execution: {e}"]
            )
        except WorkflowCanceledError as e:
            result = ActionFailed(errors=[f"Transfer workflow was cancelled: {e}"])
        else:
            if not await_completion:
                # Return immediately after successful enqueueing
                result = ActionSucceeded(
                    json_data=WorkcellTransferJSON.model_validate(
                        {
                            "message": f"Transfer workflow enqueued from {source} to {target}",
                            "workflow_id": workflow.workflow_id,
                            "source_location_id": source_location_id,
                            "target_location_id": target_location_id,
                        }
                    )
                )

            # Check final workflow status after completion
            elif workflow.status.completed:
                result = ActionSucceeded(
                    data=WorkcellTransferJSON.model_validate(
                        {
                            "message": f"Transfer completed from {source} to {target}",
                            "workflow_id": workflow.workflow_id,
                            "execution_time": workflow.duration_seconds,
                            "source_location_id": source_location_id,
                            "target_location_id": target_location_id,
                        }
                    )
                )
            elif workflow.status.failed:
                step_info = (
                    f" at step {workflow.status.current_step_index}"
                    if workflow.status.current_step_index is not None
                    else ""
                )
                description = workflow.status.description or "Unknown error"
                raise Exception(f"Transfer workflow failed{step_info}: {description}")
            elif workflow.status.cancelled:
                raise Exception("Transfer workflow was cancelled")
            else:
                raise Exception(
                    f"Transfer workflow ended in unexpected state: {workflow.status.model_dump()}"
                )
    except Exception as e:
        raise Exception(f"Unexpected error in transfer: {e}") from None
    return result


def _resolve_location_identifier(
    identifier: str, location_client: LocationClient
) -> str:
    """
    Resolve a location identifier (name or ID) to a location ID.

    Args:
        identifier: Location name or ID
        location_client: Location client for API calls

    Returns:
        Location ID if resolved successfully

    Raises:
        LocationNotFoundError: If location cannot be found by ID or name
    """
    # First try to get location by ID
    try:
        location = location_client.get_location(identifier)
        if location:
            return location.location_id
    except Exception:  # noqa: S110
        # Intentionally catching all exceptions - if ID lookup fails, try by name
        pass

    # Try to get location by name
    try:
        location = location_client.get_location_by_name(identifier)
        if location:
            return location.location_id
    except Exception:  # noqa: S110
        # Intentionally catching all exceptions - if name lookup fails, raise not found error
        pass

    raise LocationNotFoundError(f"Location '{identifier}' not found by ID or name")


def transfer_resource(
    resource_id: str, target: str, await_completion: bool = True
) -> WorkcellTransferJSON:
    """
    Transfer a specific resource from its current location to a target.

    This action finds the current location of a resource using the resource and location
    clients, then uses the transfer action to move it to the specified target.

    Args:
        resource_id: ID of the resource to transfer
        target: Target location name or ID
        await_completion: Whether to block until the transfer workflow completes

    Returns:
        ActionResult: Success if transfer workflow was executed successfully, failure otherwise
    """
    try:
        context = get_current_madsci_context()

        # Validate context configuration
        if not context.location_server_url:
            raise Exception(
                "Location server URL not configured. Set location_server_url in context."
            )

        if not context.resource_server_url:
            raise Exception(
                "Resource server URL not configured. Set resource_server_url in context."
            )

        # Find resource and perform transfer
        result = _find_resource_and_transfer(
            resource_id, target, await_completion, context
        )

        # If result is a string, it's an error message
        if isinstance(result, str):
            raise Exception(result)

        # Otherwise it's an ActionResult from the transfer
        return result

    except Exception as e:
        raise Exception(f"Unexpected error in transfer_resource: {e}") from None


def _find_resource_and_transfer(
    resource_id: str, target: str, await_completion: bool, context: Any
) -> Union[str, ActionResult]:
    """
    Helper function to find resource location and perform transfer.

    Returns:
        str: Error message if validation fails
        ActionResult: Transfer result if successful
    """
    # Get clients
    location_client = LocationClient(str(context.location_server_url))
    resource_client = ResourceClient(str(context.resource_server_url))

    # Verify the resource exists
    try:
        resource = resource_client.get_resource(resource_id)
        if not resource:
            return f"Resource '{resource_id}' not found"
    except Exception as e:
        return f"Failed to verify resource '{resource_id}': {e}"

    # Find the current location of the resource
    try:
        locations = location_client.get_locations()
        source_location_id = None

        for location in locations:
            # Get the resource hierarchy for this location
            location_resources = location_client.get_location_resources(
                location.location_id
            )

            # Check if the resource is at this location (could be the main resource or a descendant)
            if location_resources.resource_id == resource_id or any(
                resource_id in descendants
                for descendants in location_resources.descendant_ids.values()
            ):
                source_location_id = location.location_id
                break

        if not source_location_id:
            return f"Resource '{resource_id}' not found at any location"

        # Use the existing transfer action to perform the transfer
        return transfer(
            source=source_location_id,
            target=target,
            await_completion=await_completion,
        )

    except Exception as e:
        return f"Failed to find location of resource '{resource_id}': {e}"


workcell_action_dict = {
    "wait": wait,
    "transfer": transfer,
    "transfer_resource": transfer_resource,
}
