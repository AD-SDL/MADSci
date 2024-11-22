"""Base module interface implementation."""

from typing import Any, Dict, List

from madsci.common.types.action_types import (
    ActionRequest,
    ActionResponse,
)
from madsci.common.types.admin_command_types import AdminCommandResponse
from madsci.common.types.event_types import Event
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


class AbstractModuleInterface:
    """Base Module Interface, protocol agnostic, all module interfaces should inherit from or be based on this."""

    url_protocols: List[str] = []
    """The protocol(s) to use for node URL's using this interface."""

    supported_capabilities: ModuleInterfaceCapabilities = ModuleInterfaceCapabilities()
    """The capabilities supported by this module interface. Note that some capabilities may be supported by the module, but not by the interface (i.e. the 'resources' capability is not implemented at the interface level)."""

    def __init__(self, node: Node):
        """Initialize the module interface."""
        self.node = node

    def send_action(self, action_request: ActionRequest) -> ActionResponse:
        """Perform an action on the node."""
        raise NotImplementedError(
            "send_action not implemented by this module interface"
        )

    def get_actions(self) -> List[str]:
        """Get a list of the action IDs for actions that the node has recently performed."""
        raise NotImplementedError(
            "get_actions is not implemented by this module interface"
        )

    def get_action(self, action_id: str) -> ActionResponse:
        """Get the status of an action on the node."""
        raise NotImplementedError(
            "get_action is not implemented by this module interface"
        )

    def get_status(self) -> NodeStatus:
        """Get the status of the node."""
        raise NotImplementedError(
            "get_status is not implemented by this module interface"
        )

    def get_state(self) -> Dict[str, Any]:
        """Get the state of the node."""
        raise NotImplementedError(
            "get_state is not implemented by this module interface"
        )

    def get_info(self) -> NodeInfo:
        """Get information about the node and module."""
        raise NotImplementedError(
            "get_info is not implemented by this module interface"
        )

    def set_config(self, config_dict: Dict[str, Any]) -> NodeSetConfigResponse:
        """Set configuration values of the node."""
        raise NotImplementedError(
            "set_config is not implemented by this module interface"
        )

    def send_admin_command(self, admin_command: AdminCommands) -> AdminCommandResponse:
        """Perform an administrative command on the node."""
        raise NotImplementedError(
            "send_admin_command is not implemented by this module interface"
        )

    def get_resources(self) -> Dict[str, ResourceDefinition]:
        """Get the resources of the node."""
        raise NotImplementedError(
            "get_resources is not implemented by this module interface"
        )

    def get_log(self) -> List[Event]:
        """Get the log of the node."""
        raise NotImplementedError("get_log is not implemented by this module interface")
