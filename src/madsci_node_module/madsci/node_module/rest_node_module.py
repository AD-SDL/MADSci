"""REST-based Node Module helper classes."""

import os
import signal
import tempfile
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Callable, Optional, Type
from zipfile import ZipFile

from fastapi import Request, Response
from fastapi.applications import FastAPI
from fastapi.background import BackgroundTasks
from fastapi.datastructures import UploadFile
from fastapi.routing import APIRouter
from madsci.client.node.rest_node_client import RestNodeClient
from madsci.common.ownership import global_ownership_info
from madsci.common.types.action_types import (
    ActionFiles,
    ActionRequest,
    ActionResult,
    ActionStatus,
    DatapointActionResultDefinition,
    FileActionResultDefinition,
    JSONActionResultDefinition,
    create_action_request_model,
    extract_file_parameters,
    extract_file_result_definitions,
)
from madsci.common.types.admin_command_types import AdminCommandResponse
from madsci.common.types.base_types import Error
from madsci.common.types.event_types import Event
from madsci.common.types.node_types import (
    AdminCommands,
    NodeClientCapabilities,
    NodeInfo,
    NodeSetConfigResponse,
    NodeStatus,
    RestNodeConfig,
)
from madsci.common.utils import new_ulid_str
from madsci.node_module.abstract_node_module import (
    AbstractNode,
)
from pydantic import AnyUrl, BaseModel, Field, create_model
from starlette.responses import FileResponse


