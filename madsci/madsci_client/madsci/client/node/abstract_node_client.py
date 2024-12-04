"""Base node client implementation."""

from typing import Any, ClassVar

from madsci.common.types.action_types import (
    ActionRequest,
    ActionResult,
)
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


class AbstractNodeClient:
    """Base Node Client, protocol agnostic, all node clients should inherit from or be based on this."""

    url_protocols: ClassVar[list[str]] = []
    """The protocol(s) to use for node URL's using this client."""

    supported_capabilities: ClassVar[NodeClientCapabilities] = NodeClientCapabilities()
    """The capabilities supported by this node client."""

    def __init__(self, node: Node) -> "AbstractNodeClient":
        """Initialize the client."""
        self.node = node

    def send_action(self, action_request: ActionRequest) -> ActionResult:
        """Perform an action on the node."""
        raise NotImplementedError("send_action not implemented by this client")

    def get_action_history(self) -> list[str]:
        """Get a list of the action IDs for actions that the node has recently performed."""
        raise NotImplementedError(
            "get_action_history is not implemented by this client"
        )

    def get_action_result(self, action_id: str) -> ActionResult:
        """Get the status of an action on the node."""
        raise NotImplementedError("get_action_result is not implemented by this client")

    def get_status(self) -> NodeStatus:
        """Get the status of the node."""
        raise NotImplementedError("get_status is not implemented by this client")

    def get_state(self) -> dict[str, Any]:
        """Get the state of the node."""
        raise NotImplementedError("get_state is not implemented by this client")

    def get_info(self) -> NodeInfo:
        """Get information about the node and module."""
        raise NotImplementedError("get_info is not implemented by this client")

    def set_config(self, config_dict: dict[str, Any]) -> NodeSetConfigResponse:
        """Set configuration values of the node."""
        raise NotImplementedError("set_config is not implemented by this client")

    def send_admin_command(self, admin_command: AdminCommands) -> AdminCommandResponse:
        """Perform an administrative command on the node."""
        raise NotImplementedError(
            "send_admin_command is not implemented by this client"
        )

    def get_resources(self) -> dict[str, ResourceDefinition]:
        """Get the resources of the node."""
        raise NotImplementedError("get_resources is not implemented by this client")

    def get_log(self) -> list[Event]:
        """Get the log of the node."""
        raise NotImplementedError("get_log is not implemented by this client")
