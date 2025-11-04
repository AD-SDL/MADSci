"""Utility function for the workcell manager."""

import inspect
import shutil
import tempfile
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from fastapi import UploadFile
from madsci.client.data_client import DataClient
from madsci.client.event_client import EventClient
from madsci.client.location_client import LocationClient
from madsci.common.types.datapoint_types import FileDataPoint
from madsci.common.types.location_types import (
    LocationArgument,
)
from madsci.common.types.parameter_types import ParameterInputFile, ParameterTypes
from madsci.common.types.step_types import Step
from madsci.common.types.workcell_types import WorkcellManagerDefinition
from madsci.common.types.workflow_types import (
    Workflow,
    WorkflowDefinition,
)
from madsci.workcell_manager.state_handler import WorkcellStateHandler
from madsci.workcell_manager.workcell_actions import workcell_action_dict
from sqlalchemy import Null, null


def validate_node_names(
    workflow: Workflow, state_handler: WorkcellStateHandler
) -> None:
    """
    Validates that the nodes in the workflow.step are in the workcell's nodes
    """
    for node_name in [step.node for step in workflow.steps]:
        try:
            if node_name:
                state_handler.get_node(node_name)
        except KeyError as e:
            raise ValueError(
                f"Node {node_name} not in Workcell {state_handler.get_workcell_definition().name}"
            ) from e


def validate_workcell_action_step(step: Step) -> tuple[bool, str]:
    """Check if a step calling a workcell action is  valid"""
    if step.action in workcell_action_dict:
        action_callable = workcell_action_dict[step.action]
        signature = inspect.signature(action_callable)
        for name, parameter in signature.parameters.items():
            if name not in step.args and parameter.default is None:
                return (
                    False,
                    f"Step '{step.name}': Missing Required Argument {name}",
                )
        return True, f"Step '{step.name}': Validated successfully"
    return (
        False,
        f"Action {step.action} is not an existing workcell action, and no node is provided",
    )


def _validate_feedforward(
    step: Step, feedforward_parameters: dict[str, Any]
) -> Optional[tuple[bool, str]]:
    if (
        step.node is None
        and step.use_parameters
        and step.use_parameters.node is not None
    ):
        if step.use_parameters.node in [param.key for param in feedforward_parameters]:
            return (
                True,
                f"Waiting for value from feedforward parameter {step.use_parameters.node} before validating step {step.name}",
            )
        return (
            False,
            f"Step '{step.name}': Feedforward parameter {step.use_parameters.node} not found",
        )
    return None


def _validate_node_action(
    step: Step, state_handler: WorkcellStateHandler
) -> tuple[bool, str]:
    node = state_handler.get_node(step.node)
    info = node.info
    if info is None:
        return (
            True,
            f"Node {step.node} didn't return proper about information, skipping validation",
        )
    if step.action is None or step.action not in info.actions:
        return (
            False,
            f"Step '{step.name}': Node {step.node} has no action '{step.action}'",
        )
    action = info.actions[step.action]
    missing_arg = next(
        (
            arg.name
            for arg in action.args.values()
            if arg.required
            and arg.name not in step.args
            and (
                step.use_parameters is None or arg.name not in step.use_parameters.args
            )
        ),
        None,
    )
    if missing_arg:
        return (
            False,
            f"Step '{step.name}': Node {step.node}'s action, '{step.action}', is missing arg '{missing_arg}'",
        )
    missing_location = next(
        (
            loc.name
            for loc in action.locations.values()
            if loc.required
            and loc.name not in step.locations
            and (
                step.use_parameters is None
                or loc.name not in step.use_parameters.locations
            )
        ),
        None,
    )
    if missing_location:
        return (
            False,
            f"Step '{step.name}': Node {step.node}'s action, '{step.action}', is missing location '{missing_location}'",
        )
    missing_file = next(
        (
            file.name
            for file in action.files.values()
            if file.required and file.name not in step.files
        ),
        None,
    )
    if missing_file:
        return (
            False,
            f"Step '{step.name}': Node {step.node}'s action, '{step.action}', is missing file '{missing_file}'",
        )
    return (True, f"Step '{step.name}': Validated successfully")


def validate_step(
    step: Step,
    state_handler: WorkcellStateHandler,
    feedforward_parameters: list[ParameterTypes],
) -> tuple[bool, str]:
    """Check if a step is valid based on the node's info"""

    feedforward_result = _validate_feedforward(step, feedforward_parameters)
    if feedforward_result:
        return feedforward_result

    if step.node is not None:
        if step.node in state_handler.get_nodes():
            return _validate_node_action(step, state_handler)
        return (
            False,
            f"Step '{step.name}': Node {step.node} is not defined in workcell",
        )
    if step.node is None:
        if step.action in workcell_action_dict:
            return validate_workcell_action_step(step)
        return (
            False,
            f"Step '{step.name}': No internal workcell action matching '{step.action}'",
        )
    return (
        False,
        f"Step '{step.name}': Unable to validate step due to unknown configuration",
    )


