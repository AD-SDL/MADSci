"""REST-based module interface and helper classes."""

import json
import os
import shutil
import tempfile
import time
from multiprocessing import Process
from pathlib import PureWindowsPath
from threading import Thread
from typing import Any, Dict, List, Optional, Union
from zipfile import ZipFile

from fastapi.applications import FastAPI
from fastapi.datastructures import UploadFile
from fastapi.routing import APIRouter
from rich import print
from starlette.responses import FileResponse

from madsci.common.types.action_types import ActionRequest, ActionResponse, ActionStatus
from madsci.common.types.admin_command_types import AdminCommandResponse
from madsci.common.types.base_types import Error, new_ulid_str
from madsci.common.types.module_types import (
    AdminCommands,
    ModuleCapabilities,
)
from madsci.common.types.node_types import (
    NodeInfo,
    NodeSetConfigResponse,
    NodeStatus,
)
from madsci.common.utils import threaded_task
from madsci.module.abstract_module import (
    AbstractModule,
)
from madsci.module.interface.rest_module_interface import RestModuleInterface


def action_response_to_headers(action_response: ActionResponse) -> Dict[str, str]:
    """Converts the response to a dictionary of headers"""
    return {
        "x-madsci-action-id": action_response.action_id,
        "x-madsci-status": str(action_response.status),
        "x-madsci-data": json.dumps(action_response.data),
        "x-madsci-error": json.dumps(action_response.error),
        "x-madsci-files": json.dumps(action_response.files),
    }


def action_response_from_headers(headers: Dict[str, Any]) -> ActionResponse:
    """Creates an ActionResponse from the headers of a file response"""

    return ActionResponse(
        action_id=headers["x-madsci-action-id"],
        status=ActionStatus(headers["x-wei-status"]),
        errors=json.loads(headers["x-wei-error"]),
        files=json.loads(headers["x-wei-files"]),
        data=json.loads(headers["x-wei-data"]),
    )


class ActionResponseWithFiles(FileResponse):
    """Action response from a REST-based module."""

    def from_action_response(self, action_response: ActionResponse):
        """Create an ActionResponseWithFiles from an ActionResponse."""
        if len(action_response.files) == 1:
            return super().__init__(
                path=list(action_response.files.values())[0],
                headers=action_response_to_headers(action_response),
            )

        temp_zipfile_path = tempfile.TemporaryFile(suffix=".zip")
        temp_zip = ZipFile(temp_zipfile_path, "w")
        for file in action_response.files:
            temp_zip.write(action_response.files[file])
            action_response.files[file] = str(
                PureWindowsPath(action_response.files[file]).name
            )

        return super().__init__(
            path=temp_zipfile_path,
            headers=action_response_to_headers(action_response),
        )