class RestNode(AbstractNode):
    """REST-based node implementation with better OpenAPI documentation and result handling."""

    rest_api = None
    """The REST API server for the node."""
    supported_capabilities: NodeClientCapabilities = (
        RestNodeClient.supported_capabilities
    )
    """The default supported capabilities of this node module class."""
    config: RestNodeConfig = RestNodeConfig()
    """The configuration for the node."""
    config_model = RestNodeConfig
    """The node config model class. This is the class that will be used to instantiate self.config."""

    """------------------------------------------------------------------------------------------------"""
    """Node Lifecycle and Public Methods"""
    """------------------------------------------------------------------------------------------------"""

    def __init__(self, *args: Any, **kwargs: Any) -> "RestNode":
        """Initialize the node class."""
        super().__init__(*args, **kwargs)
        self.node_info.node_url = getattr(self.config, "node_url", None)

    async def _get_request_files(self, request: Request) -> list[UploadFile]:
        """Extract uploaded files from a request."""
        form = await request.form()

        # Get all uploaded files
        upload_files = []
        for _, field_value in form.items():
            if hasattr(field_value, "filename") and hasattr(field_value, "file"):
                upload_files.append(
                    UploadFile(
                        file=field_value.file,
                        filename=field_value.filename,
                        headers=getattr(field_value, "headers", None),
                    )
                )

        return upload_files

    def start_node(self, testing: bool = False) -> None:
        """Start the node."""
        global_ownership_info.node_id = self.node_definition.node_id
        url = AnyUrl(getattr(self.config, "node_url", "http://127.0.0.1:2000"))

        # Create FastAPI app metadata from node info
        app_metadata = self._create_fastapi_metadata()

        if not testing:
            self.logger.debug("Running node in production mode")
            import uvicorn  # noqa: PLC0415

            self.rest_api = FastAPI(lifespan=self._lifespan, **app_metadata)

            # Middleware to set ownership context for each request
            @self.rest_api.middleware("http")
            async def ownership_middleware(
                request: Request, call_next: Callable
            ) -> Response:
                global_ownership_info.node_id = self.node_definition.node_id
                return await call_next(request)

            self._configure_routes()
            uvicorn.run(
                self.rest_api,
                host=url.host if url.host else "127.0.0.1",
                port=url.port if url.port else 2000,
                **getattr(self.config, "uvicorn_kwargs", {}),
            )
        else:
            self.logger.debug("Running node in test mode")
            self.rest_api = FastAPI(lifespan=self._lifespan, **app_metadata)
            self._configure_routes()

    """------------------------------------------------------------------------------------------------"""
    """Interface Methods"""
    """------------------------------------------------------------------------------------------------"""

    def get_action_status(self, action_id: str) -> ActionStatus:
        """Get the status of an action on the node."""
        return super().get_action_status(action_id)

    def get_action_result(
        self,
        action_id: str,
    ) -> ActionResult:
        """Get the result of an action on the node."""
        return super().get_action_result(action_id)

    def get_action_result_dict(
        self,
        action_id: str,
    ) -> dict[str, Any]:
        """Get the result of an action on the node as a dictionary for API responses."""
        action_response = super().get_action_result(action_id)

        if isinstance(action_response, dict):
            return self._process_dict_response(action_response)
        return self._process_action_result_response(action_response)

    def _process_dict_response(self, response: dict) -> dict[str, Any]:
        """Process a response that's already a dictionary."""
        result_dict = response.copy()

        # Ensure status is a string
        if hasattr(result_dict.get("status"), "value"):
            result_dict["status"] = result_dict["status"].value

        # Handle files serialization if present
        files_field = result_dict.get("files")
        if files_field is not None:
            result_dict["files"] = self._serialize_files_field(files_field)

        return result_dict

    def _process_action_result_response(
        self, action_response: ActionResult
    ) -> dict[str, Any]:
        """Process an ActionResult object response."""
        result_dict = {
            "action_id": action_response.action_id,
            "status": action_response.status.value
            if hasattr(action_response.status, "value")
            else action_response.status,
            "errors": [
                error.model_dump() if hasattr(error, "model_dump") else error
                for error in action_response.errors
            ],
            "json_result": action_response.json_result,
            "datapoints": action_response.datapoints.model_dump()
            if action_response.datapoints
            else None,
        }

        # Handle files with proper serialization
        if action_response.files:
            result_dict["files"] = self._serialize_files_field(action_response.files)
        else:
            result_dict["files"] = None

        return result_dict

    def _serialize_files_field(self, files_field: Any) -> Any:
        """Serialize files field to JSON-compatible format."""
        if isinstance(files_field, Path):
            return str(files_field)
        if hasattr(files_field, "model_dump"):
            files_dict = files_field.model_dump()
            for key, value in files_dict.items():
                if isinstance(value, Path):
                    files_dict[key] = str(value)
            return files_dict
        if isinstance(files_field, str):
            return files_field
        return files_field

    def get_action_history(
        self, action_id: Optional[str] = None
    ) -> dict[str, list[ActionResult]]:
        """Get the action history of the node, or of a specific action."""
        return super().get_action_history(action_id)

    def get_status(self) -> NodeStatus:
        """Get the status of the node."""
        return super().get_status()

    def get_info(self) -> NodeInfo:
        """Get information about the node."""
        return super().get_info()

    def get_state(self) -> dict[str, Any]:
        """Get the state of the node."""
        return super().get_state()

    def get_log(self) -> dict[str, Event]:
        """Get the log of the node"""
        return super().get_log()

    def set_config(self, new_config: dict[str, Any]) -> NodeSetConfigResponse:
        """Set configuration values of the node."""
        return super().set_config(new_config=new_config)

    def run_admin_command(self, admin_command: AdminCommands) -> AdminCommandResponse:
        """Perform an administrative command on the node."""
        return super().run_admin_command(admin_command)

    """------------------------------------------------------------------------------------------------"""
    """Admin Commands"""
    """------------------------------------------------------------------------------------------------"""

    def reset(self) -> AdminCommandResponse:
        """Restart the node."""
        try:
            self.shutdown_handler()
            self._startup()
        except Exception as exception:
            self._exception_handler(exception)
            return AdminCommandResponse(
                success=False,
                errors=[Error.from_exception(exception)],
            )
        return AdminCommandResponse(
            success=True,
            errors=[],
        )

    def shutdown(self, background_tasks: BackgroundTasks) -> AdminCommandResponse:
        """Shutdown the node."""
        try:

            def shutdown_server() -> None:
                """Shutdown the REST server."""
                time.sleep(1)
                pid = os.getpid()
                os.kill(pid, signal.SIGTERM)

            background_tasks.add_task(shutdown_server)
        except Exception as exception:
            return AdminCommandResponse(
                success=False,
                errors=[Error.from_exception(exception)],
            )
        return AdminCommandResponse(
            success=True,
            errors=[],
        )

    """------------------------------------------------------------------------------------------------"""
    """Internal and Private Methods"""
    """------------------------------------------------------------------------------------------------"""

    def _create_fastapi_metadata(self) -> dict[str, Any]:
        """Create FastAPI app metadata from node info."""
        metadata = {}

        # Set title from node name
        if hasattr(self, "node_info") and self.node_info:
            metadata["title"] = self.node_info.node_name or "MADSci Node"

            # Set description from node description
            if self.node_info.node_description:
                metadata["description"] = self.node_info.node_description

            # Set version from module version
            if (
                hasattr(self.node_info, "module_version")
                and self.node_info.module_version
            ):
                metadata["version"] = str(self.node_info.module_version)
        elif hasattr(self, "node_definition") and self.node_definition:
            # Fallback to node definition if node_info is not available yet
            metadata["title"] = self.node_definition.node_name or "MADSci Node"

            if self.node_definition.node_description:
                metadata["description"] = self.node_definition.node_description

            if (
                hasattr(self.node_definition, "module_version")
                and self.node_definition.module_version
            ):
                metadata["version"] = str(self.node_definition.module_version)
        else:
            # Ultimate fallback
            metadata["title"] = "MADSci Node"

        # Set default values if not provided
        if "version" not in metadata:
            metadata["version"] = getattr(self, "module_version", "0.0.1")

        # Add default description if none provided
        if "description" not in metadata:
            metadata["description"] = f"REST API for {metadata['title']}"

        return metadata

    @asynccontextmanager
    async def _lifespan(self, app: FastAPI):  # noqa: ANN202, ARG002
        """The lifespan of the REST API."""
        super().start_node()

        yield

        try:
            # * Call any shutdown logic
            self.shutdown_handler()
        except Exception as exception:
            # * If an exception occurs during shutdown, handle it so we at least see the error in logs/terminal
            self._exception_handler(exception)

    def create_action(
        self, action_name: str, request_data: dict[str, Any]
    ) -> dict[str, str]:
        """Create a new action and return the action_id."""
        action_id = new_ulid_str()

        # Store the action request data for later use
        if not hasattr(self, "_pending_actions"):
            self._pending_actions = {}

        action_request = ActionRequest(
            action_id=action_id,
            action_name=action_name,
            args=request_data,
            files={},  # Files will be added separately
        )

        self._pending_actions[action_id] = action_request
        return {"action_id": action_id}

    def upload_action_file(
        self, _action_name: str, action_id: str, file_arg: str, file: UploadFile
    ) -> dict[str, str]:
        """Upload a file for a specific action."""
        if not hasattr(self, "_pending_actions"):
            self._pending_actions = {}

        if action_id not in self._pending_actions:
            raise ValueError(f"Action {action_id} not found")

        # Save the uploaded file to a temporary location
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            file.file.seek(0)
            content = file.file.read()
            temp_file.write(content)
            temp_path = Path(temp_file.name)

        # Update the action request with the file
        action_request = self._pending_actions[action_id]
        action_request.files[file_arg] = temp_path

        return {"status": "uploaded", "file_arg": file_arg}

    def start_action(self, _action_name: str, action_id: str) -> dict[str, Any]:
        """Start an action after all files have been uploaded."""
        if not hasattr(self, "_pending_actions"):
            self._pending_actions = {}

        if action_id not in self._pending_actions:
            # Return a failed action result instead of raising an exception
            return {
                "action_id": action_id,
                "status": ActionStatus.FAILED.value,
                "errors": [
                    {
                        "message": f"Action {action_id} not found",
                        "error_type": "NotFound",
                    }
                ],
                "json_result": None,
                "files": None,
                "datapoints": None,
            }

        action_request = self._pending_actions[action_id]

        # Remove from pending actions
        del self._pending_actions[action_id]

        # Execute the action
        super().run_action(action_request)

        # Wait a moment for the action to complete
        time.sleep(0.5)

        # Get the final result from action history as a dictionary for API response
        return self.get_action_result_dict(action_id)

    def get_action_files_zip(self, _action_name: str, action_id: str) -> FileResponse:
        """Get all files from an action as a ZIP file."""
        action_response = super().get_action_result(action_id)

        if not action_response.files:
            raise ValueError(f"Action {action_id} has no files")

        if isinstance(action_response.files, Path):
            # Single file - return as is (no ZIP needed)
            return FileResponse(
                path=action_response.files,
                headers={"content-type": "application/octet-stream"},
            )
        if isinstance(action_response.files, ActionFiles):
            # Multiple files - create ZIP
            files_dict = action_response.files.model_dump()

            with tempfile.NamedTemporaryFile(
                suffix=".zip", delete=False
            ) as temp_zip_file:
                with ZipFile(temp_zip_file.name, "w") as zip_file:
                    for _, file_path in files_dict.items():
                        if Path(file_path).exists():
                            zip_file.write(file_path, Path(file_path).name)

                return FileResponse(
                    path=temp_zip_file.name,
                    filename=f"{action_id}_files.zip",
                    headers={"content-type": "application/zip"},
                )
        else:
            raise ValueError("Invalid file response")

    def get_action_file(
        self, _action_name: str, action_id: str, file_key: str
    ) -> FileResponse:
        """Get a specific file from an action."""
        action_response = super().get_action_result(action_id)

        if not action_response.files:
            raise ValueError(f"Action {action_id} has no files")

        if isinstance(action_response.files, Path):
            # Single file
            if file_key == "file":
                return FileResponse(
                    path=action_response.files,
                    headers={"content-type": "application/octet-stream"},
                )
        elif isinstance(action_response.files, ActionFiles):
            # Multiple files
            files_dict = action_response.files.model_dump()
            if file_key in files_dict:
                file_path = Path(files_dict[file_key])
                return FileResponse(
                    path=file_path, headers={"content-type": "application/octet-stream"}
                )

        raise ValueError(f"File key '{file_key}' not found")

    def _configure_routes(self) -> None:
        """Configure the routes for the REST API."""
        self.router = APIRouter()

        # Standard endpoints
        self.router.add_api_route("/status", self.get_status, methods=["GET"])
        self.router.add_api_route("/info", self.get_info, methods=["GET"])
        self.router.add_api_route("/state", self.get_state, methods=["GET"])
        self.router.add_api_route("/config", self.set_config, methods=["POST"])
        self.router.add_api_route("/log", self.get_log, methods=["GET"])
        self.router.add_api_route(
            "/admin/{admin_command}",
            self.run_admin_command,
            methods=["POST"],
        )

        self._setup_action_routes()

        self.router.add_api_route("/action", self.get_action_history, methods=["GET"])
        self.router.add_api_route(
            "/action/{action_id}/status", self.get_action_status, methods=["GET"]
        )
        self.router.add_api_route(
            "/action/{action_id}/result", self.get_action_result_dict, methods=["GET"]
        )

        self.rest_api.include_router(self.router)

    def _setup_action_routes(self) -> None:
        """Set up action routes for each action handler."""
        for action_name, action_function in self.action_handlers.items():
            # Create dynamic models for this action
            request_model = create_action_request_model(action_function)
            self._create_action_result_model(action_function, action_name)

            self._setup_create_action_route(action_name, request_model)
            self._setup_file_upload_routes(action_name, action_function)
            self._setup_start_action_route(action_name)
            self._setup_get_status_route(action_name)
            self._setup_get_result_route(action_name)
            self._setup_file_download_routes(action_name, action_function)

    def _create_action_result_model(
        self, action_function: Any, action_name: str
    ) -> Type[BaseModel]:
        """Create an action result model that properly reflects the action's return type."""
        result_definitions = getattr(
            action_function, "__madsci_action_result_definitions__", []
        )

        base_fields = self._get_base_action_result_fields()

        if result_definitions:
            categorized_results = self._categorize_result_definitions(
                result_definitions
            )
            base_fields.update(
                self._create_specific_result_fields(categorized_results, action_name)
            )
        else:
            base_fields.update(self._get_generic_result_fields())

        return self._create_result_model(action_name, action_function, base_fields)

    def _get_base_action_result_fields(self) -> dict:
        """Get the base fields that all action results have."""
        return {
            "action_id": (str, Field(description="Unique identifier for this action")),
            "status": (ActionStatus, Field(description="Current status of the action")),
            "errors": (
                list[Error],
                Field(default_factory=list, description="Any errors that occurred"),
            ),
        }

    def _categorize_result_definitions(self, result_definitions: list) -> dict:
        """Categorize result definitions by type."""
        return {
            "json_results": [
                rd
                for rd in result_definitions
                if isinstance(rd, JSONActionResultDefinition)
            ],
            "file_results": [
                rd
                for rd in result_definitions
                if isinstance(rd, FileActionResultDefinition)
            ],
            "datapoint_results": [
                rd
                for rd in result_definitions
                if isinstance(rd, DatapointActionResultDefinition)
            ],
        }

    def _create_specific_result_fields(
        self, categorized_results: dict, action_name: str
    ) -> dict:
        """Create specific result fields based on categorized result definitions."""
        fields = {}
        fields.update(
            self._create_json_result_field(categorized_results["json_results"])
        )
        fields.update(
            self._create_file_result_field(
                categorized_results["file_results"], action_name
            )
        )
        fields.update(
            self._create_datapoint_result_field(
                categorized_results["datapoint_results"], action_name
            )
        )
        return fields

    def _create_json_result_field(self, json_results: list) -> dict:
        """Create JSON result field based on JSON result definitions."""
        if json_results:
            if len(json_results) == 1:
                json_def = json_results[0]
                if json_def.json_schema:
                    return {
                        "json_result": (
                            Optional[dict],
                            Field(
                                default=None,
                                description=f"JSON result data: {json_def.description or json_def.result_label}",
                            ),
                        )
                    }
                return {
                    "json_result": (
                        Optional[Any],
                        Field(default=None, description="JSON result data"),
                    )
                }
            return {
                "json_result": (
                    Optional[dict],
                    Field(default=None, description="Combined JSON result data"),
                )
            }
        return {
            "json_result": (
                Optional[Any],
                Field(default=None, description="JSON result data"),
            )
        }

    def _create_file_result_field(self, file_results: list, action_name: str) -> dict:
        """Create file result field based on file result definitions."""
        if file_results:
            if len(file_results) == 1:
                return self._create_single_file_field(file_results[0], action_name)
            return self._create_multiple_files_field(file_results, action_name)
        return {
            "files": (
                Optional[Any],
                Field(default=None, description="Result files"),
            )
        }

    def _create_single_file_field(self, file_def: Any, action_name: str) -> dict:
        """Create field definition for a single file result."""
        if file_def.result_label == "file":
            return {
                "files": (
                    Optional[str],
                    Field(default=None, description="Path to the result file"),
                )
            }
        file_fields = {
            file_def.result_label: (
                str,
                Field(description=f"Path to {file_def.result_label}"),
            )
        }
        file_model = create_model(f"{action_name.title()}Files", **file_fields)
        return {
            "files": (
                Optional[file_model],
                Field(default=None, description="Result files"),
            )
        }

    def _create_multiple_files_field(
        self, file_results: list, action_name: str
    ) -> dict:
        """Create field definition for multiple file results."""
        file_fields = {}
        for file_def in file_results:
            file_fields[file_def.result_label] = (
                str,
                Field(
                    description=f"Path to {file_def.description or file_def.result_label}"
                ),
            )
        file_model = create_model(f"{action_name.title()}Files", **file_fields)
        return {
            "files": (
                Optional[file_model],
                Field(default=None, description="Result files"),
            )
        }

    def _create_datapoint_result_field(
        self, datapoint_results: list, action_name: str
    ) -> dict:
        """Create datapoint result field based on datapoint result definitions."""
        if datapoint_results:
            dp_fields = {}
            for dp_def in datapoint_results:
                dp_fields[dp_def.result_label] = (
                    str,
                    Field(
                        description=f"Datapoint ID for {dp_def.description or dp_def.result_label}"
                    ),
                )
            if dp_fields:
                dp_model = create_model(f"{action_name.title()}Datapoints", **dp_fields)
                return {
                    "datapoints": (
                        Optional[dp_model],
                        Field(default=None, description="Result datapoint IDs"),
                    )
                }
            return {
                "datapoints": (
                    Optional[dict],
                    Field(default=None, description="Result datapoint IDs"),
                )
            }
        return {
            "datapoints": (
                Optional[dict],
                Field(default=None, description="Result datapoint IDs"),
            )
        }

    def _get_generic_result_fields(self) -> dict:
        """Get generic result fields when no specific definitions are available."""
        return {
            "json_result": (
                Optional[Any],
                Field(default=None, description="JSON result data"),
            ),
            "files": (
                Optional[Any],
                Field(default=None, description="Result files"),
            ),
            "datapoints": (
                Optional[dict],
                Field(default=None, description="Result datapoint IDs"),
            ),
        }

    def _create_result_model(
        self, action_name: str, action_function: Any, base_fields: dict
    ) -> Type[BaseModel]:
        """Create the final result model with given fields."""
        model_name = f"{action_name.title()}ActionResult"
        model_docstring = f"Result model for {action_name} action"
        if action_function.__doc__:
            model_docstring = f"{model_docstring}. {action_function.__doc__.strip()}"

        return create_model(model_name, __doc__=model_docstring, **base_fields)

    def _setup_create_action_route(self, action_name: str, request_model: type) -> None:
        """Set up the create action route for a specific action."""

        def create_action_wrapper(action: str = action_name) -> Any:
            def wrapper(request_data: Any) -> dict[str, str]:
                # Convert the typed request model to dict for internal processing
                request_dict = request_data.model_dump(exclude_unset=True)
                # Remove action_name if it exists in the request data since it's in the URL
                request_dict.pop("action_name", None)
                return self.create_action(action, request_dict)

            # Set the proper annotation for FastAPI to understand
            wrapper.__annotations__ = {
                "request_data": request_model,
                "return": dict[str, str],
            }
            return wrapper

        self.router.add_api_route(
            f"/action/{action_name}",
            create_action_wrapper(),
            methods=["POST"],
            response_model=dict,
            summary=f"Create {action_name} action",
            description=f"Create a new {action_name} action and return the action_id.",
            tags=[action_name],
        )

    def _setup_file_upload_routes(self, action_name: str, action_function: Any) -> None:
        """Set up specific upload routes for each file parameter in the action."""
        file_params = extract_file_parameters(action_function)

        # Create a specific route for each file parameter
        for param_name, param_info in file_params.items():
            required_text = "Required" if param_info["required"] else "Optional"
            description = f"{required_text} file parameter: {param_info['description']}"

            def create_upload_wrapper(file_param_name: str = param_name) -> Any:
                def wrapper(action_id: str, file: UploadFile) -> dict[str, str]:
                    return self.upload_action_file(
                        action_name, action_id, file_param_name, file
                    )

                return wrapper

            self.router.add_api_route(
                f"/action/{action_name}/{{action_id}}/upload/{param_name}",
                create_upload_wrapper(),
                methods=["POST"],
                response_model=dict,
                summary=f"Upload {param_name} for {action_name}",
                description=description,
                tags=[action_name],
            )

    def _setup_start_action_route(self, action_name: str) -> None:
        """Set up the start action route for a specific action."""

        def start_action_wrapper(action: str = action_name) -> Any:
            def wrapper(action_id: str) -> dict[str, Any]:
                return self.start_action(action, action_id)

            return wrapper

        self.router.add_api_route(
            f"/action/{action_name}/{{action_id}}/start",
            start_action_wrapper(),
            methods=["POST"],
            summary=f"Start {action_name} action",
            description=f"Start the {action_name} action after files have been uploaded.",
            tags=[action_name],
        )

    def _setup_get_status_route(self, action_name: str) -> None:
        """Set up the get status route for a specific action."""

        def get_status_wrapper() -> Any:
            def wrapper(action_id: str) -> ActionStatus:
                return self.get_action_status(action_id)

            return wrapper

        # Status endpoint
        self.router.add_api_route(
            f"/action/{action_name}/{{action_id}}/status",
            get_status_wrapper(),
            methods=["GET"],
            response_model=ActionStatus,
            summary=f"Get {action_name} action status",
            description=f"Get the current status of the {action_name} action.",
            tags=[action_name],
        )

    def _setup_get_result_route(self, action_name: str) -> None:
        """Set up the get result route for a specific action."""

        def get_result_wrapper() -> Any:
            def wrapper(action_id: str) -> dict[str, Any]:
                return self.get_action_result_dict(action_id)

            return wrapper

        self.router.add_api_route(
            f"/action/{action_name}/{{action_id}}/result",
            get_result_wrapper(),
            methods=["GET"],
            summary=f"Get {action_name} action result",
            description=f"Get the detailed result data from the {action_name} action.",
            tags=[action_name],
            responses={
                200: {
                    "description": "Action result",
                },
                404: {"description": "Action not found"},
            },
        )

    def _setup_file_download_routes(
        self, action_name: str, action_function: Any
    ) -> None:
        """Set up specific file download routes for each file result in the action."""
        file_results = extract_file_result_definitions(action_function)

        # Create specific routes for each file result
        for result_label, description in file_results.items():

            def create_file_download_wrapper(
                file_result_name: str = result_label,
            ) -> Any:
                def wrapper(action_id: str) -> Any:
                    return self.get_action_file(
                        action_name, action_id, file_result_name
                    )

                return wrapper

            self.router.add_api_route(
                f"/action/{action_name}/{{action_id}}/download/{result_label}",
                create_file_download_wrapper(),
                methods=["GET"],
                summary=f"Download {result_label} from {action_name}",
                description=description,
                tags=[action_name],
                responses={
                    200: {
                        "description": "File download",
                        "content": {
                            "application/octet-stream": {
                                "schema": {"type": "string", "format": "binary"}
                            }
                        },
                    },
                    404: {"description": "File not found"},
                },
            )

        # Create a combined files endpoint if there are multiple file results
        if len(file_results) > 1:

            def get_files_wrapper() -> Any:
                def wrapper(action_id: str) -> Any:
                    return self.get_action_files_zip(action_name, action_id)

                return wrapper

            self.router.add_api_route(
                f"/action/{action_name}/{{action_id}}/download",
                get_files_wrapper(),
                methods=["GET"],
                summary=f"Download all files from {action_name}",
                description=f"Download all files from the {action_name} action as a ZIP archive.",
                tags=[action_name],
                responses={
                    200: {
                        "description": "ZIP file containing all result files",
                        "content": {
                            "application/zip": {
                                "schema": {"type": "string", "format": "binary"}
                            }
                        },
                    },
                    404: {"description": "Files not found"},
                },
            )


if __name__ == "__main__":
    RestNode().start_node()
