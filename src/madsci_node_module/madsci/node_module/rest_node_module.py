"""REST-based Node Module helper classes."""

import os
import signal
import tempfile
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Callable, Optional, Type, get_origin, get_type_hints
from zipfile import ZipFile

from fastapi import HTTPException, Request, Response
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
    RestActionResult,
    create_action_request_model,
    create_dynamic_model,
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
from pydantic import AnyUrl
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

    def __init__(self, *args: Any, **kwargs: Any) -> "RestNode":
        """Initialize the node class."""
        super().__init__(*args, **kwargs)
        self.node_info.node_url = getattr(self.config, "node_url", None)
        self._action_result_models = {}  # Cache for dynamic result models

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

    def get_action_status(self, action_id: str) -> ActionStatus:
        """Get the status of an action on the node."""
        return super().get_action_status(action_id)

    def get_action_result(self, action_id: str) -> ActionResult:
        """Get the result of an action on the node."""
        return super().get_action_result(action_id)

    def get_action_result_dict(self, action_id: str) -> dict[str, Any]:
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

        # Handle files serialization if present - convert to file keys
        files_field = result_dict.get("files")
        if files_field is not None:
            result_dict["files"] = self._serialize_files_to_keys(files_field)

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
            "history_created_at": action_response.history_created_at,
        }

        # Handle files with proper serialization - convert to file keys for REST API
        if action_response.files:
            result_dict["files"] = self._serialize_files_to_keys(action_response.files)
        else:
            result_dict["files"] = None

        return result_dict

    def _serialize_files_to_keys(self, files_field: Any) -> Any:
        """Serialize files field to file keys for REST API responses."""
        if isinstance(files_field, Path):
            # Single file - return the file key (just "file")
            return ["file"]
        if hasattr(files_field, "model_dump"):
            # ActionFiles - return list of field names as file keys
            files_dict = files_field.model_dump()
            return list(files_dict.keys())
        if isinstance(files_field, str):
            return [files_field]
        if isinstance(files_field, list):
            return files_field
        return None

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

        # Extract args, var_args and var_kwargs from RestActionRequest structure
        args = request_data.get("args", {})
        var_args = request_data.get("var_args")
        var_kwargs = request_data.get("var_kwargs")

        action_request = ActionRequest(
            action_id=action_id,
            action_name=action_name,
            args=args,
            files={},  # Files will be added separately
            var_args=var_args,
            var_kwargs=var_kwargs,
        )

        self._pending_actions[action_id] = action_request
        return {"action_id": action_id}

    def upload_action_file(
        self, _action_name: str, action_id: str, file_arg: str, file: UploadFile
    ) -> dict[str, str]:
        """Upload a single file for a specific action."""
        if not hasattr(self, "_pending_actions"):
            self._pending_actions = {}

        if action_id not in self._pending_actions:
            raise ValueError(f"Action {action_id} not found")

        # Save the uploaded file to a temporary location, preserving filename
        original_filename = file.filename or "uploaded_file"
        temp_dir = Path(tempfile.mkdtemp())
        temp_path = temp_dir / original_filename

        with temp_path.open("wb") as temp_file:
            file.file.seek(0)
            content = file.file.read()
            temp_file.write(content)

        # Update the action request with the file
        action_request = self._pending_actions[action_id]
        action_request.files[file_arg] = temp_path

        return {"status": "uploaded", "file_arg": file_arg}

    def upload_action_files(
        self, _action_name: str, action_id: str, file_arg: str, files: list[UploadFile]
    ) -> dict[str, str]:
        """Upload multiple files for a specific action (for list[Path] parameters)."""
        if not hasattr(self, "_pending_actions"):
            self._pending_actions = {}

        if action_id not in self._pending_actions:
            raise ValueError(f"Action {action_id} not found")

        # Save the uploaded files to temporary locations, preserving filenames
        temp_paths = []
        temp_dir = Path(tempfile.mkdtemp())

        for file in files:
            original_filename = file.filename or f"uploaded_file_{len(temp_paths)}"
            temp_path = temp_dir / original_filename

            with temp_path.open("wb") as temp_file:
                file.file.seek(0)
                content = file.file.read()
                temp_file.write(content)

            temp_paths.append(temp_path)

        # Update the action request with the files list
        action_request = self._pending_actions[action_id]
        action_request.files[file_arg] = temp_paths

        return {"status": "uploaded", "file_arg": file_arg, "file_count": len(files)}

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
            if action_response.status != ActionStatus.SUCCEEDED:
                raise HTTPException(
                    status_code=400,
                    detail=f"Action {action_id} did not succeed (status: {action_response.status}). Cannot download files from failed action.",
                )
            raise HTTPException(
                status_code=404,
                detail=f"Action {action_id} completed successfully but produced no file results",
            )

        # Always create a ZIP, even for single files for consistency
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as temp_zip_file:
            with ZipFile(temp_zip_file.name, "w") as zip_file:
                if isinstance(action_response.files, Path):
                    # Single file - add to ZIP with appropriate name
                    if action_response.files.exists():
                        zip_file.write(action_response.files, "file")
                elif isinstance(action_response.files, ActionFiles):
                    # Multiple files - add all to ZIP with their labels as names
                    files_dict = action_response.files.model_dump()
                    for file_label, file_path in files_dict.items():
                        if Path(file_path).exists():
                            # Use the file label as the filename in the ZIP
                            file_extension = Path(file_path).suffix
                            zip_filename = f"{file_label}{file_extension}"
                            zip_file.write(file_path, zip_filename)
                else:
                    raise ValueError("Invalid file response")

            return FileResponse(
                path=temp_zip_file.name,
                filename=f"{action_id}_files.zip",
                headers={"content-type": "application/zip"},
            )

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
            result_model = self._create_action_result_model(
                action_function, action_name
            )

            self._setup_create_action_route(action_name, request_model)
            self._setup_file_upload_routes(action_name, action_function)
            self._setup_start_action_route(action_name)
            self._setup_get_status_route(action_name)
            self._setup_get_result_route(action_name, result_model)
            self._setup_file_download_routes(action_name, action_function)

    def _create_action_result_model(
        self, action_function: Any, action_name: str
    ) -> Type[RestActionResult]:
        """Create an action result model that properly reflects the action's return type."""
        # Check if we already have a cached model
        if action_name in self._action_result_models:
            return self._action_result_models[action_name]

        # Get the return type of the action function
        type_hints = get_type_hints(action_function)
        return_type = type_hints.get("return")

        # Determine the json_result type based on the return type
        json_result_type = self._extract_json_result_type(return_type)

        # Create the dynamic RestActionResult model
        result_model = create_dynamic_model(
            action_name=action_name,
            json_result_type=json_result_type,
            action_function=action_function,
        )

        # Cache the model
        self._action_result_models[action_name] = result_model
        return result_model

    def _extract_json_result_type(self, return_type: Any) -> Optional[type]:
        """Extract the appropriate type for json_result field from action return type."""
        if not return_type or return_type is type(None):
            return None

        # Handle tuple returns (mixed results)
        if get_origin(return_type) is tuple:
            # Extract non-file types from tuple for json_result
            json_types = []
            for arg_type in return_type.__args__:
                if not self._is_file_type(arg_type):
                    json_types.append(arg_type)

            # If we have exactly one non-file type, use it
            if len(json_types) == 1:
                return json_types[0]
            # If multiple non-file types, return None (will use generic)
            return None

        # Handle file-only returns
        if self._is_file_type(return_type):
            return None

        # Handle simple types and Pydantic models
        if not (get_origin(return_type) or return_type == Any):
            return return_type

        return None

    def _is_file_type(self, type_to_check: Any) -> bool:
        """Check if a type represents file output (Path or ActionFiles subclass)."""
        if type_to_check is Path:
            return True

        # Check if it's an ActionFiles subclass
        try:
            if hasattr(type_to_check, "__mro__") and any(
                base.__name__ == "ActionFiles" for base in type_to_check.__mro__
            ):
                return True
        except (TypeError, AttributeError):
            pass

        return False

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
            is_list = param_info.get("is_list", False)
            description = f"{required_text} file parameter: {param_info['description']}"

            if is_list:
                description += " (accepts multiple files)"

            def create_upload_wrapper(
                file_param_name: str = param_name, is_list_param: bool = is_list
            ) -> Any:
                if is_list_param:

                    def wrapper(
                        action_id: str, files: list[UploadFile]
                    ) -> dict[str, str]:
                        return self.upload_action_files(
                            action_name, action_id, file_param_name, files
                        )
                else:

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

    def _setup_get_result_route(
        self, action_name: str, result_model: Type[RestActionResult]
    ) -> None:
        """Set up the get result route for a specific action."""

        def get_result_wrapper() -> Any:
            def wrapper(action_id: str) -> dict[str, Any]:
                return self.get_action_result_dict(action_id)

            return wrapper

        self.router.add_api_route(
            f"/action/{action_name}/{{action_id}}/result",
            get_result_wrapper(),
            methods=["GET"],
            response_model=result_model,  # Use the specific result model for better OpenAPI docs
            summary=f"Get {action_name} action result",
            description=f"Get the detailed result data from the {action_name} action.",
            tags=[action_name],
            responses={
                200: {
                    "description": "Action result",
                    "model": result_model,
                },
                404: {"description": "Action not found"},
            },
        )

    def _setup_file_download_routes(
        self, action_name: str, action_function: Any
    ) -> None:
        """Set up a single ZIP download route for all actions (defensive programming)."""
        file_results = extract_file_result_definitions(action_function)

        # Create file list description for OpenAPI docs
        if len(file_results) == 1:
            file_key = next(iter(file_results.keys()))
            file_description = f"Download files from {action_name} action as a ZIP archive containing: {file_key}"
        elif len(file_results) > 1:
            files_list = ", ".join(file_results.keys())
            file_description = f"Download files from {action_name} action as a ZIP archive containing {len(file_results)} files: {files_list}"
        else:
            # No declared file results - but provide endpoint for unexpected files
            file_description = f"Download any files returned by the {action_name} action as a ZIP archive. This action is not expected to return files based on type annotations, but this endpoint is available in case files are unexpectedly produced."

        def get_files_wrapper() -> Any:
            def wrapper(action_id: str) -> Any:
                return self.get_action_files_zip(action_name, action_id)

            return wrapper

        self.router.add_api_route(
            f"/action/{action_name}/{{action_id}}/download",
            get_files_wrapper(),
            methods=["GET"],
            summary=f"Download files from {action_name}",
            description=file_description,
            tags=[action_name],
            responses={
                200: {
                    "description": "ZIP file containing action result files",
                    "content": {
                        "application/zip": {
                            "schema": {"type": "string", "format": "binary"}
                        }
                    },
                },
                404: {"description": "Action has no file results"},
            },
        )


if __name__ == "__main__":
    RestNode().start_node()
