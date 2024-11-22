"""REST-based module interface implementation."""

import json
from typing import Any, Dict, List

import requests

from madsci.common.types.action_types import ActionRequest, ActionResponse
from madsci.common.types.admin_command_types import AdminCommandResponse
from madsci.common.types.module_types import (
    AdminCommands,
    ModuleInterfaceCapabilities,
)
from madsci.common.types.node_types import (
    Node,
    NodeInfo,
    NodeSetConfigResponse,
    NodeStatus,
)
from madsci.common.types.resource_types import ResourceDefinition
from madsci.module.interface.abstract_module_interface import (
    AbstractModuleInterface,
)


class RestModuleInterface(AbstractModuleInterface):
    """REST-based module interface."""

    url_protocols: List[str] = ["http", "https"]
    """The protocols supported by this module interface."""

    supported_capabilities: ModuleInterfaceCapabilities = ModuleInterfaceCapabilities(
        get_info=True,
        get_state=True,
        get_status=True,
        send_action=True,
        get_action=True,
        get_actions=True,
        action_files=True,
        send_admin_commands=True,
        set_config=True,
        get_resources=False,
    )

    def __init__(self, node: Node):
        """Initialize the module interface."""
        super().__init__(node)

    def send_action(self, action_request: ActionRequest) -> ActionResponse:
        """Perform an action on the node."""
        rest_response = requests.post(
            f"{self.node.node_url}/action",
            params={
                "action_name": action_request.action_name,
                "args": json.dumps(action_request.args),
                "action_id": action_request.action_id,
            },
            files=[
                ("files", (file, open(path, "rb")))
                for file, path in action_request.files.items()
            ],
        )
        if not rest_response.ok:
            rest_response.raise_for_status()
        return ActionResponse.model_validate(rest_response.json())

    def get_actions(self) -> List[str]:
        """Get a list of the action IDs for actions that the node has recently performed."""
        response = requests.get(f"{self.node.node_url}/action")
        if not response.ok:
            response.raise_for_status()
        return response.json()

    def get_action(self, action_id: str) -> ActionResponse:
        """Get the status of an action on the module."""
        response = requests.get(f"{self.node.node_url}/action/{action_id}")
        if not response.ok:
            response.raise_for_status()
        return ActionResponse.model_validate(response.json())

    def get_status(self) -> NodeStatus:
        """Get the status of the module."""
        response = requests.get(f"{self.node.node_url}/status")
        if not response.ok:
            response.raise_for_status()
        return NodeStatus.model_validate(response.json())

    def get_state(self) -> Dict[str, Any]:
        """Get the state of the module."""
        response = requests.get(f"{self.node.node_url}/state")
        if not response.ok:
            response.raise_for_status()
        return response.json()

    def get_info(self) -> NodeInfo:
        """Get information about the module."""
        response = requests.get(f"{self.node.node_url}/info")
        if not response.ok:
            response.raise_for_status()
        return NodeInfo.model_validate(response.json())

    def set_config(self, config_dict: Dict[str, Any]) -> NodeSetConfigResponse:
        """Set configuration values of the module."""
        response = requests.post(
            f"{self.node.node_url}/config",
            json=config_dict,
        )
        if not response.ok:
            response.raise_for_status()
        return NodeSetConfigResponse.model_validate(response.json())

    def send_admin_command(self, admin_command: AdminCommands) -> bool:
        """Perform an administrative command on the module."""
        response = requests.post(
            f"{self.node.node_url}/admin", json={"admin_command": admin_command}
        )
        if not response.ok:
            response.raise_for_status()
        return AdminCommandResponse.model_validate(response.json())

    def get_resources(self) -> Dict[str, ResourceDefinition]:
        """Get the resources of the node."""
        raise NotImplementedError(
            "get_resources is not implemented by this module interface"
        )
        # TODO: Implement get_resources endpoint
        # response = requests.get(f"{self.node.node_url}/resources")
        # if not response.ok:
        #     response.raise_for_status()
        # return response.json()
