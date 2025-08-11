"""MADSci Workcell Manager Server."""

import json
import traceback
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, Optional, Union

from fastapi import FastAPI, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.params import Body
from madsci.client.event_client import EventClient
from madsci.client.resource_client import ResourceClient
from madsci.common.ownership import global_ownership_info, ownership_context
from madsci.common.types.action_types import ActionStatus
from madsci.common.types.auth_types import OwnershipInfo
from madsci.common.types.context_types import MadsciContext
from madsci.common.types.event_types import Event, EventType
from madsci.common.types.location_types import Location
from madsci.common.types.node_types import Node
from madsci.common.types.workcell_types import (
    WorkcellDefinition,
    WorkcellManagerSettings,
    WorkcellState,
)
from madsci.common.types.workflow_types import (
    Workflow,
    WorkflowDefinition,
)
from madsci.common.utils import new_ulid_str
from madsci.workcell_manager.state_handler import WorkcellStateHandler
from madsci.workcell_manager.workcell_engine import Engine
from madsci.workcell_manager.workcell_utils import find_node_client
from madsci.workcell_manager.workflow_utils import (
    copy_workflow_files,
    create_workflow,
    save_workflow_files,
)
from pymongo.synchronous.database import Database


def create_workcell_server(  # noqa: C901, PLR0915
    workcell: Optional[WorkcellDefinition] = None,
    workcell_settings: Optional[WorkcellManagerSettings] = None,
    context: Optional[MadsciContext] = None,
    redis_connection: Optional[Any] = None,
    mongo_connection: Optional[Database] = None,
    start_engine: bool = True,
) -> FastAPI:
    """Creates a Workcell Manager's REST server."""

    logger = EventClient()
    workcell_settings = workcell_settings or WorkcellManagerSettings()
    workcell_path = Path(workcell_settings.workcell_definition)
    if not workcell:
        if workcell_path.exists():
            workcell = WorkcellDefinition.from_yaml(workcell_path)
        else:
            name = str(workcell_path.name).split(".")[0]
            workcell = WorkcellDefinition(workcell_name=name)
        logger.info(f"Writing to workcell definition file: {workcell_path}")
        workcell.to_yaml(workcell_path)
    global_ownership_info.workcell_id = workcell.workcell_id
    global_ownership_info.manager_id = workcell.workcell_id
    logger = EventClient(
        name=f"workcell.{workcell.workcell_name}",
    )
    logger.info(workcell)
    context = context or MadsciContext()
    logger.info(context)

    state_handler = WorkcellStateHandler(
        workcell,
        redis_connection=redis_connection,
        mongo_connection=mongo_connection,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):  # noqa: ANN202, ARG001
        """Start the REST server and initialize the state handler and engine"""
        global_ownership_info.workcell_id = workcell.workcell_id
        global_ownership_info.manager_id = workcell.workcell_id

        # LOG WORKCELL START EVENT
        logger.log(
            Event(
                event_type=EventType.WORKCELL_START,
                event_data=workcell.model_dump(mode="json"),
            )
        )

        if start_engine:
            engine = Engine(state_handler)
            engine.spin()
        else:
            with state_handler.wc_state_lock():
                state_handler.initialize_workcell_state(
                    resource_client=ResourceClient()
                )
        try:
            yield
        finally:
            # LOG WORKCELL STOP EVENT
            logger.log(
                Event(
                    event_type=EventType.WORKCELL_STOP,
                    event_data=workcell.model_dump(mode="json"),
                )
            )

    app = FastAPI(
        lifespan=lifespan,
        title=workcell.workcell_name,
        description=workcell.description,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/")
    @app.get("/info")
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
        permanent: bool = False,
    ) -> Union[Node, str]:
        """Add a node to the workcell's node list"""
        if node_name in state_handler.get_nodes():
            return "Node name exists, node names must be unique!"
        node = Node(node_url=node_url)
        state_handler.set_node(node_name, node)
        if permanent:
            workcell = state_handler.get_workcell_definition()
            workcell.nodes[node_name] = node_url
            workcell.to_yaml(workcell_path)
            state_handler.set_workcell_definition(workcell)

        return state_handler.get_node(node_name)

    @app.post("/admin/{command}")
    def send_admin_command(command: str) -> list:
        """Send an admin command to all capable nodes."""
        responses = []
        for node in state_handler.get_nodes().values():
            if command in node.info.capabilities.admin_commands:
                client = find_node_client(node.node_url)
                response = client.send_admin_command(command)
                responses.append(response)
        return responses

    @app.post("/admin/{command}/{node}")
    def send_admin_command_to_node(command: str, node: str) -> list:
        """Send admin command to a node."""
        responses = []
        node = state_handler.get_node(node)
        if command in node.info.capabilities.admin_commands:
            client = find_node_client(node.node_url)
            response = client.send_admin_command(command)
            responses.append(response)
        return responses

    @app.get("/workflows/active")
    def get_active_workflows() -> dict[str, Workflow]:
        """Get active workflows."""
        return state_handler.get_active_workflows()

    @app.get("/workflows/archived")
    def get_archived_workflows(number: int = 20) -> dict[str, Workflow]:
        """Get archived workflows."""
        return state_handler.get_archived_workflows(number)

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
            wf = state_handler.get_active_workflow(workflow_id)
            if wf.status.active:
                if wf.status.running:
                    send_admin_command_to_node(
                        "pause", wf.steps[wf.status.current_step_index].node
                    )
                wf.status.paused = True
                state_handler.set_active_workflow(wf)

        return state_handler.get_active_workflow(workflow_id)

    @app.post("/workflow/{workflow_id}/resume")
    def resume_workflow(workflow_id: str) -> Workflow:
        """Resume a paused workflow."""
        with state_handler.wc_state_lock():
            wf = state_handler.get_active_workflow(workflow_id)
            if wf.status.paused:
                if wf.status.running:
                    send_admin_command_to_node(
                        "resume", wf.steps[wf.status.current_step_index].node
                    )
                wf.status.paused = False
                state_handler.set_active_workflow(wf)
                state_handler.enqueue_workflow(wf.workflow_id)
        return state_handler.get_active_workflow(workflow_id)

    @app.post("/workflow/{workflow_id}/cancel")
    def cancel_workflow(workflow_id: str) -> Workflow:
        """Cancel a specific workflow."""
        with state_handler.wc_state_lock():
            wf = state_handler.get_workflow(workflow_id)
            if wf.status.running:
                send_admin_command_to_node(
                    "cancel", wf.steps[wf.status.current_step_index].node
                )
            wf.status.cancelled = True
            state_handler.set_active_workflow(wf)
        return state_handler.get_active_workflow(workflow_id)

    @app.post("/workflow/{workflow_id}/resubmit")
    def resubmit_workflow(workflow_id: str) -> Workflow:
        """resubmit a previous workflow as a new workflow."""
        with state_handler.wc_state_lock():
            wf = state_handler.get_workflow(workflow_id)
            wf.workflow_id = new_ulid_str()
            wf.status.reset()
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
            state_handler.set_active_workflow(wf)
            state_handler.enqueue_workflow(wf.workflow_id)
        return state_handler.get_active_workflow(wf.workflow_id)

    @app.post("/workflow/{workflow_id}/retry")
    def retry_workflow(workflow_id: str, index: int = -1) -> Workflow:
        """Retry an existing workflow from a specific step."""
        with state_handler.wc_state_lock():
            wf = state_handler.get_workflow(workflow_id)
            if wf.status.terminal:
                index = max(index, 0)
                wf.status.reset(index)
                state_handler.set_active_workflow(wf)
                state_handler.delete_archived_workflow(wf.workflow_id)
                state_handler.enqueue_workflow(wf.workflow_id)
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Workflow is not in a terminal state, cannot retry",
                )
        return state_handler.get_active_workflow(workflow_id)

    @app.post("/workflow")
    async def start_workflow(
        workflow: Annotated[str, Form()],
        ownership_info: Annotated[Optional[str], Form()] = None,
        parameters: Annotated[Optional[str], Form()] = None,
        validate_only: Annotated[Optional[bool], Form()] = False,
        files: list[UploadFile] = [],
    ) -> Workflow:
        """
        Parses the payload and workflow files, and then pushes a workflow job onto the redis queue

        Parameters
        ----------
        workflow: YAML string
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
            with ownership_context(**ownership_info.model_dump(exclude_none=True)):
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
                        state_handler.set_active_workflow(wf)
                        state_handler.enqueue_workflow(wf.workflow_id)

                    logger.log(
                        Event(
                            event_type=EventType.WORKFLOW_START,
                            event_data=wf.model_dump(mode="json"),
                        )
                    )
                return wf

        except HTTPException as e:
            raise e
        except Exception as e:
            logger.error(f"Error starting workflow: {e}")
            traceback.print_exc()
            raise HTTPException(
                status_code=500,
                detail=f"Error starting workflow: {e}",
            ) from e

    @app.get("/locations")
    def get_locations() -> dict[str, Location]:
        """Get the locations of the workcell."""
        return state_handler.get_locations()

    @app.post("/location")
    def add_location(location: Location, permanent: bool = True) -> Location:
        """Add a location to the workcell's location list"""
        with state_handler.wc_state_lock():
            state_handler.set_location(location)
        if permanent:
            workcell = state_handler.get_workcell_definition()
            workcell.locations.append(location)
            workcell.to_yaml(workcell_path)
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
            workcell = state_handler.get_workcell_definition()
            workcell.locations = list(
                filter(
                    lambda location: location.location_id != location_id,
                    workcell.locations,
                )
            )
            workcell.to_yaml(workcell_path)
            state_handler.set_workcell_definition(workcell)
        return {"status": "deleted"}

    @app.post("/location/{location_id}/add_lookup/{node_name}")
    def add_or_update_location_lookup(
        location_id: str,
        node_name: str,
        lookup_val: Any = Body(...),  # noqa: B008
    ) -> Location:
        """Add a lookup value to a locations lookup list"""
        with state_handler.wc_state_lock():
            location = state_handler.get_location(location_id)
            location.lookup[node_name] = lookup_val["lookup_val"]
            state_handler.set_location(location)
        return state_handler.get_location(location.location_id)

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

    return app


if __name__ == "__main__":
    import uvicorn

    workcell_settings = WorkcellManagerSettings()
    app = create_workcell_server(workcell_settings=workcell_settings)
    uvicorn.run(
        app,
        host=workcell_settings.workcell_server_url.host,
        port=workcell_settings.workcell_server_url.port or 8000,
    )
