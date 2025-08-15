"""REST-based node client implementation."""

import json
import tempfile
import time
from pathlib import Path
from typing import Any, ClassVar, Optional
from zipfile import ZipFile

import requests
from madsci.client.event_client import EventClient
from madsci.client.node.abstract_node_client import (
    AbstractNodeClient,
)
from madsci.common.types.action_types import ActionRequest, ActionResult, ActionStatus
from madsci.common.types.admin_command_types import AdminCommandResponse
from madsci.common.types.event_types import Event
from madsci.common.types.node_types import (
    AdminCommands,
    NodeClientCapabilities,
    NodeInfo,
    NodeSetConfigResponse,
    NodeStatus,
)
from madsci.common.types.resource_types.definitions import ResourceDefinition
from pydantic import AnyUrl


class RestNodeClient(AbstractNodeClient):
    """REST-based node client."""

    url_protocols: ClassVar[list[str]] = ["http", "https"]
    """The protocols supported by this client."""

    supported_capabilities: NodeClientCapabilities = NodeClientCapabilities(
        # *Supported capabilities
        get_info=True,
        get_state=True,
        get_status=True,
        send_action=True,
        get_action_result=True,
        get_action_history=True,
        action_files=True,
        send_admin_commands=True,
        set_config=True,
        get_log=True,
        # *Unsupported Capabilities
        get_resources=False,
    )

    def __init__(self, url: AnyUrl) -> "RestNodeClient":
        """Initialize the client."""
        super().__init__(url)
        self.logger = EventClient()

    def send_action(
        self,
        action_request: ActionRequest,
        await_result: bool = True,
        timeout: Optional[float] = None,
    ) -> ActionResult:
        """Perform an action on the node."""
        files = []
        try:
            files = [
                ("files", (file, Path(path).expanduser().open("rb")))
                for file, path in action_request.files.items()
            ]

            serialized_args = action_request.model_dump(mode="json")["args"]

            rest_response = requests.post(
                f"{self.url}/action",
                params={
                    "action_name": action_request.action_name,
                    "args": json.dumps(serialized_args),
                    "action_id": action_request.action_id,
                },
                files=files,
                timeout=60,
            )
        finally:
            # * Ensure files are closed
            for file in files:
                file[1][1].close()
        try:
            rest_response.raise_for_status()
        except requests.HTTPError as e:
            self.logger.log_error(f"{rest_response.status_code}: {rest_response.text}")
            raise e
        if "x-madsci-status" in rest_response.headers:
            self.logger.log_info("Processing file response")
            response = process_file_response(rest_response)
        else:
            self.logger.log_info("Processing JSON response")
            response = ActionResult.model_validate(rest_response.json())
        self.logger.log_info(response)
        if await_result and not response.status.is_terminal:
            response = self.await_action_result(response.action_id, timeout=timeout)
        return response

    def get_action_history(
        self, action_id: Optional[str] = None
    ) -> dict[str, list[ActionResult]]:
        """Get the history of a single action performed on the node, or every action, if no action_id is specified."""
        response = requests.get(
            f"{self.url}/action", params={"action_id": action_id}, timeout=10
        )
        response.raise_for_status()
        return response.json()

    def get_action_result(self, action_id: str) -> ActionResult:
        """Get the result of an action on the node."""
        rest_response = requests.get(
            f"{self.url}/action/{action_id}",
            timeout=10,
        )
        rest_response.raise_for_status()
        if "x-madsci-status" in rest_response.headers:
            response = process_file_response(rest_response)
        else:
            response = ActionResult.model_validate(rest_response.json())
        return response

    def await_action_result(
        self, action_id: str, timeout: Optional[float] = None
    ) -> ActionResult:
        """Wait for an action to complete and return the result. Optionally, specify a timeout in seconds."""
        start_time = time.time()
        interval = 0.25
        while True:
            if timeout is not None and time.time() - start_time > timeout:
                raise TimeoutError("Timed out waiting for action to complete.")
            response = self.get_action_result(action_id)
            if not response.status.is_terminal:
                time.sleep(interval)
                interval = (
                    interval * 1.5 if interval < 5 else 5
                )  # * Capped Exponential backoff
                continue
            return response

    def get_status(self) -> NodeStatus:
        """Get the status of the node."""
        response = requests.get(f"{self.url}/status", timeout=10)
        response.raise_for_status()
        return NodeStatus.model_validate(response.json())

    def get_state(self) -> dict[str, Any]:
        """Get the state of the node."""
        response = requests.get(f"{self.url}/state", timeout=10)
        response.raise_for_status()
        return response.json()

    def get_info(self) -> NodeInfo:
        """Get information about the node."""
        response = requests.get(f"{self.url}/info", timeout=10)
        response.raise_for_status()
        return NodeInfo.model_validate(response.json())

    def set_config(self, new_config: dict[str, Any]) -> NodeSetConfigResponse:
        """Update configuration values of the node."""
        response = requests.post(
            f"{self.url}/config",
            json=new_config,
            timeout=60,
        )
        response.raise_for_status()
        return NodeSetConfigResponse.model_validate(response.json())

    def send_admin_command(self, admin_command: AdminCommands) -> bool:
        """Perform an administrative command on the node."""
        response = requests.post(f"{self.url}/admin/{admin_command}", timeout=10)
        response.raise_for_status()
        return AdminCommandResponse.model_validate(response.json())

    def get_resources(self) -> dict[str, ResourceDefinition]:
        """Get the resources of the node."""
        raise NotImplementedError(
            "get_resources is not implemented by this client",
        )
        # TODO: Implement get_resources endpoint

    def get_log(self) -> dict[str, Event]:
        """Get the log from the node"""
        response = requests.get(f"{self.url}/log", timeout=10)
        response.raise_for_status()
        return response.json()


def action_response_from_headers(headers: dict[str, Any]) -> ActionResult:
    """Creates an ActionResult from the headers of a file response"""

    return ActionResult(
        action_id=headers["x-madsci-action-id"],
        status=ActionStatus(headers["x-madsci-status"]),
        errors=json.loads(headers["x-madsci-errors"]),
        files=json.loads(headers["x-madsci-files"]),
        datapoints=json.loads(headers["x-madsci-datapoints"]),
        data=json.loads(headers["x-madsci-data"]),
    )


def process_file_response(rest_response: requests.Response) -> ActionResult:
    """Process a file rest response, saving files and getting headers"""
    response = action_response_from_headers(rest_response.headers)
    if response.files and len(response.files) == 1:
        file_key = next(iter(response.files.keys()))
        filename = response.files[file_key]
        with tempfile.NamedTemporaryFile(
            suffix="".join(Path(filename).suffixes), delete=False
        ) as temp_file:
            temp_file.write(rest_response.content)
            temp_path = Path(temp_file.name)
        response.files[file_key] = temp_path
    elif response.files and len(response.files) > 1:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as temp_zip:
            temp_zip.write(rest_response.content)
            temp_zip_path = Path(temp_zip.name)
        with ZipFile(temp_zip_path) as zip_file:
            for file_key in list(response.files.keys()):
                filename = response.files[file_key]
                with tempfile.NamedTemporaryFile(
                    suffix="".join(Path(filename).suffixes), delete=False
                ) as temp_file:
                    temp_file.write(zip_file.read(filename))
                    temp_path = Path(temp_file.name)
                response.files[file_key] = temp_path
    return response
