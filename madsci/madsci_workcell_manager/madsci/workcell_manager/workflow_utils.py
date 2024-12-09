"""Utility function for the workcell manager."""
from madsci.common.types.workcell_types import WorkcellDefinition
from madsci.common.types.workflow_types import Workflow, WorkflowDefinition
from madsci.common.types.step_types import Step
from madsci.common.types.node_types import Node
from typing import Optional, Any
from fastapi import UploadFile

def find_step_node(workcell: WorkcellDefinition, step_module: str) -> Optional[Node]:
    """finds the full module information based on just its name

    Parameters
    ----------
    step_module : str
        the name of the module
    Returns
    -------
    module: Module
        The class with full information about the given module
    """
    for node in workcell.nodes:
        node_name = node.name
        if node_name == step_module:
            return node

    raise ValueError(f"Module {step_module} not in Workcell {workcell.name}")

def validate_node_names(workflow: Workflow, workcell: WorkcellDefinition) -> None:
    """
    Validates that the nodes in the workflow.flowdef are in the workcell.modules
    """
    [
        find_step_node(workcell, node_name)
        for node_name in [step.node for step in workflow.flowdef]
    ]
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
            "parameters": parameters,
            "experiment_id": experiment_id,
            "simulate": simulate,
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
def save_workflow_files(wf: Workflow, files: list[UploadFile]) -> Workflow:
    """Saves the files to the workflow run directory,
    and updates the step files to point to the new location"""

    return wf
