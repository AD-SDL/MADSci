"""Base node client implementation."""

from typing import Any, ClassVar, Optional

from madsci.common.types.action_types import (
    ActionRequest,
    ActionResult,
)
from madsci.common.types.admin_command_types import AdminCommandResponse
from madsci.common.types.event_types import Event
from madsci.common.types.node_types import (
    AdminCommands,
    NodeClientCapabilities,
    NodeInfo,
    NodeSetConfigResponse,
    NodeStatus,
)
from madsci.common.types.resource_types import ResourceDataModels
from pydantic import AnyUrl


class AbstractNodeClient:
    """Base Node Client, protocol agnostic, all node clients should inherit from or be based on this."""

    url_protocols: ClassVar[list[str]] = []
    """The protocol(s) to use for node URL's using this client."""

    supported_capabilities: ClassVar[NodeClientCapabilities] = NodeClientCapabilities()
    """The capabilities supported by this node client."""

    def __init__(self, url: AnyUrl) -> "AbstractNodeClient":
        """Initialize the client."""
        self.url = url

    def send_action(
        self,
        action_request: ActionRequest,
        await_result: bool = True,
        timeout: Optional[float] = None,
    ) -> ActionResult:
        """Perform an action on the node."""
        raise NotImplementedError("send_action not implemented by this client")

    def get_action_history(self) -> dict[str, list[ActionResult]]:
        """Get the history of a specific action, or all actions run by the node."""
        raise NotImplementedError(
            "get_action_history is not implemented by this client"
        )

    def get_action_result(self, action_id: str) -> ActionResult:
        """Get the status of an action on the node."""
        raise NotImplementedError("get_action_result is not implemented by this client")

    def await_action_result(
        self, action_id: str, timeout: Optional[float] = None
    ) -> ActionResult:
        """Wait for an action to complete and return the result. Optionally, specify a timeout in seconds."""
        raise NotImplementedError(
            "await_action_result is not implemented by this client"
        )

    def get_status(self) -> NodeStatus:
        """Get the status of the node."""
        raise NotImplementedError("get_status is not implemented by this client")

    def get_state(self) -> dict[str, Any]:
        """Get the state of the node."""
        raise NotImplementedError("get_state is not implemented by this client")

    def get_info(self) -> NodeInfo:
        """Get information about the node."""
        raise NotImplementedError("get_info is not implemented by this client")

    def set_config(self, config_dict: dict[str, Any]) -> NodeSetConfigResponse:
        """Set configuration values of the node."""
        raise NotImplementedError("set_config is not implemented by this client")

    def send_admin_command(self, admin_command: AdminCommands) -> AdminCommandResponse:
        """Perform an administrative command on the node."""
        raise NotImplementedError(
            "send_admin_command is not implemented by this client"
        )

    def get_resources(self) -> dict[str, ResourceDataModels]:
        """Get the resources of the node."""
        raise NotImplementedError("get_resources is not implemented by this client")

    def get_log(self) -> dict[str, Event]:
        """Get the log of the node."""
        raise NotImplementedError("get_log is not implemented by this client")

    @classmethod
    def validate_url(cls, url: AnyUrl) -> bool:
        """check if a url matches this node type"""
        protocol = url.scheme
        return protocol in cls.url_protocols
