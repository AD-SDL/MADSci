"""MADSci Workcell Manager Server."""

from fastapi import FastAPI, Form, HTTPException, UploadFile
from fastapi.datastructures import State
from redis_handler import WorkcellRedisHandler

from madsci.workcell_manager.workcell_manager_types import (
    WorkcellManagerDefinition,
)

from madsci.workcell_manager.workflow_utils import create_workflow, save_workflow_files
from madsci.workcell_manager.workcell_utils import find_node_client
from workcell_engine import Engine

from typing import Annotated, Optional
from madsci.common.types.workcell_types import WorkcellDefinition
from madsci.common.types.workflow_types import WorkflowDefinition, Workflow
from madsci.common.types.node_types import Node
import argparse
import json
import traceback


arg_parser = argparse.ArgumentParser()
arg_parser.add_argument(
    "--workcell_file",
    type=str,
    default="./workcells/workcell.yaml",
    help="location of the workcell file",
)
async def lifespan(app: FastAPI) -> None:
    app.state.state_handler=WorkcellRedisHandler(workcell_manager_definition)
    app.state.state_handler.set_workcell(workcell)
    engine = Engine(workcell_manager_definition, app.state.state_handler)
    engine.start_engine_thread()
    yield
app = FastAPI(lifespan=lifespan)

@app.get("/info")
def info() -> WorkcellManagerDefinition:
    """Get information about the resource manager."""
    return workcell_manager_definition

@app.get("/workcell")
def get_workcell() -> WorkcellDefinition:
    """Get information about the resource manager."""
    return app.state.state_handler.get_workcell()

@app.get("/nodes")
def get_nodes() -> dict[str, Node]:
    """Get information about the resource manager."""
    return app.state.state_handler.get_all_nodes()

@app.get("/admin/{command}")
def send_admin_command(command: str) -> list:
    """Get information about the resource manager."""
    responses = []
    for node in app.state.state_handler.get_all_nodes().values():
        if command in node.info.capabilities.admin_commands:
            client = find_node_client(node.node_url)
            response = client.send_admin_command(command)
            responses.append(response)
    return responses

@app.get("/admin/{command}/{node}")
def send_admin_command_to_node(command: str, node: str) -> list:
    """Get information about the resource manager."""
    responses = []
    node = app.state.state_handler.get_node(node)
    if command in node.info.capabilities.admin_commands:
        client = find_node_client(node.node_url)
        response = client.send_admin_command(command)
        responses.append(response)
    return responses


@app.get("/workflows")
def get_workflows() -> dict[str, Workflow]:
    """Get information about the resource manager."""
    return app.state.state_handler.get_all_workflows()

@app.post("/start_workflow")
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
            isinstance(k, str) for k in parameters.keys()
        ):
            raise HTTPException(
                status_code=400, detail="Parameters must be a dictionary with string keys"
            )
    workcell = app.state.state_handler.get_workcell()

    wf = create_workflow(
        workflow_def=wf_def,
        workcell=workcell,
        experiment_id=experiment_id,
        parameters=parameters,
        state_manager=app.state.state_handler
    )

    if not validate_only:
        wf = save_workflow_files(working_directory=workcell_manager_definition.plugin_config.workcell_directory, workflow=wf, files=files)
        with app.state.state_handler.wc_state_lock():
            app.state.state_handler.set_workflow(wf)
    return wf







if __name__ == "__main__":
    import uvicorn
    args =  arg_parser.parse_args()
    workcell_file = args.workcell_file
    workcell = WorkcellDefinition.from_yaml(workcell_file)
    workcell_manager_definition = WorkcellManagerDefinition(
    name="Workcell Manager 1",
    description="The First MADSci Workcell Manager.",
    plugin_config=workcell.config,
    manager_type="workcell_manager"

    )
    uvicorn.run(
        app,
        host=workcell_manager_definition.plugin_config.host,
        port=workcell_manager_definition.plugin_config.port,
    )
