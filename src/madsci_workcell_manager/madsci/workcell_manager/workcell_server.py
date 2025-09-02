"""MADSci Workcell Manager Server."""

import json
import traceback
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any, Optional, Union

from fastapi import FastAPI, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.params import Body
from madsci.client.data_client import DataClient
from madsci.client.event_client import EventClient
from madsci.client.resource_client import ResourceClient
from madsci.common.context import get_current_madsci_context
from madsci.common.ownership import global_ownership_info, ownership_context
from madsci.common.types.auth_types import OwnershipInfo
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
from madsci.workcell_manager.state_handler import WorkcellStateHandler
from madsci.workcell_manager.workcell_engine import Engine
from madsci.workcell_manager.workcell_utils import find_node_client
from madsci.workcell_manager.workflow_utils import (
    check_parameters,
    # validate_workflow_definition,
    create_workflow,
    save_workflow_files,
)
from pymongo.synchronous.database import Database
from ulid import ULID


def create_workcell_server(  # noqa: C901, PLR0915
    workcell: Optional[WorkcellDefinition] = None,
    workcell_settings: Optional[WorkcellManagerSettings] = None,
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
    logger.info(get_current_madsci_context())

    state_handler = WorkcellStateHandler(
        workcell,
        redis_connection=redis_connection,
        mongo_connection=mongo_connection,
    )
    context = get_current_madsci_context()

    data_client = DataClient(context.data_server_url)

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
            engine = Engine(state_handler, data_client)
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
            if workcell_path.exists():
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

    @app.post("/workflow/{workflow_id}/retry")
    def retry_workflow(workflow_id: str, index: int = -1) -> Workflow:
        """Retry an existing workflow from a specific step."""
        with state_handler.wc_state_lock():
            wf = state_handler.get_workflow(workflow_id)
            if wf.status.terminal:
                if index < 0:
                    index = wf.status.current_step_index
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

    @app.post("/workflow_definition")
    async def submit_workflow_definition(
        workflow_definition: WorkflowDefinition,
    ) -> str:
        """
        Parses the payload and workflow files, and then pushes a workflow job onto the redis queue

        Parameters
        ----------
        workflow_definition: YAML string
        - The workflow_definition yaml file


        Returns
        -------
        response: Workflow Definition ID
        - the workflow definition ID
        """
        try:
            try:
                wf_def = WorkflowDefinition.model_validate(workflow_definition)

            except Exception as e:
                traceback.print_exc()
                raise HTTPException(status_code=422, detail=str(e)) from e
            # TODO: Validation
            return state_handler.save_workflow_definition(
                workflow_definition=wf_def,
            )
        except HTTPException as e:
            raise e
        except Exception as e:
            logger.error(f"Error saving workflow definition: {e}")
            traceback.print_exc()
            raise HTTPException(
                status_code=500,
                detail=f"Error saving workflow definition: {e}",
            ) from e

    @app.get("/workflow_definition/{workflow_definition_id}")
    async def get_workflow_definition(
        workflow_definition_id: str,
    ) -> WorkflowDefinition:
        """
        Parses the payload and workflow files, and then pushes a workflow job onto the redis queue

        Parameters
        ----------
        Workflow Definition ID: str
        - the workflow definition ID

        Returns
        -------
        response: WorkflowDefinition
        - a workflow run object for the requested run_id
        """
        try:
            return state_handler.get_workflow_definition(workflow_definition_id)
        except Exception as e:
            traceback.print_exc()
            raise HTTPException(status_code=404, detail=str(e)) from e

    @app.post("/workflow")
    async def start_workflow(
        workflow_definition_id: Annotated[str, Form()],
        ownership_info: Annotated[Optional[str], Form()] = None,
        input_values: Annotated[Optional[str], Form()] = None,
        input_file_paths: Annotated[Optional[str], Form()] = None,
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
                workflow_id = ULID.from_str(workflow_definition_id)
                wf_def = state_handler.get_workflow_definition(str(workflow_id))

            except Exception as e:
                traceback.print_exc()
                raise HTTPException(status_code=422, detail=str(e)) from e

            ownership_info = (
                OwnershipInfo.model_validate_json(ownership_info)
                if ownership_info
                else OwnershipInfo()
            )
            with ownership_context(**ownership_info.model_dump(exclude_none=True)):
                if input_values is None or input_values == "":
                    input_values = {}
                else:
                    input_values = json.loads(input_values)
                    if not isinstance(input_values, dict) or not all(
                        isinstance(k, str) for k in input_values
                    ):
                        raise HTTPException(
                            status_code=400,
                            detail="Parameters must be a dictionary with string keys",
                        )
                if input_file_paths is None or input_file_paths == "":
                    input_file_paths = {}
                else:
                    input_file_paths = json.loads(input_file_paths)
                    if not isinstance(input_file_paths, dict) or not all(
                        isinstance(k, str) for k in input_file_paths
                    ):
                        raise HTTPException(
                            status_code=400,
                            detail="Input File Paths must be a dictionary with string keys",
                        )
                workcell = state_handler.get_workcell_definition()
                check_parameters(wf_def, input_values)
                wf = create_workflow(
                    workflow_def=wf_def,
                    workcell=workcell,
                    input_values=input_values,
                    input_file_paths=input_file_paths,
                    data_client=data_client,
                    state_handler=state_handler,
                )

                wf = save_workflow_files(
                    workflow=wf, files=files, data_client=data_client
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
            if workcell_path.exists():
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
            if workcell_path.exists():
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