def create_workflow(
    workflow_def: WorkflowDefinition,
    workcell: WorkcellManagerDefinition,
    state_handler: WorkcellStateHandler,
    data_client: DataClient,
    json_inputs: Optional[dict[str, Any]] = None,
    file_input_paths: Optional[dict[str, str]] = None,
    location_client: Optional[LocationClient] = None,
) -> Workflow:
    """Pulls the workcell and builds a list of dictionary steps to be executed

    Parameters
    ----------
    workflow_def: WorkflowDefintion
        The workflow data file loaded in from the workflow yaml file

    workcell : Workcell
        The Workcell object stored in the database

    parameters: Dict
        The input to the workflow

    ownership_info: OwnershipInfo
        Information on the owner(s) of the workflow

    simulate: bool
        Whether or not to use real robots

    Returns
    -------
    steps: WorkflowRun
        a completely initialized workflow run
    """
    validate_node_names(workflow_def, state_handler)
    wf_dict = workflow_def.model_dump(mode="json")
    wf_dict.update(
        {
            "label": workflow_def.name,
            "parameter_values": json_inputs,
            "file_input_paths": file_input_paths,
        }
    )
    wf = Workflow(**wf_dict)
    wf.step_definitions = workflow_def.steps
    steps = []
    for step in workflow_def.steps:
        steps.append(
            prepare_workflow_step(
                workcell,
                state_handler,
                step,
                wf,
                data_client,
                location_client,
                running=False,
            )
        )

    wf.steps = [Step.model_validate(step.model_dump()) for step in steps]
    wf.submitted_time = datetime.now()
    return wf


def insert_parameters(step: Step, parameter_values: dict[str, Any]) -> Step:
    """Replace parameter values in a provided step"""
    if step.use_parameters is not None:
        step_dict = step.model_dump()
        for key, parameter_name in step.use_parameters.model_dump().items():
            if type(parameter_name) is str and parameter_name in parameter_values:
                step_dict[key] = parameter_values[parameter_name]
        step = Step.model_validate(step_dict)

        for key, parameter_name in step.use_parameters.args.items():
            if parameter_name in parameter_values:
                step.args[key] = parameter_values[parameter_name]
        for key, parameter_name in step.use_parameters.locations.items():
            if parameter_name in parameter_values:
                step.locations[key] = parameter_values[parameter_name]
    return step


def prepare_workflow_step(
    workcell: WorkcellManagerDefinition,
    state_handler: WorkcellStateHandler,
    step: Step,
    workflow: Workflow,
    data_client: DataClient,
    location_client: Optional[LocationClient] = None,
    running: bool = True,
) -> Step:
    """Prepares a step for execution by replacing locations and validating it"""
    parameter_values = workflow.parameter_values
    working_step = deepcopy(step)
    if step.use_parameters is not None:
        working_step = insert_parameters(working_step, parameter_values)
    replace_locations(workcell, working_step, location_client)
    valid, validation_string = validate_step(
        working_step,
        state_handler=state_handler,
        feedforward_parameters=workflow.parameters.feed_forward,
    )
    if running:
        working_step = prepare_workflow_files(working_step, workflow, data_client)
    EventClient().info(validation_string)
    if not valid:
        raise ValueError(validation_string)
    return working_step


def check_parameters(
    workflow_definition: WorkflowDefinition,
    json_inputs: Optional[dict[str, Any]] = None,
    file_input_paths: Optional[dict[str, str]] = None,
) -> None:
    """Check that all required parameters are provided"""
    if workflow_definition.parameters.json_inputs:
        check_json_parameters(workflow_definition, json_inputs)
    for ffv in workflow_definition.parameters.feed_forward:
        if (json_inputs and ffv.key in json_inputs) or (
            file_input_paths and ffv.key in file_input_paths
        ):
            raise ValueError(
                f"{ffv.key} is a Feed Forward Value and will be calculated during execution; it should not be provided as an input."
            )
    if workflow_definition.parameters.file_inputs:
        if file_input_paths is None:
            raise ValueError(
                "Workflow requires at least one file input; none were provided"
            )
        for file_input in workflow_definition.parameters.file_inputs:
            if file_input.key not in file_input_paths:
                raise ValueError(f"Required file {file_input.key} not provided")


def check_json_parameters(
    workflow_definition: WorkflowDefinition, json_inputs: Optional[dict[str, Any]]
) -> None:
    """Check that all required JSON parameters are provided"""
    if json_inputs is None:
        raise ValueError(
            "Workflow requires at least one JSON input; none were provided"
        )
    for json_input in workflow_definition.parameters.json_inputs:
        if json_input.key not in json_inputs:
            if json_input.default is not None:
                json_inputs[json_input.key] = json_input.default
            else:
                raise ValueError(f"Required value {json_input.key} not provided")


