"""REST-based Node Module helper classes."""

import asyncio
import inspect
import json
import logging
import os
import signal
import tempfile
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Callable, Optional, ParamSpec, TypeVar, Union

from fastapi import Request, Response
from fastapi.applications import FastAPI
from fastapi.background import BackgroundTasks
from fastapi.datastructures import UploadFile
from fastapi.routing import APIRouter
from madsci.client.node.rest_node_client import RestNodeClient
from madsci.common.ownership import global_ownership_info
from madsci.common.types.action_types import (
    ActionDatapoints,
    ActionJSON,
    ActionRequest,
    ActionResult,
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
from madsci.node_module.helpers import ActionResultWithFiles
from pydantic import AnyUrl
from starlette.middleware.base import BaseHTTPMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

P = ParamSpec("P")
R = TypeVar("R")


class RestNode(AbstractNode):
    """REST-based node implementation and helper class. Inherit from this class to create a new REST-based node class."""

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

    async def get_request_files(self, request: Request) -> list[UploadFile]:
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

    def handle_pure_return(self, response: ActionResult) -> Response:
        """Handle pure return values from actions."""
        if isinstance(response.json_data, ActionJSON):
            response.json_data = response.json_data.model_dump(mode="json")
        if isinstance(response.datapoints, ActionDatapoints):
            response.datapoints = response.datapoints.model_dump(mode="json")
        if response.json_data is not None and response.datapoints is not None:
            response = (response.json_data, response.datapoints)
        elif response.json_data is not None:
            response = response.json_data
        elif response.datapoints is not None:
            response = response.datapoints
        else:
            response = {}
        return Response(content=json.dumps(response), media_type="application/json")

    def check_action_mode(
        self, request: Request, json_data: dict[str, Any]
    ) -> tuple[bool, ActionRequest]:
        """Check if action is run from swaggerdocs or the client"""
        if "action_name" in json_data:
            if "args" in json_data:
                json_data["args"] = json.loads(json_data["args"])
            action_request = ActionRequest(**json_data)
            pure_return = False
        else:
            action_name = Path(request.url.components.path).name
            pure_return = True
            action_request = ActionRequest(action_name=action_name, args=json_data)
        return pure_return, action_request

    class ActionMiddleware(BaseHTTPMiddleware):
        """Middleware to handle action requests. allows use both through client and Swaggerdocs"""

        rest_node_module: Optional["RestNode"] = None

        async def dispatch(self, request: Request, call_next: Callable) -> Any:
            """Middleware function to handle action requests."""
            if "action" in str(request.url) and request.method == "POST":
                files = []
                json_data = request.query_params.__dict__["_dict"]
                pure_return, action_request = self.rest_node_module.check_action_mode(
                    request, json_data
                )
                files = await self.rest_node_module.get_request_files(request)
                response = self.rest_node_module.run_action(
                    action_request.action_name,
                    json.dumps(action_request.args),
                    files,
                    action_request.action_id,
                )
                if pure_return:
                    while (
                        not isinstance(response, ActionResultWithFiles)
                        and not response.status.is_terminal
                    ):
                        if not isinstance(response, ActionResult):
                            raise ValueError("Response is not an ActionResult")
                        await asyncio.sleep(0.1)
                        response = self.rest_node_module.get_action_result(
                            response.action_id
                        )
                if isinstance(response, ActionResultWithFiles):
                    return response
                if pure_return:
                    return self.rest_node_module.handle_pure_return(response)
                return Response(
                    content=response.model_dump_json(),
                    headers={"content-type": "application/json"},
                )
            return await call_next(request)

    def return_action_middleware_class(self) -> Any:
        """Return the action middleware class with the node instance set."""
        self.ActionMiddleware.rest_node_module = self
        return self.ActionMiddleware

    def start_node(self, testing: bool = False) -> None:
        """Start the node."""
        global_ownership_info.node_id = self.node_definition.node_id
        url = AnyUrl(getattr(self.config, "node_url", "http://127.0.0.1:2000"))
        if not testing:
            self.logger.debug("Running node in production mode")
            import uvicorn  # noqa: PLC0415

            self.rest_api = FastAPI(lifespan=self._lifespan)

            # Middleware to set ownership context for each request
            @self.rest_api.middleware("http")
            async def ownership_middleware(
                request: Request, call_next: Callable
            ) -> Response:
                global_ownership_info.node_id = self.node_definition.node_id
                return await call_next(request)

            self.rest_api.add_middleware(self.return_action_middleware_class())

            self._configure_routes()
            uvicorn.run(
                self.rest_api,
                host=url.host if url.host else "127.0.0.1",
                port=url.port if url.port else 2000,
                **getattr(self.config, "uvicorn_kwargs", {}),
            )
        else:
            self.logger.debug("Running node in test mode")
            self.rest_api = FastAPI(lifespan=self._lifespan)
            self.rest_api.add_middleware(self.return_action_middleware_class())
            self._configure_routes()

    """------------------------------------------------------------------------------------------------"""
    """Interface Methods"""
    """------------------------------------------------------------------------------------------------"""

    def run_action(
        self,
        action_name: str,
        args: Optional[str] = None,
        files: Optional[list[UploadFile]] = [],
        action_id: Optional[str] = None,
    ) -> Union[ActionResult, ActionResultWithFiles]:
        """Run an action on the node."""
        if args:
            args = json.loads(args)
            if not isinstance(args, dict):
                raise ValueError("args must be a JSON object")
        else:
            args = {}
        local_files = {}
        # * Save the uploaded files to a temporary directory
        for i in range(len(files)):
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                file = files[i]
                file.file.seek(0)
                content = file.file.read()
                temp_file.write(content)
                local_files[file.filename] = temp_file.name

        response = super().run_action(
            ActionRequest(
                action_id=action_id or new_ulid_str(),
                action_name=action_name,
                args=args,
                files={
                    file.filename: Path(local_files[file.filename]) for file in files
                },
            ),
        )
        # * Return a file response if there are files to be returned
        logger.error(str(response))
        if response.files is not None:
            return ActionResultWithFiles.from_action_response(
                action_response=response,
            )
        # * Otherwise, return a normal action response
        return ActionResult.model_validate(response)

    def get_action_result(
        self,
        action_id: str,
    ) -> Union[ActionResult, ActionResultWithFiles]:
        """Get the status of an action on the node."""
        action_response = super().get_action_result(action_id)
        if action_response.files:
            return ActionResultWithFiles.from_action_response(
                action_response=action_response,
            )
        return ActionResult.model_validate(action_response)

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

    def remove_self_wrapper(self: Any, method: Callable) -> Callable:
        """
        Creates a wrapper function that removes the 'self' argument from a method.

        Args:
            self: The instance object to bind to the method
            method: The method that requires a 'self' argument

        Returns:
            A new function with 'self' pre-bound and removed from the signature
        """

        # Get the original signature
        original_sig = inspect.signature(method)

        # Create new parameters without 'self' and transform Path to UploadFile
        new_params = []
        for name, param in original_sig.parameters.items():
            if name != "self":
                # Transform Path annotation to UploadFile
                if param.annotation == Path:
                    new_param = param.replace(annotation=UploadFile)
                else:
                    new_param = param
                new_params.append(new_param)

        # Create new signature with transformed parameters
        new_sig = original_sig.replace(parameters=new_params)

        # Create the wrapper function dynamically
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return method(self, *args, **kwargs)

        # Set metadata on the wrapper
        wrapper.__name__ = method.__name__
        wrapper.__doc__ = method.__doc__
        wrapper.__signature__ = new_sig
        wrapper.__module__ = method.__module__
        wrapper.__qualname__ = method.__qualname__

        # Set annotations by extracting them from the new signature
        wrapper.__annotations__ = {}
        for param in new_sig.parameters.values():
            if param.annotation != inspect.Parameter.empty:
                wrapper.__annotations__[param.name] = param.annotation

        # Add return annotation if it exists
        if new_sig.return_annotation != inspect.Signature.empty:
            wrapper.__annotations__["return"] = new_sig.return_annotation

        return wrapper

    def _configure_routes(self) -> None:
        """Configure the routes for the REST API."""
        self.router = APIRouter()
        self.router.add_api_route("/status", self.get_status, methods=["GET"])
        self.router.add_api_route("/info", self.get_info, methods=["GET"])
        self.router.add_api_route("/state", self.get_state, methods=["GET"])
        for action, function in self.action_handlers.items():
            self.router.add_api_route(
                f"/action/{action}",
                self.remove_self_wrapper(function),
                methods=["POST"],
            )

        self.router.add_api_route(
            "/action/{action_id}",
            self.get_action_result,
            methods=["GET"],
            response_model=None,
        )
        self.router.add_api_route("/action", self.get_action_history, methods=["GET"])
        self.router.add_api_route("/config", self.set_config, methods=["POST"])
        self.router.add_api_route(
            "/admin/{admin_command}",
            self.run_admin_command,
            methods=["POST"],
        )
        self.router.add_api_route(
            "/log",
            self.get_log,
            methods=["GET"],
        )
        self.rest_api.include_router(self.router)


if __name__ == "__main__":
    RestNode().start_node()
