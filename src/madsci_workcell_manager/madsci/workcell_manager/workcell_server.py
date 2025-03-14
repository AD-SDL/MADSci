"""MADSci Workcell Manager Server."""

import json
import traceback
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Annotated, Any, Optional, Union

from fastapi import FastAPI, Form, HTTPException, UploadFile
from madsci.common.types.action_types import ActionStatus
from madsci.common.types.auth_types import OwnershipInfo
from madsci.common.types.base_types import new_ulid_str
from madsci.common.types.node_types import Node, NodeDefinition
from madsci.common.types.workcell_types import WorkcellDefinition
from madsci.common.types.workflow_types import (
    Workflow,
    WorkflowDefinition,
    WorkflowStatus,
)
from madsci.workcell_manager.redis_handler import WorkcellRedisHandler
from madsci.workcell_manager.workcell_engine import Engine
from madsci.workcell_manager.workcell_utils import find_node_client
from madsci.workcell_manager.workflow_utils import (
    copy_workflow_files,
    create_workflow,
    save_workflow_files,
)


def create_workcell_server(  # noqa: C901, PLR0915
    workcell: WorkcellDefinition,
    redis_connection: Optional[Any] = None,
    start_engine: bool = True,
) -> FastAPI:
    """Creates a Workcell Manager's REST server."""

    state_handler = WorkcellRedisHandler(workcell, redis_connection=redis_connection)

    @asynccontextmanager
    async def lifespan(app: FastAPI):  # noqa: ANN202, ARG001
        """Start the REST server and initialize the state handler and engine"""
        state_handler.set_workcell(workcell)
        if start_engine:
            engine = Engine(workcell, state_handler)
            engine.start_engine_thread()
        yield

    app = FastAPI(lifespan=lifespan)

    @app.get("/definition")
    @app.get("/workcell")
    def get_workcell() -> WorkcellDefinition:
        """Get the currently running workcell."""
        return state_handler.get_workcell()

    @app.get("/state")
    def get_state() -> dict:
        """Get the current state of the workcell."""
        return state_handler.get_state()

    @app.get("/nodes")
    def get_nodes() -> dict[str, Node]:
        """Get info on the nodes in the workcell."""
        return state_handler.get_all_nodes()

    @app.get("/nodes/{node_name}")
    def get_node(node_name: str) -> Union[Node, str]:
        """Get information about about a specific node."""
        try:
            node = state_handler.get_node(node_name)
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
        """Add a node to the workcell's node list"""
        if node_name in state_handler.get_all_nodes():
            return "Node name exists, node names must be unique!"
        node = Node(node_url=node_url)
        state_handler.set_node(node_name, node)
        if permanent:
            workcell.nodes[node_name] = NodeDefinition(
                node_name=node_name,
                node_url=node_url,
                node_description=node_description,
            )
            workcell.to_yaml(workcell._definition_path)
        return state_handler.get_node(node_name)

    @app.get("/admin/{command}")
    def send_admin_command(command: str) -> list:
        """Send an admin command to all capable nodes."""
        responses = []
        for node in state_handler.get_all_nodes().values():
            if command in node.info.capabilities.admin_commands:
                client = find_node_client(node.node_url)
                response = client.send_admin_command(command)
                responses.append(response)
        return responses

    @app.get("/admin/{command}/{node}")
    def send_admin_command_to_node(command: str, node: str) -> list:
        """Send admin command to a node."""
        responses = []
        node = state_handler.get_node(node)
        if command in node.info.capabilities.admin_commands:
            client = find_node_client(node.node_url)
            response = client.send_admin_command(command)
            responses.append(response)
        return responses

    @app.get("/workflows")
    def get_all_workflows() -> dict[str, Workflow]:
        """get all workflows."""
        return state_handler.get_all_workflows()

    @app.get("/workflows/{workflow_id}")
    def get_workflow(workflow_id: str) -> Workflow:
        """Get info on a specific workflow."""
        return state_handler.get_workflow(workflow_id)

    @app.post("/workflows/pause/{workflow_id}")
    def pause_workflow(workflow_id: str) -> Workflow:
        """Pause a specific workflow."""
        with state_handler.wc_state_lock():
            wf = state_handler.get_workflow(workflow_id)
            if wf.status in ["running", "in_progress", "queued"]:
                if wf.status == "running":
                    send_admin_command_to_node("pause", wf.steps[wf.step_index].node)
                    wf.steps[wf.step_index] = ActionStatus.PAUSED
                wf.paused = True
                state_handler.set_workflow(wf)

        return state_handler.get_workflow(workflow_id)

    @app.post("/workflows/resume/{workflow_id}")
    def resume_workflow(workflow_id: str) -> Workflow:
        """Resume a paused workflow."""
        with state_handler.wc_state_lock():
            wf = state_handler.get_workflow(workflow_id)
            if wf.paused:
                if wf.status == "running":
                    send_admin_command_to_node("resume", wf.steps[wf.step_index].node)
                    wf.steps[wf.step_index] = ActionStatus.RUNNING
                wf.paused = False
                state_handler.set_workflow(wf)
        return state_handler.get_workflow(workflow_id)

    @app.post("/workflows/cancel/{workflow_id}")
    def cancel_workflow(workflow_id: str) -> Workflow:
        """Cancel a specific workflow."""
        with state_handler.wc_state_lock():
            wf = state_handler.get_workflow(workflow_id)
            if wf.status == "running":
                send_admin_command_to_node("stop", wf.steps[wf.step_index].node)
                wf.steps[wf.step_index] = ActionStatus.CANCELLED
            wf.status = WorkflowStatus.CANCELLED
            state_handler.set_workflow(wf)
        return state_handler.get_workflow(workflow_id)

    @app.post("/workflows/resubmit/{workflow_id}")
    def resubmit_workflow(workflow_id: str) -> Workflow:
        """resubmit a previous workflow as a new workflow."""
        with state_handler.wc_state_lock():
            wf = state_handler.get_workflow(workflow_id)
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
                working_directory=workcell.workcell_directory,
            )
            state_handler.set_workflow(wf)
        return state_handler.get_workflow(wf.workflow_id)

    @app.post("/workflows/retry/{workflow_id}")
    def retry_workflow(workflow_id: str, index: int = -1) -> Workflow:
        """Retry an existing workflow from a specific step."""
        with state_handler.wc_state_lock():
            wf = state_handler.get_workflow(workflow_id)
            if wf.status in [
                WorkflowStatus.COMPLETED,
                WorkflowStatus.FAILED,
                WorkflowStatus.CANCELLED,
            ]:
                if index >= 0:
                    wf.step_index = index
                wf.status = WorkflowStatus.QUEUED
                state_handler.set_workflow(wf)
        return state_handler.get_workflow(workflow_id)

    @app.post("/workflows/start")
    async def start_workflow(
        workflow: Annotated[str, Form()],
        ownership_info: Annotated[Optional[str], Form()] = None,
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
        ownership_info: Optional[OwnershipInfo]
        - Information about the experiments, users, etc. that own this workflow
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

        if ownership_info is None:
            ownership_info = OwnershipInfo()
        else:
            ownership_info = OwnershipInfo.model_validate_json(ownership_info)

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
        workcell = state_handler.get_workcell()

        wf = create_workflow(
            workflow_def=wf_def,
            workcell=workcell,
            ownership_info=ownership_info,
            parameters=parameters,
            state_handler=state_handler,
        )

        if not validate_only:
            wf = save_workflow_files(
                working_directory=workcell.workcell_directory,
                workflow=wf,
                files=files,
            )
            with state_handler.wc_state_lock():
                state_handler.set_workflow(wf)
        return wf

    return app


if __name__ == "__main__":
    import uvicorn

    workcell = None
    workcell = WorkcellDefinition.load_model(require_unique=True)
    if workcell is None:
        raise ValueError(
            "No workcell manager definition found, please specify a path with --definition, or add it to your lab definition's 'managers' section"
        )
    app = create_workcell_server(workcell)
    uvicorn.run(
        app,
        host=workcell.config.host,
        port=workcell.config.port,
    )
