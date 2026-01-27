Module madsci.workcell_manager.workcell_actions
===============================================
Built-in actions for the Workcell Manager, which don't require a node to be specified.

Functions
---------

`transfer(source: str, target: str, await_completion: bool = True) ‑> madsci.common.types.action_types.ActionResult`
:   Transfer a single discrete object between locations.

    This action takes a source and target (either location name or ID),
    asks the location manager to generate a workflow to accomplish the transfer,
    submits that workflow to the workcell manager, and optionally waits for completion.

    Args:
        source: Source location name or ID
        target: Target location name or ID
        await_completion: Whether to block until the transfer workflow completes

    Returns:
        ActionResult: Success if transfer workflow was executed successfully, failure otherwise

`transfer_resource(resource_id: str, target: str, await_completion: bool = True) ‑> madsci.common.types.action_types.ActionResult`
:   Transfer a specific resource from its current location to a target.

    This action finds the current location of a resource using the resource and location
    clients, then uses the transfer action to move it to the specified target.

    Args:
        resource_id: ID of the resource to transfer
        target: Target location name or ID
        await_completion: Whether to block until the transfer workflow completes

    Returns:
        ActionResult: Success if transfer workflow was executed successfully, failure otherwise

`wait(seconds: int | float) ‑> madsci.common.types.action_types.ActionResult`
:   Waits for a specified number of seconds

Classes
-------

`WorkcellTransferJSON(**data: Any)`
:   JSON response model for transfer action

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.action_types.ActionJSON
    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `execution_time: float | None`
    :   The time taken to execute the transfer, in seconds. Only present if await_completion is True.

    `message: str`
    :   A message describing the result of the transfer.

    `model_config`
    :

    `source_location_id: str`
    :   The ID of the source location.

    `target_location_id: str`
    :   The ID of the target location.

    `workflow_id: str`
    :   The ID of the workflow that was executed.
