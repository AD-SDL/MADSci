"""MADSci Workcell Manager using AbstractManagerBase."""

import json
import traceback
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any, AsyncGenerator, Optional, Union

from classy_fastapi import get, post
from fastapi import FastAPI, Form, HTTPException, UploadFile
from fastapi.params import Body
from madsci.client.data_client import DataClient
from madsci.client.location_client import LocationClient
from madsci.common.context import get_current_madsci_context
from madsci.common.manager_base import AbstractManagerBase
from madsci.common.mongodb_version_checker import MongoDBVersionChecker
from madsci.common.ownership import global_ownership_info, ownership_context
from madsci.common.types.admin_command_types import AdminCommandResponse
from madsci.common.types.auth_types import OwnershipInfo
from madsci.common.types.event_types import Event, EventType
from madsci.common.types.node_types import Node
from madsci.common.types.workcell_types import (
    WorkcellManagerDefinition,
    WorkcellManagerHealth,
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
    create_workflow,
    save_workflow_files,
)
from pymongo.synchronous.database import Database
from ulid import ULID

# Module-level constants for Body() calls to avoid B008 linting errors
LOOKUP_VAL_BODY = Body(...)


class WorkcellManager(
    AbstractManagerBase[WorkcellManagerSettings, WorkcellManagerDefinition]
):
    """MADSci Workcell Manager using the new AbstractManagerBase pattern."""

    SETTINGS_CLASS = WorkcellManagerSettings
    DEFINITION_CLASS = WorkcellManagerDefinition

    def __init__(
        self,
        settings: Optional[WorkcellManagerSettings] = None,
        definition: Optional[WorkcellManagerDefinition] = None,
        redis_connection: Optional[Any] = None,
        mongo_connection: Optional[Database] = None,
        start_engine: bool = True,
        **kwargs: Any,
    ) -> None:
        """Initialize the WorkcellManager."""
        self.redis_connection = redis_connection
        self.mongo_connection = mongo_connection
        self.start_engine = start_engine

        super().__init__(settings=settings, definition=definition, **kwargs)

    def create_default_definition(self) -> WorkcellManagerDefinition:
        """Create a default definition instance for this manager."""
        name = str(self.get_definition_path().name).split(".")[0]
        return WorkcellManagerDefinition(name=name)

    def initialize(self, **kwargs: Any) -> None:
        """Initialize manager-specific components."""
        super().initialize(**kwargs)

        # Skip version validation if external mongo_connection was provided (e.g., in tests)
        # This is commonly done in tests where a mock or containerized MongoDB is used
        if self.mongo_connection is not None:
            # External connection provided, likely in test context - skip version validation
            self.logger.info(
                "External mongo_connection provided, skipping MongoDB version validation"
            )
            # Continue with the rest of initialization (ownership, state handler, clients)
            global_ownership_info.workcell_id = self.definition.manager_id
            global_ownership_info.manager_id = self.definition.manager_id

            # Initialize state handler
            self.state_handler = WorkcellStateHandler(
                self.definition,
                workcell_settings=self.settings,
                redis_connection=self.redis_connection,
                mongo_connection=self.mongo_connection,
            )

            # Initialize clients
            context = get_current_madsci_context()
            self.data_client = DataClient(context.data_server_url)
            self.location_client = LocationClient(context.location_server_url)
            return

        # DATABASE VERSION VALIDATION - MongoDB version checking
        self.logger.info("Validating MongoDB schema version...")
        version_checker = None
        try:
            # Get schema file path relative to this module
            schema_file_path = Path(__file__).parent / "schema.json"

            version_checker = MongoDBVersionChecker(
                db_url=self.settings.mongo_url or "mongodb://localhost:27017",
                database_name="workcell_manager",
                schema_file_path=str(schema_file_path),
                logger=self.logger,
            )
            version_checker.validate_or_fail()
            self.logger.info("MongoDB version validation completed successfully")
        except RuntimeError as e:
            if "needs version tracking initialization" in str(e):
                self.logger.error(
                    "DATABASE INITIALIZATION REQUIRED! SERVER STARTUP ABORTED! "
                    "The database exists but needs version tracking setup."
                )
            else:
                self.logger.error(
                    "DATABASE VERSION MISMATCH DETECTED! SERVER STARTUP ABORTED! "
                    "Please run the migration tool before starting the server."
                )
            self.logger.error(
                "\nTo resolve this issue, run the migration tool and restart the server."
            )
            raise

        # Set up global ownership
        global_ownership_info.workcell_id = self.definition.manager_id
        global_ownership_info.manager_id = self.definition.manager_id

        # Initialize state handler
        self.state_handler = WorkcellStateHandler(
            self.definition,
            workcell_settings=self.settings,
            redis_connection=self.redis_connection,
            mongo_connection=self.mongo_connection,
        )

        # Initialize clients
        context = get_current_madsci_context()
        self.data_client = DataClient(context.data_server_url)
        self.location_client = LocationClient(context.location_server_url)

    def create_server(self, **kwargs: Any) -> FastAPI:
        """Create the FastAPI server application with lifespan."""

        # Set up lifespan context manager
        @asynccontextmanager
        async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
            """Start the REST server and initialize the state handler and engine"""
            _ = app  # Mark app as used to avoid lint warning
            global_ownership_info.workcell_id = self.definition.manager_id
            global_ownership_info.manager_id = self.definition.manager_id

            # LOG WORKCELL START EVENT
            self.logger.log(
                Event(
                    event_type=EventType.WORKCELL_START,
                    event_data=self.definition.model_dump(mode="json"),
                )
            )

            if self.start_engine:
                engine = Engine(self.state_handler, self.data_client)
                engine.spin()
            else:
                with self.state_handler.wc_state_lock():
                    self.state_handler.initialize_workcell_state()
            try:
                yield
            finally:
                # LOG WORKCELL STOP EVENT
                self.logger.log(
                    Event(
                        event_type=EventType.WORKCELL_STOP,
                        event_data=self.definition.model_dump(mode="json"),
                    )
                )

        # Create app with lifespan
        app = FastAPI(
            title=self._definition.name,
            description=self._definition.description
            or f"{self._definition.name} Manager",
            lifespan=lifespan,
            **kwargs,
        )

        # Configure the app (middleware, etc.)
        self.configure_app(app)

        # Include the router from this Routable class
        app.include_router(self.router)

        return app

    # Endpoint implementations

    def get_health(self) -> WorkcellManagerHealth:
        """Get the health status of the Workcell Manager."""
        health = WorkcellManagerHealth()

        try:
            # Test Redis connection if configured
            if (
                hasattr(self.state_handler, "_redis_client")
                and self.state_handler._redis_client
            ):
                self.state_handler._redis_client.ping()
                health.redis_connected = True
            else:
                health.redis_connected = None

            # Count nodes and check their reachability
            total_nodes = len(self.definition.nodes)
            health.total_nodes = total_nodes

            # TODO: Implement actual node reachability checks
            health.nodes_reachable = total_nodes

            health.healthy = True
            health.description = "Workcell Manager is running normally"

        except Exception as e:
            health.healthy = False
            if "redis" in str(e).lower():
                health.redis_connected = False
            health.description = f"Health check failed: {e!s}"

        return health

    @get("/workcell")
    def get_workcell(self) -> WorkcellManagerDefinition:
        """Get the currently running workcell (backward compatibility)."""
        return self.state_handler.get_workcell_definition()

    @get("/state")
    def get_state(self) -> WorkcellState:
        """Get the current state of the workcell."""
        return self.state_handler.get_workcell_state()

    @get("/nodes")
    def get_nodes(self) -> dict[str, Node]:
        """Get info on the nodes in the workcell."""
        return self.state_handler.get_nodes()

    @get("/node/{node_name}")
    def get_node(self, node_name: str) -> Union[Node, str]:
        """Get information about about a specific node."""
        try:
            node = self.state_handler.get_node(node_name)
        except Exception:
            return "Node not found!"
        return node

    @post("/node")
    def add_node(
        self,
        node_name: str,
        node_url: str,
        permanent: bool = False,
    ) -> Union[Node, str]:
        """Add a node to the workcell's node list"""
        if node_name in self.state_handler.get_nodes():
            return "Node name exists, node names must be unique!"
        node = Node(node_url=node_url)
        self.state_handler.set_node(node_name, node)
        if permanent:
            workcell = self.state_handler.get_workcell_definition()
            workcell.nodes[node_name] = node_url
            workcell_path = self.get_definition_path()
            if workcell_path.exists():
                workcell.to_yaml(workcell_path)
            self.state_handler.set_workcell_definition(workcell)

        return self.state_handler.get_node(node_name)

    @post("/admin/{command}")
    def send_admin_command(self, command: str) -> list:
        """Send an admin command to all capable nodes."""
        responses = []
        for node in self.state_handler.get_nodes().values():
            if command in node.info.capabilities.admin_commands:
                client = find_node_client(node.node_url)
                response = client.send_admin_command(command)
                responses.append(response)
        return responses

    @post("/admin/{command}/{node}")
    def send_admin_command_to_node(
        self, command: str, node: str
    ) -> AdminCommandResponse:
        """Send admin command to a node."""
        node = self.state_handler.get_node(node)
        if command in node.info.capabilities.admin_commands:
            client = find_node_client(node.node_url)
            return client.send_admin_command(command)
        raise HTTPException(
            status_code=400, detail="Node cannot perform that admin command"
        )

    @get("/workflows/active")
    def get_active_workflows(self) -> dict[str, Workflow]:
        """Get active workflows."""
        return self.state_handler.get_active_workflows()

    @get("/workflows/archived")
    def get_archived_workflows(self, number: int = 20) -> dict[str, Workflow]:
        """Get archived workflows."""
        return self.state_handler.get_archived_workflows(number)

    @get("/workflows/queue")
    def get_workflow_queue(self) -> list[Workflow]:
        """Get all queued workflows."""
        return self.state_handler.get_workflow_queue()

    @get("/workflow/{workflow_id}")
    def get_workflow(self, workflow_id: str) -> Workflow:
        """Get info on a specific workflow."""
        return self.state_handler.get_workflow(workflow_id)

    @post("/workflow/{workflow_id}/pause")
    def pause_workflow(self, workflow_id: str) -> Workflow:
        """Pause a specific workflow."""
        with self.state_handler.wc_state_lock():
            wf = self.state_handler.get_active_workflow(workflow_id)
            if wf.status.active:
                if wf.status.running:
                    self.send_admin_command_to_node(
                        "pause", wf.steps[wf.status.current_step_index].node
                    )
                wf.status.paused = True
                self.state_handler.set_active_workflow(wf)

        return self.state_handler.get_active_workflow(workflow_id)

    @post("/workflow/{workflow_id}/resume")
    def resume_workflow(self, workflow_id: str) -> Workflow:
        """Resume a paused workflow."""
        with self.state_handler.wc_state_lock():
            wf = self.state_handler.get_active_workflow(workflow_id)
            if wf.status.paused:
                if wf.status.running:
                    self.send_admin_command_to_node(
                        "resume", wf.steps[wf.status.current_step_index].node
                    )
                wf.status.paused = False
                self.state_handler.set_active_workflow(wf)
                self.state_handler.enqueue_workflow(wf.workflow_id)
        return self.state_handler.get_active_workflow(workflow_id)

    @post("/workflow/{workflow_id}/cancel")
    def cancel_workflow(self, workflow_id: str) -> Workflow:
        """Cancel a specific workflow."""
        with self.state_handler.wc_state_lock():
            wf = self.state_handler.get_workflow(workflow_id)
            if wf.status.running:
                self.send_admin_command_to_node(
                    "cancel", wf.steps[wf.status.current_step_index].node
                )
            wf.status.cancelled = True
            self.state_handler.set_active_workflow(wf)
        return self.state_handler.get_active_workflow(workflow_id)

    @post("/workflow/{workflow_id}/retry")
    def retry_workflow(self, workflow_id: str, index: int = -1) -> Workflow:
        """Retry an existing workflow from a specific step."""
        with self.state_handler.wc_state_lock():
            wf = self.state_handler.get_workflow(workflow_id)
            if wf.status.terminal:
                if index < 0:
                    index = wf.status.current_step_index
                wf.status.reset(index)
                self.state_handler.set_active_workflow(wf)
                self.state_handler.delete_archived_workflow(wf.workflow_id)
                self.state_handler.enqueue_workflow(wf.workflow_id)
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Workflow is not in a terminal state, cannot retry",
                )
        return self.state_handler.get_active_workflow(workflow_id)

    @post("/workflow_definition")
    async def submit_workflow_definition(
        self,
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
            return self.state_handler.save_workflow_definition(
                workflow_definition=wf_def,
            )
        except HTTPException as e:
            raise e
        except Exception as e:
            self.logger.error(f"Error saving workflow definition: {e}")
            traceback.print_exc()
            raise HTTPException(
                status_code=500,
                detail=f"Error saving workflow definition: {e}",
            ) from e

    @get("/workflow_definition/{workflow_definition_id}")
    async def get_workflow_definition(
        self,
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
            return self.state_handler.get_workflow_definition(workflow_definition_id)
        except Exception as e:
            traceback.print_exc()
            raise HTTPException(status_code=404, detail=str(e)) from e

    @post("/workflow")
    async def start_workflow(
        self,
        workflow_definition_id: Annotated[str, Form()],
        ownership_info: Annotated[Optional[str], Form()] = None,
        json_inputs: Annotated[Optional[str], Form()] = None,
        file_input_paths: Annotated[Optional[str], Form()] = None,
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
                wf_def = self.state_handler.get_workflow_definition(str(workflow_id))

            except Exception as e:
                traceback.print_exc()
                raise HTTPException(status_code=422, detail=str(e)) from e

            ownership_info = (
                OwnershipInfo.model_validate_json(ownership_info)
                if ownership_info
                else OwnershipInfo()
            )
            with ownership_context(**ownership_info.model_dump(exclude_none=True)):
                if json_inputs is None or json_inputs == "":
                    json_inputs = {}
                else:
                    json_inputs = json.loads(json_inputs)
                    if not isinstance(json_inputs, dict) or not all(
                        isinstance(k, str) for k in json_inputs
                    ):
                        raise HTTPException(
                            status_code=400,
                            detail="Parameters must be a dictionary with string keys",
                        )
                if file_input_paths is None or file_input_paths == "":
                    file_input_paths = {}
                else:
                    file_input_paths = json.loads(file_input_paths)
                    if not isinstance(file_input_paths, dict) or not all(
                        isinstance(k, str) for k in file_input_paths
                    ):
                        raise HTTPException(
                            status_code=400,
                            detail="Input File Paths must be a dictionary with string keys",
                        )
                workcell = self.state_handler.get_workcell_definition()
                check_parameters(wf_def, json_inputs, file_input_paths)
                wf = create_workflow(
                    workflow_def=wf_def,
                    workcell=workcell,
                    json_inputs=json_inputs,
                    file_input_paths=file_input_paths,
                    data_client=self.data_client,
                    state_handler=self.state_handler,
                    location_client=self.location_client,
                )

                wf = save_workflow_files(
                    workflow=wf, files=files, data_client=self.data_client
                )

                with self.state_handler.wc_state_lock():
                    self.state_handler.set_active_workflow(wf)
                    self.state_handler.enqueue_workflow(wf.workflow_id)

                self.logger.log(
                    Event(
                        event_type=EventType.WORKFLOW_START,
                        event_data=wf.model_dump(mode="json"),
                    )
                )
                return wf

        except HTTPException as e:
            raise e
        except Exception as e:
            self.logger.error(f"Error starting workflow: {e}")
            traceback.print_exc()
            raise HTTPException(
                status_code=500,
                detail=f"Error starting workflow: {e}",
            ) from e


if __name__ == "__main__":
    manager = WorkcellManager()
    manager.run_server()