class RestModule(AbstractModule):
    """REST-based module implementation and helper classes. Inherits from BaseModule. Inherit from this class to create a new module."""

    rest_api = None
    """The REST API server for the node."""
    restart_flag = False
    """Whether the node should restart the REST server."""
    exit_flag = False
    """Whether the node should exit."""
    capabilities: ModuleCapabilities = ModuleCapabilities(
        **RestModuleInterface.supported_capabilities.model_dump()
    )

    """------------------------------------------------------------------------------------------------"""
    """Node Lifecycle and Public Methods"""
    """------------------------------------------------------------------------------------------------"""

    def start_node(self, config: Dict[str, Any] = {}):
        """Start the node."""
        super().start_node(config)  # *Kick off protocol agnostic-startup
        self._start_rest_api()

    """------------------------------------------------------------------------------------------------"""
    """Interface Methods"""
    """------------------------------------------------------------------------------------------------"""

    def run_action(
        self,
        action_name: str,
        args: Optional[str] = None,
        files: List[UploadFile] = [],
        action_id: Optional[str] = None,
    ) -> Union[ActionResponse, ActionResponseWithFiles]:
        """Run an action on the node."""
        if args:
            args = json.loads(args)
            if not isinstance(args, dict):
                raise ValueError("args must be a JSON object")
        else:
            args = {}
        with tempfile.TemporaryDirectory() as temp_dir:
            # * Save the uploaded files to a temporary directory
            for file in files:
                with open(os.path.join(temp_dir, file.filename), "wb") as f:
                    shutil.copyfileobj(file.file, f)
            response = super().run_action(
                ActionRequest(
                    action_id=action_id if action_id else new_ulid_str(),
                    action_name=action_name,
                    args=args,
                    files={
                        file.filename: os.path.join(temp_dir, file.filename)
                        for file in files
                    },
                )
            )
            # * Return a file response if there are files to be returned
            if response.files:
                return ActionResponseWithFiles().from_action_response(
                    action_response=response
                )
            else:
                # * Otherwise, return a normal action response
                return ActionResponse.model_validate(response)

    def get_action(self, action_id: str):
        """Get the status of an action on the node."""
        action_response = super().get_action(action_id)
        if action_response.files:
            return ActionResponseWithFiles().from_action_response(
                action_response=action_response
            )
        else:
            return ActionResponse.model_validate(action_response)

    def get_actions(self) -> List[str]:
        """Get the action history of the node."""
        return super().get_actions()

    def get_status(self) -> NodeStatus:
        """Get the status of the node."""
        return super().get_status()

    def get_info(self) -> NodeInfo:
        """Get information about the node."""
        return super().get_info()

    def get_state(self) -> Dict[str, Any]:
        """Get the state of the node."""
        return super().get_state()

    def set_config(self, config_key: str, config_value: Any) -> NodeSetConfigResponse:
        """Set configuration values of the node."""
        return super().set_config(config_key, config_value)

    def run_admin_command(self, admin_command: AdminCommands) -> AdminCommandResponse:
        """Perform an administrative command on the node."""
        return super().run_admin_command(admin_command)

    """------------------------------------------------------------------------------------------------"""
    """Admin Commands"""
    """------------------------------------------------------------------------------------------------"""

    def reset(self) -> AdminCommandResponse:
        """Restart the node."""
        try:
            self.restart_flag = True  # * Restart the REST server
            self.shutdown_handler()
            self.startup_handler(self.config)
        except Exception as exception:
            return AdminCommandResponse(
                success=False,
                errors=[Error.from_exception(exception)],
            )
        return AdminCommandResponse(
            success=True,
            errors=[],
        )

    def shutdown(self) -> AdminCommandResponse:
        """Shutdown the node."""
        try:
            self.restart_flag = False

            @threaded_task
            def shutdown_server():
                """Shutdown the REST server."""
                time.sleep(2)
                self.rest_server_process.terminate()
                self.exit_flag = True

            shutdown_server()
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

    def _start_rest_api(self):
        """Start the REST API for the node."""
        import uvicorn

        self.rest_api = FastAPI(lifespan=self._lifespan)
        self._configure_routes()
        self.rest_server_process = Process(
            target=uvicorn.run,
            args=(self.rest_api,),
            kwargs={"host": self.config["host"], "port": self.config["port"]},
            daemon=True,
        )
        self.rest_server_process.start()
        while True:
            time.sleep(1)
            if self.restart_flag:
                self.rest_server_process.terminate()
                self.restart_flag = False
                self._start_rest_api()
                break
            if self.exit_flag:
                break

    def _startup_thread(self):
        """The startup thread for the REST API."""
        try:
            # * Create a clean status and mark the node as initializing
            self.node_status.initializing = True
            self.node_status.errored = False
            self.node_status.locked = False
            self.node_status.paused = False
            self.startup_handler()
        except Exception as exception:
            # * Handle any exceptions that occurred during startup
            self._exception_handler(exception)
            self.node_status.errored = True
        finally:
            # * Mark the node as no longer initializing
            print("Startup complete")
            self.node_status.initializing = False

    def _lifespan(self, app: FastAPI):
        """The lifespan of the REST API."""
        # * Run startup on a separate thread so it doesn't block the rest server from starting
        # * (module won't accept actions until startup is complete)
        Thread(target=self._startup_thread, daemon=True).start()
        self._loop_handler()

        yield

        try:
            # * Call any shutdown logic
            self.shutdown_handler()
        except Exception as exception:
            # * If an exception occurs during shutdown, handle it so we at least see the error in logs/terminal
            self._exception_handler(exception)

    def _configure_routes(self):
        """Configure the routes for the REST API."""
        self.router = APIRouter()
        self.router.add_api_route("/status", self.get_status, methods=["GET"])
        self.router.add_api_route("/info", self.get_info, methods=["GET"])
        self.router.add_api_route("/state", self.get_state, methods=["GET"])
        self.router.add_api_route(
            "/action", self.run_action, methods=["POST"], response_model=None
        )
        self.router.add_api_route(
            "/action/{action_id}", self.get_action, methods=["GET"]
        )
        self.router.add_api_route("/action", self.get_actions, methods=["GET"])
        self.router.add_api_route("/config", self.set_config, methods=["POST"])
        self.router.add_api_route(
            "/admin/{admin_command}", self.run_admin_command, methods=["POST"]
        )
        self.rest_api.include_router(self.router)


if __name__ == "__main__":
    RestModule().start_node()
