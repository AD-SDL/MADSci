"""MADSci Workcell Manager Server."""

import argparse
import json
import traceback
from datetime import datetime
from typing import Annotated, Optional, Union

from fastapi import FastAPI, Form, HTTPException, UploadFile
from madsci.common.types.action_types import ActionStatus
from madsci.common.types.base_types import new_ulid_str
from madsci.common.types.node_types import Node, NodeDefinition
from madsci.common.types.workcell_types import WorkcellDefinition
from madsci.common.types.workflow_types import (
    Workflow,
    WorkflowDefinition,
    WorkflowStatus,
)
from madsci.workcell_manager.workcell_manager_types import (
    WorkcellManagerDefinition,
)
from madsci.workcell_manager.workcell_utils import find_node_client
from madsci.workcell_manager.workflow_utils import (
    copy_workflow_files,
    create_workflow,
    save_workflow_files,
)
from redis_handler import WorkcellRedisHandler
from workcell_engine import Engine

arg_parser = argparse.ArgumentParser()
arg_parser.add_argument(
    "--workcell_file",
    type=str,
    default="./workcells/workcell.yaml",
    help="location of the workcell file",
)


async def lifespan(app: FastAPI) -> None:
    """start the server functionality and initialize the state handler"""
    app.state.state_handler = WorkcellRedisHandler(workcell_manager_definition)
    app.state.state_handler.set_workcell(workcell)
    engine = Engine(workcell_manager_definition, app.state.state_handler)
    engine.start_engine_thread()
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/info")
def info() -> WorkcellManagerDefinition:
    """Get information about the workcell manager."""
    return workcell_manager_definition


@app.get("/workcell")
def get_workcell() -> WorkcellDefinition:
    """Get the currently running workcell."""
    return app.state.state_handler.get_workcell()


@app.get("/nodes")
def get_nodes() -> dict[str, Node]:
    """Get info on the nodes in the workcell."""
    return app.state.state_handler.get_all_nodes()


@app.get("/nodes/{node_name}")
def get_node(node_name: str) -> Union[Node, str]:
    """Get information about about a specific node."""
    try:
        node = app.state.state_handler.get_node(node_name)
    except Exception:
        return "Node not found!"
    return node


@app.post("/nodes/add_node")
def add_node(
    node_name: str,
    node_url: str,
    node_description: str = "A Node",
    permanent: bool = False,
) -> Union[Node, str]:
    """Add a node to the workcells nodes"""
    if node_name in app.state.state_handler.get_all_nodes():
        return "Node name exists, node names must be unique!"
    node = Node(node_url=node_url)
    app.state.state_handler.set_node(node_name, node)
    if permanent:
        workcell.nodes[node_name] = NodeDefinition(
            node_name=node_name, node_url=node_url, node_description=node_description
        )
        workcell.to_yaml(workcell_file)
    return app.state.state_handler.get_node(node_name)


# TODO add node reserve endpoint


@app.get("/admin/{command}")
def send_admin_command(command: str) -> list:
    """Send an admin command to all capable nodes."""
    responses = []
    for node in app.state.state_handler.get_all_nodes().values():
        if command in node.info.capabilities.admin_commands:
            client = find_node_client(node.node_url)
            response = client.send_admin_command(command)
            responses.append(response)
    return responses


@app.get("/admin/{command}/{node}")
def send_admin_command_to_node(command: str, node: str) -> list:
    """Send admin command to a node."""
    responses = []
    node = app.state.state_handler.get_node(node)
    if command in node.info.capabilities.admin_commands:
        client = find_node_client(node.node_url)
        response = client.send_admin_command(command)
        responses.append(response)
    return responses


@app.get("/workflows")
def get_all_workflows() -> dict[str, Workflow]:
    """get all workflows."""
    return app.state.state_handler.get_all_workflows()


@app.get("/workflows/{workflow_id}")
def get_workflow(workflow_id: str) -> Workflow:
    """Get info on a specific workflow."""
    return app.state.state_handler.get_workflow(workflow_id)


@app.get("/workflows/pause/{workflow_id}")
def pause_workflow(workflow_id: str) -> Workflow:
    """Pause a specific workflow."""
    with app.state.state_handler.wc_state_lock():
        wf = app.state.state_handler.get_workflow(workflow_id)
        if wf.status in ["running", "in_progress", "queued"]:
            if wf.status == "running":
                send_admin_command_to_node("pause", wf.steps[wf.step_index].node)
                wf.steps[wf.step_index] = ActionStatus.PAUSED
            wf.paused = True
            app.state.state_handler.set_workflow(wf)

    return app.state.state_handler.get_workflow(workflow_id)


