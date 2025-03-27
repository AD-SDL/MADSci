"""MADSci Workcell Manager Server."""

import json
import traceback
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Annotated, Any, Optional, Union

from fastapi import FastAPI, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from madsci.client.event_client import EventClient
from madsci.client.resource_client import ResourceClient
from madsci.common.types.action_types import ActionStatus
from madsci.common.types.auth_types import OwnershipInfo
from madsci.common.types.base_types import new_ulid_str
from madsci.common.types.location_types import Location
from madsci.common.types.node_types import Node, NodeDefinition
from madsci.common.types.workcell_types import WorkcellDefinition, WorkcellState
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
        if start_engine:
            engine = Engine(state_handler)
            engine.spin()
        else:
            with state_handler.wc_state_lock():
                state_handler.initialize_workcell_state(
                    resource_client=ResourceClient(
                        url=workcell.config.resource_server_url
                    )
                    if workcell.config.resource_server_url is not None
                    else None,
                )
        yield

    app = FastAPI(lifespan=lifespan)

    @app.get("/definition")
    @app.get("/workcell")
    def get_workcell() -> WorkcellDefinition:
        """Get the currently running workcell."""
        return state_handler.get_workcell_definition()

    @app.get("/state")
    def get_state() -> WorkcellState:
        """Get the current state of the workcell."""
        return state_handler.get_workcell_state()

    @app.get("/nodes")
    def get_nodes() -> dict[str, Node]:
        """Get info on the nodes in the workcell."""
        return state_handler.get_nodes()

    @app.get("/node/{node_name}")
    def get_node(node_name: str) -> Union[Node, str]:
        """Get information about about a specific node."""
        try:
            node = state_handler.get_node(node_name)
        except Exception:
            return "Node not found!"
        return node

    @app.post("/node")
    def add_node(
        node_name: str,
        node_url: str,
        node_description: str = "A Node",
        permanent: bool = False,
    ) -> Union[Node, str]:
        """Add a node to the workcell's node list"""
        if node_name in state_handler.get_nodes():
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
        for node in state_handler.get_nodes().values():
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
    def get_workflows() -> dict[str, Workflow]:
        """Get all workflows."""
        return state_handler.get_workflows()

    @app.get("/workflows/queue")
    def get_workflow_queue() -> list[Workflow]:
        """Get all queued workflows."""
        return state_handler.get_workflow_queue()

    @app.get("/workflow/{workflow_id}")
    def get_workflow(workflow_id: str) -> Workflow:
        """Get info on a specific workflow."""
        return state_handler.get_workflow(workflow_id)

    @app.post("/workflow/{workflow_id}/pause")
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

    @app.post("/workflow/{workflow_id}/resume")
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

    @app.post("/workflow/{workflow_id}/cancel")
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

    @app.post("/workflow/{workflow_id}/resubmit")
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

    @app.post("/workflow/{workflow_id}/retry")
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

    @app.post("/workflow")
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

        ownership_info = (
            OwnershipInfo.model_validate_json(ownership_info)
            if ownership_info
            else OwnershipInfo()
        )

        if parameters is None or parameters == "":
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
        workcell = state_handler.get_workcell_definition()
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

    @app.get("/locations")
    def get_locations() -> dict[str, Location]:
        """Get the locations of the workcell."""
        return state_handler.get_locations()

    @app.post("/location")
    def add_location(
        location: Location,
    ) -> Location:
        """Add a location to the workcell's location list"""
        with state_handler.wc_state_lock():
            state_handler.set_location(location)
        return state_handler.get_location(location.location_id)

    @app.get("/location/{location_id}")
    def get_location(location_id: str) -> Location:
        """Get information about about a specific location."""
        return state_handler.get_location(location_id)

    @app.delete("/location/{location_id}")
    def delete_location(location_id: str) -> dict:
        """Delete a location from the workcell's location list"""
        with state_handler.wc_state_lock():
            state_handler.delete_location(location_id)
        return {"status": "deleted"}

    @app.post("/location/{location_id}/attach_resource")
    def add_resource_to_location(
        location_id: str,
        resource_id: str,
    ) -> Location:
        """Attach a resource container to a location."""
        with state_handler.wc_state_lock():
            location = state_handler.get_location(location_id)
            location.resource_id = resource_id
            state_handler.set_location(location)
        return state_handler.get_location(location_id)

    if workcell.config.static_files_path is not None:
        try:
            app.mount(
                "/", StaticFiles(directory=workcell.config.static_files_path, html=True)
            )
        except Exception:
            EventClient(workcell.config.event_client_config).log_error(
                f"Error mounting static files: {workcell.config.static_files_path}"
            )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

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
