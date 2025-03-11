"MADSci Node Types."

from datetime import datetime
from enum import Enum
from typing import Any, ClassVar, Optional

from madsci.common.types.action_types import ActionDefinition
from madsci.common.types.admin_command_types import AdminCommands
from madsci.common.types.auth_types import OwnershipInfo
from madsci.common.types.base_types import BaseModel, Error, new_ulid_str
from madsci.common.types.event_types import EventClientConfig
from madsci.common.validators import ulid_validator
from pydantic import SerializationInfo, SerializerFunctionWrapHandler, model_serializer
from pydantic.config import ConfigDict
from pydantic.fields import computed_field
from pydantic.functional_validators import field_validator
from pydantic.networks import AnyUrl
from pydantic_extra_types.semantic_version import SemanticVersion
from semver import Version
from sqlmodel.main import Field


class NodeType(str, Enum):
    """The type of a MADSci node."""

    DEVICE = "device"
    COMPUTE = "compute"
    RESOURCE_MANAGER = "resource_manager"
    EVENT_MANAGER = "event_manager"
    WORKCELL_MANAGER = "workcell_manager"
    DATA_MANAGER = "data_manager"
    TRANSFER_MANAGER = "transfer_manager"


class NodeConfig(BaseModel):
    """Basic Configuration for a MADSci Node."""

    model_config = ConfigDict(extra="allow")

    status_update_interval: Optional[float] = Field(
        title="Status Update Interval",
        description="The interval in seconds at which the node should update its status.",
        default=None,
    )
    state_update_interval: Optional[float] = Field(
        title="State Update Interval",
        description="The interval in seconds at which the node should update its state.",
        default=None,
    )
    event_client_config: Optional[EventClientConfig] = Field(
        title="Event Client Configuration",
        description="The configuration for a MADSci event client.",
        default=None,
    )


class RestNodeConfig(NodeConfig):
    """Default Configuration for a MADSci Node that communicates over REST."""

    host: str = Field(
        title="Host",
        description="The host of the REST API.",
        default="127.0.0.1",
    )
    port: int = Field(
        title="Port",
        description="The port of the REST API.",
        default=8000,
    )
    protocol: str = Field(
        title="Protocol",
        description="The protocol of the REST API, either 'http' or 'https'.",
        default="http",
    )


class NodeClientCapabilities(BaseModel):
    """Capabilities of a MADSci Node Client. Default values are None, meaning the capability is not explicitly set. If a capability is set to False, it is explicitly not supported."""

    get_info: Optional[bool] = Field(
        default=None,
        title="Node Info",
        description="Whether the node supports querying its info.",
    )
    get_state: Optional[bool] = Field(
        default=None,
        title="Node State",
        description="Whether the node supports querying its state.",
    )
    get_status: Optional[bool] = Field(
        default=None,
        title="Node Status",
        description="Whether the node supports querying its status.",
    )
    send_action: Optional[bool] = Field(
        default=None,
        title="Node Send Action",
        description="Whether the node supports sending actions.",
    )
    get_action_result: Optional[bool] = Field(
        default=None,
        title="Node Get Action",
        description="Whether the node supports querying the status of an action.",
    )
    get_action_history: Optional[bool] = Field(
        default=None,
        title="Node Get Actions",
        description="Whether the node supports querying the history of actions.",
    )
    action_files: Optional[bool] = Field(
        default=None,
        title="Node Action Files",
        description="Whether the node supports sending action files.",
    )
    send_admin_commands: Optional[bool] = Field(
        default=None,
        title="Node Send Admin Commands",
        description="Whether the node supports sending admin commands.",
    )
    set_config: Optional[bool] = Field(
        default=None,
        title="Node Set Config",
        description="Whether the node supports setting configuration.",
    )
    get_resources: Optional[bool] = Field(
        default=None,
        title="Node Get Resources",
        description="Whether the node supports querying its resources.",
    )
    get_log: Optional[bool] = Field(
        default=None,
        title="Node Get Log",
        description="Whether the node supports querying its log.",
    )

    @model_serializer(mode="wrap")
    def exclude_unset_by_default(
        self, nxt: SerializerFunctionWrapHandler, info: SerializationInfo
    ) -> dict[str, Any]:
        """Exclude unset fields by default."""
        serialized = nxt(self, info)
        return {k: v for k, v in serialized.items() if v is not None}