def prepare_workflow_files(
    step: Step, workflow: Workflow, data_client: DataClient
) -> Step:
    """Get workflow files ready to upload"""
    file_input_ids = workflow.file_input_ids
    for file, definition in step.files.items():
        suffixes = []
        if type(definition) is str:
            datapoint_id = file_input_ids[definition]
            if definition in workflow.file_input_paths:
                suffixes = Path(workflow.file_input_paths[definition]).suffixes
        elif type(definition) is ParameterInputFile:
            datapoint_id = file_input_ids[definition.key]
            if definition.key in workflow.file_input_paths:
                suffixes = Path(workflow.file_input_paths[definition.key]).suffixes

        with tempfile.NamedTemporaryFile(delete=False, suffix="".join(suffixes)) as f:
            data_client.save_datapoint_value(datapoint_id, f.name)
            step.file_paths[file] = f.name
    return step


def replace_locations(
    workcell: WorkcellManagerDefinition,
    step: Step,
    location_client: Optional[LocationClient] = None,
) -> None:
    """Replaces the location names with the location objects"""
    locations = {}
    if location_client is not None:
        location_list = location_client.get_locations()
        locations = {loc.location_id: loc for loc in location_list}
    for location_arg, location_name_or_object in step.locations.items():
        # * No location provided, set to None
        if location_name_or_object is None:
            step.locations[location_arg] = None
            continue
        # * Location is a LocationArgument, use it as is
        if isinstance(location_name_or_object, LocationArgument):
            step.locations[location_arg] = location_name_or_object
            continue

        # * Location is a string, find the corresponding Location object from state_handler
        target_loc = next(
            (loc for loc in locations.values() if loc.name == location_name_or_object),
            None,
        )
        if target_loc is None:
            raise ValueError(
                f"Location {location_name_or_object} not found in Workcell '{workcell.name}'"
            )
        node_location = LocationArgument(
            location=target_loc.representations[step.node],
            resource_id=target_loc.resource_id,
            location_name=target_loc.name,
        )
        step.locations[location_arg] = node_location


def save_workflow_files(
    workflow: Workflow, files: list[UploadFile], data_client: DataClient
) -> Workflow:
    """Saves the files to the workflow run directory,
    and updates the step files to point to the new location"""
    file_input_paths = workflow.file_input_paths
    file_inputs = {}

    for file in files:
        file_inputs[file.filename] = file.file
    file_input_ids = {}
    for file in workflow.parameters.file_inputs:
        if file.key not in file_inputs:
            raise ValueError(f"Missing file: {file.key}")
        path = Path(file_input_paths[file.key])
        suffixes = path.suffixes
        with tempfile.NamedTemporaryFile(delete=False, suffix="".join(suffixes)) as f:
            f.write(file_inputs[file.key].read())
            f.flush()  # Ensure file contents are written to disk before submitting
            datapoint = FileDataPoint(
                label=file.key,
                ownership_info=workflow.ownership_info,
                path=Path(f.name),
            )
            datapoint_id = data_client.submit_datapoint(datapoint).datapoint_id
            file_input_ids[file.key] = datapoint_id
    workflow.file_input_ids = file_input_ids
    return workflow


def copy_workflow_files(
    working_directory: str, old_id: str, workflow: Workflow
) -> Workflow:
    """Saves the files to the workflow run directory,
    and updates the step files to point to the new location"""

    new = get_workflow_inputs_directory(
        workflow_id=workflow.workflow_id, working_directory=working_directory
    )
    old = get_workflow_inputs_directory(
        workflow_id=old_id, working_directory=working_directory
    )
    shutil.copytree(old, new)
    return workflow


def get_workflow_inputs_directory(
    workflow_id: Optional[str] = None, working_directory: Optional[str] = None
) -> Path:
    """returns a directory name for the workflows inputs"""
    return Path(working_directory).expanduser() / "Workflows" / workflow_id / "Inputs"


def cancel_workflow(wf: Workflow, state_handler: WorkcellStateHandler) -> None:
    """Cancels the workflow run"""
    wf.status.cancelled = True
    # if not wf.start_time:
    #     wf.start_time = datetime.now()
    # if not wf.end_time:
    #     wf.end_time = datetime.now()
    with state_handler.wc_state_lock():
        state_handler.set_active_workflow(wf)
    return wf


def cancel_active_workflows(state_handler: WorkcellStateHandler) -> None:
    """Cancels all currently running workflow runs"""
    for wf in state_handler.get_active_workflows().values():
        if wf.status.active:
            cancel_workflow(wf, state_handler=state_handler)
