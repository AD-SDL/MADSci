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
from madsci.common.types.datapoint_types import FileDataPoint
from madsci.common.types.location_types import (
    LocationArgument,
)
from madsci.common.types.parameter_types import InputFile
from madsci.common.types.step_types import Step
from madsci.common.types.workcell_types import WorkcellDefinition
from madsci.common.types.workflow_types import (
    Workflow,
    WorkflowDefinition,
)
from madsci.workcell_manager.state_handler import WorkcellStateHandler
from madsci.workcell_manager.workcell_actions import workcell_action_dict


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
                f"Node {node_name} not in Workcell {state_handler.get_workcell_definition().workcell_name}"
            ) from e


def validate_workcell_action_step(step: Step) -> tuple[bool, str]:
    """Check if a step calling a workcell action is  valid"""
    if step.action in workcell_action_dict:
        action_callable = workcell_action_dict[step.action]
        signature = inspect.signature(action_callable)
        for name, parameter in signature.parameters.items():
            if name not in step.args and parameter.default is None:
                result = (
                    False,
                    f"Step '{step.name}': Missing Required Argument {name}",
                )
        result = (True, f"Step '{step.name}': Validated successfully")
    else:
        result = (
            False,
            f"Action {step.action} is not an existing workcell action, and no node is provided",
        )
    return result


def validate_step(step: Step, state_handler: WorkcellStateHandler) -> tuple[bool, str]:
    """Check if a step is valid based on the node's info"""
    result = validate_workcell_action_step(step)
    if step.node is not None and step.node in state_handler.get_nodes():
        node = state_handler.get_node(step.node)
        info = node.info
        if info is None:
            result = (
                True,
                f"Node {step.node} didn't return proper about information, skipping validation",
            )
        elif step.action in info.actions:
            action = info.actions[step.action]
            for action_arg in action.args.values():
                if (
                    action_arg.name not in step.args
                    and action_arg.name not in step.parameters.args
                    and action_arg.required
                ):
                    return (
                        False,
                        f"Step '{step.name}': Node {step.node}'s action, '{step.action}', is missing arg '{action_arg.name}'",
                    )
                # TODO: Action arg type validation goes here
            for action_location in action.locations.values():
                if (
                    action_location.name not in step.locations
                    and action_location not in step.parameters.locations
                    and action_location.required
                ):
                    return (
                        False,
                        f"Step '{step.name}': Node {step.node}'s action, '{step.action}', is missing location '{action_location.name}'",
                    )
            for action_file in action.files.values():
                if action_file.name not in step.files and action_file.required:
                    return (
                        False,
                        f"Step '{step.name}': Node {step.node}'s action, '{step.action}', is missing file '{action_file.name}'",
                    )
            result = (True, f"Step '{step.name}': Validated successfully")
        else:
            result = (
                False,
                f"Step '{step.name}': Node {step.node} has no action '{step.action}'",
            )
    else:
        result = (
            False,
            f"Step '{step.name}': Node {step.node} is not defined in workcell",
        )
    return result


def create_workflow(
    workflow_def: WorkflowDefinition,
    workcell: WorkcellDefinition,
    state_handler: WorkcellStateHandler,
    data_client: DataClient,
    input_values: Optional[dict[str, Any]] = None,
    input_file_paths: Optional[dict[str, str]] = None,
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
            "parameter_values": input_values,
            "input_file_paths": input_file_paths,
        }
    )
    wf = Workflow(**wf_dict)
    wf.step_definitions = workflow_def.steps
    steps = []
    for step in workflow_def.steps:
        steps.append(
            prepare_workflow_step(
                workcell, state_handler, step, wf, data_client, running=False
            )
        )

    wf.steps = [Step.model_validate(step.model_dump()) for step in steps]
    wf.submitted_time = datetime.now()
    return wf


def insert_parameters(step: Step, parameter_values: dict[str, Any]) -> Step:
    """Replace parameter values in a provided step"""
    if step.parameters is not None:
        step_dict = step.model_dump()
        for key, parameter_name in step.parameters.model_dump().items():
            if type(parameter_name) is str and parameter_name in parameter_values:
                step_dict[key] = parameter_values[parameter_name]
        step = Step.model_validate(step_dict)

        for key, parameter_name in step.parameters.args.items():
            if parameter_name in parameter_values:
                step.args[key] = parameter_values[parameter_name]
        for key, parameter_name in step.parameters.locations.items():
            if parameter_name in parameter_values:
                step.locations[key] = parameter_values[parameter_name]
    return step