class NodeCapabilities(NodeClientCapabilities):
    """Capabilities of a MADSci Node."""

    events: Optional[bool] = Field(
        default=None,
        title="Node Events",
        description="Whether the node supports raising MADSci events.",
    )
    resources: Optional[bool] = Field(
        default=None,
        title="Node Resources",
        description="Whether the node supports MADSci-compatible resource management.",
    )
    admin_commands: set[AdminCommands] = Field(
        default=set(),
        title="Node Admin Commands",
        description="Which admin commands the node supports, if any.",
    )


class NodeDefinition(BaseModel):
    """Definition of a MADSci Node, a unique instance of a MADSci Node Module."""

    _definition_file_patterns: ClassVar[list[str]] = ["*.node.yaml"]

    node_name: str = Field(title="Node Name", description="The name of the node.")
    node_id: str = Field(
        title="Node ID", description="The ID of the node.", default_factory=new_ulid_str
    )
    node_url: Optional[AnyUrl] = Field(
        title="Node URL",
        description="The URL used to communicate with the node.",
        default=None,
    )
    node_description: Optional[str] = Field(
        title="Description",
        description="A description of the node.",
        default=None,
    )
    node_type: Optional[NodeType] = Field(
        title="Node Type",
        description="The type of thing this node provides an interface for.",
        default=None,
    )
    module_name: str = Field(
        title="Node Module Name",
        description="The name of the node module.",
    )
    module_version: SemanticVersion = Field(
        default=Version.parse("0.0.1"),
        title="Module Version",
        description="The version of the node module.",
    )
    capabilities: "NodeCapabilities" = Field(
        default_factory=lambda: NodeCapabilities(),
        title="Node Capabilities",
        description="The capabilities of the node.",
    )
    commands: dict[str, str] = Field(
        title="Node Commands",
        description="The commands that the node supports. These can be used to stop, start, or otherwise administrate the node(s).",
        default_factory=dict,
    )
    is_template: bool = Field(
        default=False,
        title="Is Template",
        description="Whether this is a template definition.",
    )
    config_defaults: dict[str, Any] = Field(
        default_factory=dict,
        title="Node Configuration Defaults",
        description="Default values to use for configuration parameters for this particular node.",
    )

    is_ulid = field_validator("node_id")(ulid_validator)

    @model_serializer(mode="wrap")
    def exclude_node_id_on_templates(
        self, nxt: SerializerFunctionWrapHandler, info: SerializationInfo
    ) -> dict[str, Any]:
        """Exclude node_id on templates."""
        serialized = nxt(self, info)
        if self.is_template:
            serialized.pop("node_id")
        return serialized


class Node(BaseModel, arbitrary_types_allowed=True):
    """A runtime representation of a MADSci Node used in a Workcell."""

    node_url: AnyUrl = Field(
        title="Node URL",
        description="The URL used to communicate with the node.",
    )
    status: Optional["NodeStatus"] = Field(
        default=None,
        title="Node Status",
        description="The status of the node. Set to None if the node does not support status reporting or the status is unknown (e.g. if it hasn't reported/responded to status requests).",
    )
    info: Optional["NodeInfo"] = Field(
        default=None,
        title="Node Info",
        description="Information about the node, provided by the node itself.",
    )
    state: Optional[dict[str, Any]] = Field(
        default=None,
        title="Node State",
        description="Detailed nodes specific state information",
    )
    reserved_by: Optional["NodeReservation"] = Field(
        default=None,
        title="Reserved By",
        description="Ownership unit that is reserving this node",
    )


