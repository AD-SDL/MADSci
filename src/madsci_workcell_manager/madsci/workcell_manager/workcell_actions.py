"""Built-in actions for the Workcell Manager, which don't require a node to be specified."""

import time
from typing import Union

from madsci.client.location_client import LocationClient
from madsci.client.workcell_client import WorkcellClient
from madsci.common.context import get_current_madsci_context
from madsci.common.exceptions import WorkflowCanceledError, WorkflowFailedError
from madsci.common.types.action_types import ActionFailed, ActionResult, ActionSucceeded


class LocationNotFoundError(Exception):
    """Raised when a location cannot be found by ID or name."""


def wait(seconds: Union[int, float]) -> ActionResult:
    """Waits for a specified number of seconds"""
    time.sleep(seconds)
    return ActionSucceeded()


def transfer(  # noqa: C901
    source: str, destination: str, await_completion: bool = True
) -> ActionResult:
    """
    Transfer a single discrete object between locations.

    This action takes a source and destination (either location name or ID),
    asks the location manager to generate a workflow to accomplish the transfer,
    submits that workflow to the workcell manager, and optionally waits for completion.

    Args:
        source: Source location name or ID
        destination: Destination location name or ID
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
        destination_location_id = _resolve_location_identifier(
            destination, location_client
        )

        # Plan the transfer using the location client
        workflow_definition = location_client.plan_transfer(
            source_location_id=source_location_id,
            destination_location_id=destination_location_id,
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
                    data={
                        "message": f"Transfer workflow enqueued from {source} to {destination}",
                        "workflow_id": workflow.workflow_id,
                        "source_location_id": source_location_id,
                        "destination_location_id": destination_location_id,
                    }
                )

            # Check final workflow status after completion
            elif workflow.status.completed:
                result = ActionSucceeded(
                    data={
                        "message": f"Transfer completed from {source} to {destination}",
                        "workflow_id": workflow.workflow_id,
                        "execution_time": workflow.status.workflow_runtime,
                        "source_location_id": source_location_id,
                        "destination_location_id": destination_location_id,
                    }
                )
            elif workflow.status.failed:
                step_info = (
                    f" at step {workflow.status.current_step_index}"
                    if workflow.status.current_step_index is not None
                    else ""
                )
                description = workflow.status.description or "Unknown error"
                result = ActionFailed(
                    errors=[f"Transfer workflow failed{step_info}: {description}"]
                )
            elif workflow.status.cancelled:
                result = ActionFailed(errors=["Transfer workflow was cancelled"])
            else:
                result = ActionFailed(
                    errors=[
                        f"Transfer workflow ended in unexpected state: {workflow.status.model_dump()}"
                    ]
                )
    except Exception as e:
        result = ActionFailed(errors=[f"Unexpected error in transfer: {e}"])
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


workcell_action_dict = {
    "wait": wait,
    "transfer": transfer,
}
