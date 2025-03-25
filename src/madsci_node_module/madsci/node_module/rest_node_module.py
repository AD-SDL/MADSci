"""REST-based Node Module helper classes."""

import json
import os
import shutil
import signal
import tempfile
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Optional, Union

from fastapi.applications import FastAPI
from fastapi.background import BackgroundTasks
from fastapi.datastructures import UploadFile
from fastapi.routing import APIRouter
from madsci.client.node.rest_node_client import RestNodeClient
from madsci.common.types.action_types import (
    ActionRequest,
    ActionResult,
)
from madsci.common.types.admin_command_types import AdminCommandResponse
from madsci.common.types.base_types import Error, new_ulid_str
from madsci.common.types.event_types import Event
from madsci.common.types.node_types import (
    AdminCommands,
    NodeClientCapabilities,
    NodeConfig,
    NodeInfo,
    NodeSetConfigResponse,
    NodeStatus,
    RestNodeConfig,
)
from madsci.node_module.abstract_node_module import (
    AbstractNode,
)
from madsci.node_module.helpers import ActionResultWithFiles
from pydantic import AnyUrl


class RestNode(AbstractNode):
    """REST-based node implementation and helper class. Inherit from this class to create a new REST-based node class."""

    rest_api = None
    """The REST API server for the node."""
    supported_capabilities: NodeClientCapabilities = (
        RestNodeClient.supported_capabilities
    )
    """The default supported capabilities of this node module class."""
    config: NodeConfig = RestNodeConfig()
    """The configuration for the node."""

    """------------------------------------------------------------------------------------------------"""
    """Node Lifecycle and Public Methods"""
    """------------------------------------------------------------------------------------------------"""

    def __init__(self, *args: Any, **kwargs: Any) -> "RestNode":
        """Initialize the node class."""
        super().__init__(*args, **kwargs)
        host = getattr(self.config, "host", "localhost")
        port = getattr(self.config, "port", 2000)
        scheme = getattr(self.config, "protocol", "http")
        self.node_info.node_url = AnyUrl.build(
            scheme=scheme,
            host=host,
            port=port,
        )

    def start_node(self, testing: bool = False) -> None:
        """Start the node."""
        host = getattr(self.config, "host", "localhost")
        port = getattr(self.config, "port", 2000)
        if not testing:
            self.logger.log_debug("Running node in production mode")
            import uvicorn

            self.rest_api = FastAPI(lifespan=self._lifespan)
            self._configure_routes()
            uvicorn.run(self.rest_api, host=host, port=port)
        else:
            self.logger.log_debug("Running node in test mode")
            self.rest_api = FastAPI(lifespan=self._lifespan)
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
        with tempfile.TemporaryDirectory() as temp_dir:
            # * Save the uploaded files to a temporary directory
            for i in range(len(files)):
                file = files[i]
                with (Path(temp_dir) / file.filename).open("wb") as f:
                    shutil.copyfileobj(file.file, f)
            response = super().run_action(
                ActionRequest(
                    action_id=action_id if action_id else new_ulid_str(),
                    action_name=action_name,
                    args=args,
                    files={
                        file.filename: Path(temp_dir) / file.filename for file in files
                    },
                ),
            )
            # * Return a file response if there are files to be returned
            if response.files:
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

    def _configure_routes(self) -> None:
        """Configure the routes for the REST API."""
        self.router = APIRouter()
        self.router.add_api_route("/status", self.get_status, methods=["GET"])
        self.router.add_api_route("/info", self.get_info, methods=["GET"])
        self.router.add_api_route("/state", self.get_state, methods=["GET"])
        self.router.add_api_route(
            "/action",
            self.run_action,
            methods=["POST"],
            response_model=None,
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
