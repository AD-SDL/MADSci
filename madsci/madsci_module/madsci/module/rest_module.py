"""REST-based module interface and helper classes."""

import json
import os
import shutil
import tempfile
from pathlib import PureWindowsPath
from typing import Any, Dict, List, Union
from zipfile import ZipFile

from fastapi import requests
from fastapi.applications import FastAPI
from fastapi.datastructures import UploadFile
from fastapi.routing import APIRouter
from starlette.datastructures import State
from starlette.responses import FileResponse

from madsci.common.types.action_types import ActionRequest, ActionResponse, ActionStatus
from madsci.common.types.admin_command_types import AdminCommandResponse
from madsci.common.types.module_types import (
    AdminCommands,
    ModuleInterfaceCapabilities,
)
from madsci.common.types.node_types import NodeInfo, NodeSetConfigResponse, NodeStatus
from madsci.module.base_module import BaseModule, BaseModuleInterface


class RestModuleInterface(BaseModuleInterface):
    """REST-based module interface."""

    url_protocols: List[str] = ["http", "https"]
    """The protocols supported by this module interface."""

    supported_capabilities: ModuleInterfaceCapabilities = ModuleInterfaceCapabilities(
        get_info=True,
        get_state=True,
        get_status=True,
        send_action=False,
        get_action=True,
        action_files=True,
        send_admin_commands=True,
        set_config=True,
    )

    def __init__(self, module: BaseModule):
        """Initialize the module interface."""
        super().__init__(module)

    def send_action(self, action_request: ActionRequest) -> ActionResponse:
        """Perform an action on the module."""
        rest_response = requests.post(
            self.module.module_url,
            params={
                "name": action_request.name,
                "args": json.dumps(action_request.args),
            },
            files=[
                ("files", (file, open(path, "rb")))
                for file, path in action_request.files.items()
            ],
        )
        if not rest_response.ok:
            rest_response.raise_for_status()
        return ActionResponse.model_validate(rest_response.json())

    def get_action(self, action_id: str) -> ActionResponse:
        """Get the status of an action on the module."""
        response = requests.get(f"{self.module.module_url}/action/{action_id}")
        if not response.ok:
            response.raise_for_status()
        return ActionResponse.model_validate(response.json())

    def get_status(self) -> NodeStatus:
        """Get the status of the module."""
        response = requests.get(f"{self.module.module_url}/status")
        if not response.ok:
            response.raise_for_status()
        return NodeStatus.model_validate(response.json())

    def get_state(self) -> Dict[str, Any]:
        """Get the state of the module."""
        response = requests.get(f"{self.module.module_url}/state")
        if not response.ok:
            response.raise_for_status()
        return response.json()

    def get_info(self) -> NodeInfo:
        """Get information about the module."""
        response = requests.get(f"{self.module.module_url}/info")
        if not response.ok:
            response.raise_for_status()
        return NodeInfo.model_validate(response.json())

    def set_config(self, config_key: str, config_value: Any) -> NodeSetConfigResponse:
        """Set configuration values of the module."""
        response = requests.post(
            f"{self.module.module_url}/config",
            json={"config_key": config_key, "config_value": config_value},
        )
        if not response.ok:
            response.raise_for_status()
        return NodeSetConfigResponse.model_validate(response.json())

    def send_admin_command(self, admin_command: AdminCommands) -> bool:
        """Perform an administrative command on the module."""
        response = requests.post(
            f"{self.module.module_url}/admin", json={"admin_command": admin_command}
        )
        if not response.ok:
            response.raise_for_status()
        return AdminCommandResponse.model_validate(response.json())


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


class RestModule(BaseModule):
    """REST-based module implementation and helper classes. Inherits from BaseModule. Inherit from this class to create a new module."""

    def start_module(self):
        """Start the node."""
        super().start_module()  # *Kick off protocol agnostic-startup
        self.start_rest_api()

    def start_rest_api(self):
        """Start the REST API for the node."""
        import uvicorn

        self.rest_api = FastAPI()
        self.rest_api.state = State({"node": self})
        self.configure_routes()
        print(self.node_definition.node_config)
        uvicorn.run(self.rest_api, host=self.args.host, port=self.args.port)

    def configure_routes(self):
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
        self.router.add_api_route("/config", self.set_config, methods=["POST"])
        self.router.add_api_route(
            "/admin/{admin_command}", self.run_admin_command, methods=["POST"]
        )
        self.rest_api.include_router(self.router)

    def run_action(
        self, name: str, args: Dict[str, Any] = {}, files: List[UploadFile] = []
    ) -> Union[ActionResponse, ActionResponseWithFiles]:
        """Run an action on the node."""
        with tempfile.TemporaryDirectory() as temp_dir:
            for file in files:
                with open(os.path.join(temp_dir, file.filename), "wb") as f:
                    shutil.copyfileobj(file.file, f)
            response = super().run_action(
                ActionRequest(
                    name=name,
                    args=args,
                    files={
                        file.filename: os.path.join(temp_dir, file.filename)
                        for file in files
                    },
                )
            )
            if response.files:
                return ActionResponseWithFiles().from_action_response(
                    action_response=response
                )
            else:
                return ActionResponse.model_validate(response)

    def get_status(self) -> NodeStatus:
        """Get the status of the node."""
        return super().get_status()

    def get_info(self) -> NodeInfo:
        """Get information about the node."""
        return super().get_info()

    def get_state(self) -> Dict[str, Any]:
        """Get the state of the node."""
        return super().get_state()

    def get_action_response(self, action_id: str) -> ActionResponse:
        """Get the status of an action on the node."""
        return super().get_action_response(action_id)

    def set_config(self, config_key: str, config_value: Any) -> NodeSetConfigResponse:
        """Set configuration values of the node."""
        return super().set_config(config_key, config_value)

    def run_admin_command(self, admin_command: AdminCommands) -> AdminCommandResponse:
        """Perform an administrative command on the node."""
        return super().run_admin_command(admin_command)

    def get_action(self, action_id: str) -> ActionResponse:
        """Get the status of an action on the node."""
        return super().get_action_response(action_id)


if __name__ == "__main__":
    RestModule().start_module()
