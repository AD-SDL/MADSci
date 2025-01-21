"""REST-based node client implementation."""

import json
from pathlib import Path
from typing import Any, ClassVar

import requests
from madsci.client.node.abstract_node_client import (
    AbstractNodeClient,
)
from madsci.common.types.action_types import ActionRequest, ActionResult
from madsci.common.types.admin_command_types import AdminCommandResponse
from madsci.common.types.event_types import Event
from madsci.common.types.node_types import (
    AdminCommands,
    Node,
    NodeClientCapabilities,
    NodeInfo,
    NodeSetConfigResponse,
    NodeStatus,
)
from madsci.common.types.resource_types import ResourceDefinition


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

    def __init__(self, node: Node) -> "RestNodeClient":
        """Initialize the client."""
        super().__init__(node)

    def send_action(self, action_request: ActionRequest) -> ActionResult:
        """Perform an action on the node."""
        files = []
        try:
            files = [
                ("files", (file, Path(path).open("rb")))  # noqa: SIM115
                for file, path in action_request.files.items()
            ]
            self.logger.log_debug(files)

            rest_response = requests.post(
                f"{self.node.node_url}/action",
                params={
                    "action_name": action_request.action_name,
                    "args": json.dumps(action_request.args),
                    "action_id": action_request.action_id,
                },
                files=files,
                timeout=10,
            )
        finally:
            # * Ensure files are closed
            for file in files:
                file[1].close()
        if not rest_response.ok:
            rest_response.raise_for_status()
        return ActionResult.model_validate(rest_response.json())

    def get_action_history(self) -> list[str]:
        """Get a list of the action IDs for actions that the node has recently performed."""
        response = requests.get(f"{self.node.node_url}/action", timeout=10)
        if not response.ok:
            response.raise_for_status()
        return response.json()

    def get_action_result(self, action_id: str) -> ActionResult:
        """Get the result of an action on the node."""
        response = requests.get(
            f"{self.node.node_url}/action/{action_id}",
            timeout=10,
        )
        if not response.ok:
            response.raise_for_status()
        return ActionResult.model_validate(response.json())

    def get_status(self) -> NodeStatus:
        """Get the status of the node."""
        response = requests.get(f"{self.node.node_url}/status", timeout=10)
        if not response.ok:
            response.raise_for_status()
        return NodeStatus.model_validate(response.json())

    def get_state(self) -> dict[str, Any]:
        """Get the state of the node."""
        response = requests.get(f"{self.node.node_url}/state", timeout=10)
        if not response.ok:
            response.raise_for_status()
        return response.json()

    def get_info(self) -> NodeInfo:
        """Get information about the node and module."""
        response = requests.get(f"{self.node.node_url}/info", timeout=10)
        if not response.ok:
            response.raise_for_status()
        return NodeInfo.model_validate(response.json())

    def set_config(self, config_dict: dict[str, Any]) -> NodeSetConfigResponse:
        """Set configuration values of the node."""
        response = requests.post(
            f"{self.node.node_url}/config",
            json=config_dict,
            timeout=60,
        )
        if not response.ok:
            response.raise_for_status()
        return NodeSetConfigResponse.model_validate(response.json())

    def send_admin_command(self, admin_command: AdminCommands) -> bool:
        """Perform an administrative command on the node."""
        response = requests.post(
            f"{self.node.node_url}/admin",
            json={"admin_command": admin_command},
            timeout=10,
        )
        if not response.ok:
            response.raise_for_status()
        return AdminCommandResponse.model_validate(response.json())

    def get_resources(self) -> dict[str, ResourceDefinition]:
        """Get the resources of the node."""
        raise NotImplementedError(
            "get_resources is not implemented by this client",
        )
        # TODO: Implement get_resources endpoint

    def get_log(self) -> list[Event]:
        """Get the log from the node"""
        response = requests.get(f"{self.node.node_url}/log", timeout=10)
        if not response.ok:
            response.raise_for_status()
        return response.json()