def prepare_workflow_step(
    workcell: WorkcellDefinition,
    state_handler: WorkcellStateHandler,
    step: Step,
    workflow: Workflow,
    data_client: DataClient,
    running: bool = True,
) -> Step:
    """Prepares a step for execution by replacing locations and validating it"""
    parameter_values = workflow.parameter_values
    working_step = deepcopy(step)
    if step.parameters is not None:
        working_step = insert_parameters(working_step, parameter_values)
    replace_locations(workcell, working_step, state_handler)
    valid, validation_string = validate_step(working_step, state_handler=state_handler)
    if running:
        working_step = prepare_workflow_files(working_step, workflow, data_client)
    EventClient().log_info(validation_string)
    if not valid:
        raise ValueError(validation_string)
    return working_step


def check_parameters(
    workflow_definition: WorkflowDefinition,
    input_values: Optional[dict[str, Any]] = None,
) -> None:
    """Check that all required parameters are provided"""
    if input_values is not None:
        for input_value in workflow_definition.parameters.input_values:
            if input_value.key not in input_values:
                if input_value.default is not None:
                    input_values[input_value.key] = input_value.default
                else:
                    raise ValueError(f"Required value {input_value.key} not provided")
    for ffv in workflow_definition.parameters.feed_forward_values:
        if ffv.key in input_values:
            raise ValueError(
                f"{ffv.key} is a Feed Forward Value and will be calculated during execution"
            )


def prepare_workflow_files(
    step: Step, workflow: Workflow, data_client: DataClient
) -> Step:
    """Get workflow files ready to upload"""
    input_file_ids = workflow.input_file_ids
    for file, definition in step.files.items():
        suffixes = []
        if type(definition) is str:
            datapoint_id = input_file_ids[definition]
            if definition in workflow.input_file_paths:
                suffixes = Path(workflow.input_file_paths[definition]).suffixes
        elif type(definition) is InputFile:
            datapoint_id = input_file_ids[definition.key]
            if definition.key in workflow.input_file_paths:
                suffixes = Path(workflow.input_file_paths[definition.key]).suffixes

        with tempfile.NamedTemporaryFile(delete=False, suffix="".join(suffixes)) as f:
            data_client.save_datapoint_value(datapoint_id, f.name)
            step.file_paths[file] = f.name
    return step


def replace_locations(
    workcell: WorkcellDefinition, step: Step, state_handler: WorkcellStateHandler
) -> None:
    """Replaces the location names with the location objects"""
    locations = state_handler.get_locations()
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
            (
                loc
                for loc in locations.values()
                if loc.location_name == location_name_or_object
            ),
            None,
        )
        if target_loc is None:
            raise ValueError(
                f"Location {location_name_or_object} not found in Workcell '{workcell.workcell_name}'"
            )
        node_location = LocationArgument(
            location=target_loc.lookup[step.node],
            resource_id=target_loc.resource_id,
            location_name=target_loc.location_name,
        )
        step.locations[location_arg] = node_location


def save_workflow_files(
    workflow: Workflow, files: list[UploadFile], data_client: DataClient
) -> Workflow:
    """Saves the files to the workflow run directory,
    and updates the step files to point to the new location"""
    input_file_paths = workflow.input_file_paths
    input_files = {}

    for file in files:
        input_files[file.filename] = file.file
    input_file_ids = {}
    for file in workflow.parameters.input_files:
        if file.key not in input_files:
            raise ValueError(f"Missing file: {file.key}")
        path = Path(input_file_paths[file.key])
        suffixes = path.suffixes
        with tempfile.NamedTemporaryFile(delete=False, suffix="".join(suffixes)) as f:
            f.write(input_files[file.key].read())
            datapoint = FileDataPoint(
                label=file.key,
                ownership_info=workflow.ownership_info,
                path=Path(f.name),
            )
            datapoint_id = data_client.submit_datapoint(datapoint).datapoint_id
            input_file_ids[file.key] = datapoint_id
    workflow.input_file_ids = input_file_ids
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
    with state_handler.wc_state_lock():
        state_handler.set_active_workflow(wf)
    return wf


def cancel_active_workflows(state_handler: WorkcellStateHandler) -> None:
    """Cancels all currently running workflow runs"""
    for wf in state_handler.get_active_workflows().values():
        if wf.status.active:
            cancel_workflow(wf, state_handler=state_handler)
