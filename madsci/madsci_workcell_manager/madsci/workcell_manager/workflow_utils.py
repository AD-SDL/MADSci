"""Utility function for the workcell manager."""
from madsci.common.types.workcell_types import WorkcellDefinition
from madsci.common.types.workflow_types import Workflow, WorkflowDefinition, WorkflowStatus
from madsci.common.types.step_types import Step
from madsci.common.types.node_types import Node
from redis_handler import WorkcellRedisHandler
from typing import Optional, Any
from fastapi import UploadFile
import re
import copy
from pathlib import Path


def validate_node_names(workflow: Workflow, workcell: WorkcellDefinition) -> None:
    """
    Validates that the nodes in the workflow.flowdef are in the workcell.modules
    """
    for node_name in [step.node for step in workflow.flowdef]:
        if not node_name in workcell.nodes:
             raise ValueError(f"Node {node_name} not in Workcell {workcell.name}")

def replace_positions(workcell: WorkcellDefinition, step: Step):
    """Allow the user to put location names instead of """
    pass

def validate_step(step: Step) -> tuple[bool, str]:
    """Check if a step is valid based on the node's info"""
    return (True, "")

def create_workflow(
    workflow_def: WorkflowDefinition,
    workcell: WorkcellDefinition,
    experiment_id: Optional[str] = None,
    parameters: Optional[dict[str, Any]] = None,
    simulate: bool = False,
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

    experiment_path: PathLike
        The path to the data of the experiment for the workflow

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
            "experiment_id": experiment_id,
            "simulate": simulate,
            "parameter_values": parameters
        }
    )
    wf = Workflow(**wf_dict)

    steps = []
    for step in workflow_def.flowdef:
        replace_positions(workcell, step)
        valid, validation_string = validate_step(step)
        print(validation_string)
        if not valid:
            raise ValueError(validation_string)
        steps.append(step)

    wf.steps = steps

    return wf

def save_workflow_files(working_directory: str, workflow: Workflow, files: list[UploadFile]) -> Workflow:
    """Saves the files to the workflow run directory,
    and updates the step files to point to the new location"""

    get_workflow_inputs_directory(
        workflow_run_id=workflow.run_id,
        working_directory=working_directory
    ).mkdir(parents=True, exist_ok=True)
    if files:
        for file in files:
            file_path = (
                get_workflow_inputs_directory(
                    working_directory=working_directory,
                    workflow_run_id=workflow.run_id,
                )
                / file.filename
            )
            with Path.open(file_path, "wb") as f:
                f.write(file.file.read())
            for step in workflow.steps:
                for step_file_key, step_file_path in step.files.items():
                    if step_file_path == file.filename:
                        step.files[step_file_key] = str(file_path)
                        print(f"{step_file_key}: {file_path} ({step_file_path})")
    return workflow

def get_workflow_inputs_directory(workflow_run_id: str = None, working_directory: str = None) -> Path:
    """returns a directory name for the workflows inputs"""
    return Path(working_directory) / "Workflows" / workflow_run_id / "Inputs"


def cancel_workflow(wf: Workflow, state_manager: WorkcellRedisHandler) -> None:
    """Cancels the workflow run"""
    wf.scheduler_metadata.status = WorkflowStatus.CANCELLED
    with state_manager.wc_state_lock():
        state_manager.set_workflow_run(wf)
    return wf


def cancel_active_workflows(state_manager: WorkcellRedisHandler) -> None:
    """Cancels all currently running workflow runs"""
    for wf in state_manager.get_all_workflows().values():
        if wf.scheduler_metadata.status in [
            WorkflowStatus.RUNNING,
            WorkflowStatus.QUEUED,
            WorkflowStatus.IN_PROGRESS,
        ]:
            cancel_workflow(wf)