@app.get("/workflows/resume/{workflow_id}")
def resume_workflow(workflow_id: str) -> Workflow:
    """Resume a paused workflow."""
    with app.state.state_handler.wc_state_lock():
        wf = app.state.state_handler.get_workflow(workflow_id)
        if wf.paused:
            if wf.status == "running":
                send_admin_command_to_node("resume", wf.steps[wf.step_index].node)
                wf.steps[wf.step_index] = ActionStatus.RUNNING
            wf.paused = False
            app.state.state_handler.set_workflow(wf)
    return app.state.state_handler.get_workflow(workflow_id)


@app.get("/workflows/cancel/{workflow_id}")
def cancel_workflow(workflow_id: str) -> Workflow:
    """Cancel a specific workflow."""
    with app.state.state_handler.wc_state_lock():
        wf = app.state.state_handler.get_workflow(workflow_id)
        if wf.status == "running":
            send_admin_command_to_node("stop", wf.steps[wf.step_index].node)
            wf.steps[wf.step_index] = ActionStatus.CANCELLED
        wf.status = WorkflowStatus.CANCELLED
        app.state.state_handler.set_workflow(wf)
    return app.state.state_handler.get_workflow(workflow_id)


@app.get("/workflows/resubmit/{workflow_id}")
def resubmit_workflow(workflow_id: str) -> Workflow:
    """resubmit a previous workflow as a new workflow."""
    with app.state.state_handler.wc_state_lock():
        wf = app.state.state_handler.get_workflow(workflow_id)
        wf.workflow_id = new_ulid_str()
        wf.step_index = 0
        wf.start_time = None
        wf.end_time = None
        wf.submitted_time = datetime.now()
        for step in wf.steps:
            step.step_id = new_ulid_str()
            step.start_time = None
            step.end_time = None
            step.status = ActionStatus.NOT_STARTED
        copy_workflow_files(
            old_id=workflow_id,
            workflow=wf,
            working_directory=workcell_manager_definition.plugin_config.workcell_directory,
        )
        app.state.state_handler.set_workflow(wf)
    return app.state.state_handler.get_workflow(workflow_id)


@app.post("/workflows/retry")
def retry_workflow(workflow_id: str, index: int = -1) -> Workflow:
    """Retry an existing workflow from a specific step."""
    with app.state.state_handler.wc_state_lock():
        wf = app.state.state_handler.get_workflow(workflow_id)
        if wf.status in ["completed", "failed"]:
            if index >= 0:
                wf.step_index = index
            wf.status = WorkflowStatus.QUEUED
            app.state.state_handler.set_workflow(wf)
    return app.state.state_handler.get_workflow(workflow_id)


@app.post("/workflows/start")
async def start_workflow(
    workflow: Annotated[str, Form()],
    experiment_id: Annotated[Optional[str], Form()] = None,
    parameters: Annotated[Optional[str], Form()] = None,
    validate_only: Annotated[Optional[bool], Form()] = False,
    files: list[UploadFile] = [],
) -> Workflow:
    """
    parses the payload and workflow files, and then pushes a workflow job onto the redis queue

    Parameters
    ----------
    workflow: UploadFile
    - The workflow yaml file
    parameters: Optional[Dict[str, Any]] = {}
    - Dynamic values to insert into the workflow file
    experiment_id: str
    - The id of the experiment this workflow is associated with
    simulate: bool
    - whether to use real robots or not
    validate_only: bool
    - whether to validate the workflow without queueing it

    Returns
    -------
    response: Workflow
    - a workflow run object for the requested run_id
    """
    try:
        wf_def = WorkflowDefinition.model_validate_json(workflow)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=422, detail=str(e)) from e

    if parameters is None:
        parameters = {}
    else:
        parameters = json.loads(parameters)
        if not isinstance(parameters, dict) or not all(
            isinstance(k, str) for k in parameters
        ):
            raise HTTPException(
                status_code=400,
                detail="Parameters must be a dictionary with string keys",
            )
    workcell = app.state.state_handler.get_workcell()

    wf = create_workflow(
        workflow_def=wf_def,
        workcell=workcell,
        experiment_id=experiment_id,
        parameters=parameters,
        state_handler=app.state.state_handler,
    )

    if not validate_only:
        wf = save_workflow_files(
            working_directory=workcell_manager_definition.plugin_config.workcell_directory,
            workflow=wf,
            files=files,
        )
        with app.state.state_handler.wc_state_lock():
            app.state.state_handler.set_workflow(wf)
    return wf


# TODO add reserv nodes endpoint


if __name__ == "__main__":
    import uvicorn

    args = arg_parser.parse_args()
    workcell_file = args.workcell_file
    workcell = WorkcellDefinition.from_yaml(workcell_file)
    workcell_manager_definition = WorkcellManagerDefinition(
        name="Workcell Manager 1",
        description="The First MADSci Workcell Manager.",
        plugin_config=workcell.config,
        manager_type="workcell_manager",
    )
    uvicorn.run(
        app,
        host=workcell_manager_definition.plugin_config.host,
        port=workcell_manager_definition.plugin_config.port,
    )