class NodeInfo(NodeDefinition):
    """Information about a MADSci Node."""

    actions: dict[str, "ActionDefinition"] = Field(
        title="Node Actions",
        description="The actions that the node supports.",
        default_factory=dict,
    )
    config: Optional[Any] = Field(
        default=None,
        title="Node Configuration",
        description="The current configuration of the node.",
    )
    config_schema: Optional[dict[str, Any]] = Field(
        title="Node Configuration Schema",
        description="JSON Schema for the configuration of the node.",
        default_factory=NodeConfig.model_json_schema,
    )

    @classmethod
    def from_node_def_and_config(
        cls,
        node: NodeDefinition,
        config: Optional[NodeConfig] = None,
    ) -> "NodeInfo":
        """Create a NodeInfo from a NodeDefinition and config."""
        return cls(
            **node.model_dump(exclude={"commands"}),
            config=config,
            config_schema=config.model_json_schema(),
        )


class NodeStatus(BaseModel):
    """Status of a MADSci Node."""

    busy: bool = Field(
        default=False,
        title="Node Busy",
        description="Whether the node is currently at capacity, i.e. running the maximum number of actions allowed.",
    )
    running_actions: set[str] = Field(
        default_factory=set,
        title="Running Action IDs",
        description="The IDs of the actions that the node is currently running.",
    )
    paused: bool = Field(
        default=False,
        title="Node Paused",
        description="Whether the node is paused.",
    )
    locked: bool = Field(
        default=False,
        title="Node Locked",
        description="Whether the node is locked, preventing it from accepting any actions.",
    )
    stopped: bool = Field(
        default=False,
        title="Node Stopped",
        description="Whether the node has been stopped (e.g. due to a safety stop).",
    )
    errored: bool = Field(
        default=False,
        title="Node Errored",
        description="Whether the node is in an errored state.",
    )
    errors: list[Error] = Field(
        default_factory=list,
        title="Node Errors",
        description="A list of errors that the node has encountered.",
    )
    initializing: bool = Field(
        default=False,
        title="Node Initializing",
        description="Whether the node is currently initializing.",
    )
    waiting_for_config: set[str] = Field(
        default_factory=set,
        title="Node Waiting for Configuration",
        description="Set of configuration parameters that the node is waiting for.",
    )
    config_values: dict[str, Any] = Field(
        default_factory=dict,
        title="Node Configuration Values",
        description="The current configuration values of the node.",
    )

    @computed_field
    @property
    def ready(self) -> bool:
        """Whether the node is ready to accept actions."""
        ready = True
        if self.busy:
            ready = False
        if self.locked:
            ready = False
        if self.stopped:
            ready = False
        if self.errored:
            ready = False
        if self.initializing:
            ready = False
        if self.paused:
            ready = False
        if len(self.waiting_for_config) > 0:
            ready = False
        return ready

    @computed_field
    @property
    def description(self) -> str:
        """A description of the node's status."""
        reasons = []
        if self.busy:
            reasons.append("Node is busy")
        if self.locked:
            reasons.append("Node is locked")
        if self.errored:
            reasons.append("Node is in an error state")
        if self.initializing:
            reasons.append("Node is initializing")
        if self.paused:
            reasons.append("Node is paused")
        if len(self.waiting_for_config) > 0:
            reasons.append(
                f"Node is missing configuration values: {self.waiting_for_config}",
            )
        if reasons:
            return "; ".join(reasons)
        return "Node is ready"


class NodeReservation(BaseModel):
    """Reservation of a MADSci Node."""

    owned_by: OwnershipInfo = Field(
        title="Owned By",
        description="Who has ownership of the reservation.",
    )
    created: datetime = Field(
        title="Created Datetime",
        description="When the reservation was created.",
    )
    start: datetime = Field(
        title="Start Datetime",
        description="When the reservation starts.",
    )
    end: datetime = Field(
        title="End Datetime",
        description="When the reservation ends.",
    )


class NodeSetConfigResponse(BaseModel):
    """Response from a Node Set Config Request"""

    success: bool = Field(
        title="Success",
        description="Whether the config was successfully set.",
    )
