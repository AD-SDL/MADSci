"""REST-based module interface and helper classes."""

from typing import Any, Dict, List

from fastapi import requests

from madsci.common.types.action_types import ActionResponse
from madsci.common.types.admin_command_types import AdminCommandResponse
from madsci.common.types.module_types import (
    AdminCommands,
    ModuleInfo,
    ModuleInterfaceCapabilities,
    ModuleSetConfigResponse,
    NodeStatus,
)
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

    def send_action(self, name: str, args: None, files: None) -> ActionResponse:
        """Perform an action on the module."""
        raise NotImplementedError(
            "send_action not implemented by this module interface"
        )

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

    def get_info(self) -> ModuleInfo:
        """Get information about the module."""
        response = requests.get(f"{self.module.module_url}/info")
        if not response.ok:
            response.raise_for_status()
        return ModuleInfo.model_validate(response.json())

    def set_config(self, config_key: str, config_value: Any) -> bool:
        """Set configuration values of the module."""
        response = requests.post(
            f"{self.module.module_url}/config",
            json={"config_key": config_key, "config_value": config_value},
        )
        if not response.ok:
            response.raise_for_status()
        return ModuleSetConfigResponse.model_validate(response.json())

    def send_admin_command(self, admin_command: AdminCommands) -> bool:
        """Perform an administrative command on the module."""
        response = requests.post(
            f"{self.module.module_url}/admin", json={"admin_command": admin_command}
        )
        if not response.ok:
            response.raise_for_status()
        return AdminCommandResponse.model_validate(response.json())


class RestModule(BaseModule):
    """REST-based module interface and helper classes. Inherits from BaseModule. Inherit from this class to create a new module."""
