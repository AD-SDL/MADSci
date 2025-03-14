"""Utility function for the workcell manager."""

import shutil
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from fastapi import UploadFile
from madsci.client.event_client import default_logger
from madsci.common.types.auth_types import OwnershipInfo
from madsci.common.types.location_types import Location
from madsci.common.types.step_types import Step
from madsci.common.types.workcell_types import WorkcellDefinition
from madsci.common.types.workflow_types import (
    Workflow,
    WorkflowDefinition,
    WorkflowStatus,
)
from madsci.workcell_manager.redis_handler import WorkcellRedisHandler


def validate_node_names(workflow: Workflow, workcell: WorkcellDefinition) -> None:
    """
    Validates that the nodes in the workflow.step are in the workcell.nodes
    """
    for node_name in [step.node for step in workflow.steps]:
        if node_name not in workcell.nodes:
            raise ValueError(f"Node {node_name} not in Workcell {workcell.name}")


def validate_step(step: Step, state_handler: WorkcellRedisHandler) -> tuple[bool, str]:
    """Check if a step is valid based on the node's info"""
    if step.node in state_handler.get_all_nodes():
        node = state_handler.get_node(step.node)
        info = node.info
        if info is None:
            return (
                True,
                f"Node {step.node} didn't return proper about information, skipping validation",
            )
        if step.action in info.actions:
            action = info.actions[step.action]
            for action_arg in action.args.values():
                if action_arg.name not in step.args and action_arg.required:
                    return (
                        False,
                        f"Step '{step.name}': Node {step.node}'s action, '{step.action}', is missing arg '{action_arg.name}'",
                    )
                # TODO: Action arg type validation goes here
            for action_file in action.files:
                if action_file.name not in step.files and action_file.required:
                    return (
                        False,
                        f"Step '{step.name}': Node {step.node}'s action, '{step.action}', is missing file '{action_file.name}'",
                    )
            return True, f"Step '{step.name}': Validated successfully"

        return (
            False,
            f"Step '{step.name}': Node {step.node} has no action '{step.action}'",
        )
    return (
        False,
        f"Step '{step.name}': Node {step.node} is not defined in workcell",
    )


def create_workflow(
    workflow_def: WorkflowDefinition,
    workcell: WorkcellDefinition,
    state_handler: WorkcellRedisHandler,
    ownership_info: Optional[OwnershipInfo] = None,
    parameters: Optional[dict[str, Any]] = None,
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
    validate_node_names(workflow_def, workcell)
    wf_dict = workflow_def.model_dump()
    wf_dict.update(
        {
            "label": workflow_def.name,
            "ownership_info": ownership_info.model_dump(mode="json"),
            "parameter_values": parameters,
        }
    )
    wf = Workflow(**wf_dict)
    wf.step_definitions = workflow_def.steps
    steps = []
    for step in workflow_def.steps:
        working_step = deepcopy(step)
        replace_locations(workcell, working_step)
        valid, validation_string = validate_step(
            working_step, state_handler=state_handler
        )
        default_logger.log_info(validation_string)
        if not valid:
            raise ValueError(validation_string)
        steps.append(working_step)

    wf.steps = steps
    wf.submitted_time = datetime.now()
    return wf


def replace_locations(workcell: WorkcellDefinition, step: Step) -> None:
    """Replaces the location names with the location objects"""
    for location_arg, location_name_or_object in step.locations.items():
        if isinstance(location_name_or_object, Location):
            step.locations[location_arg] = location_name_or_object
        elif location_name_or_object in workcell.locations:
            step.locations[location_arg] = workcell.locations[location_name_or_object]
        else:
            raise ValueError(
                f"Location {location_name_or_object} not in Workcell {workcell.name}"
            )


def save_workflow_files(
    working_directory: str, workflow: Workflow, files: list[UploadFile]
) -> Workflow:
    """Saves the files to the workflow run directory,
    and updates the step files to point to the new location"""

    get_workflow_inputs_directory(
        workflow_id=workflow.workflow_id, working_directory=working_directory
    ).expanduser().mkdir(parents=True, exist_ok=True)
    if files:
        for file in files:
            file_path = (
                get_workflow_inputs_directory(
                    working_directory=working_directory,
                    workflow_id=workflow.workflow_id,
                )
                / file.filename
            ).expanduser()
            with Path.open(file_path, "wb") as f:
                f.write(file.file.read())
            for step in workflow.steps:
                for step_file_key, step_file_path in step.files.items():
                    if step_file_path == file.filename:
                        step.files[step_file_key] = str(file_path)
                        default_logger.log_info(
                            f"{step_file_key}: {file_path} ({step_file_path})"
                        )
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


def cancel_workflow(wf: Workflow, state_handler: WorkcellRedisHandler) -> None:
    """Cancels the workflow run"""
    wf.status = WorkflowStatus.CANCELLED
    with state_handler.wc_state_lock():
        state_handler.set_workflow(wf)
    return wf


def cancel_active_workflows(state_handler: WorkcellRedisHandler) -> None:
    """Cancels all currently running workflow runs"""
    for wf in state_handler.get_all_workflows().values():
        if wf.status in [
            WorkflowStatus.RUNNING,
            WorkflowStatus.QUEUED,
            WorkflowStatus.IN_PROGRESS,
        ]:
            cancel_workflow(wf, state_handler=state_handler)
