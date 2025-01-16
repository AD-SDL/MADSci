"""MADSci Node Types."""

from enum import Enum
from os import PathLike
from pathlib import Path
from typing import Any, Optional, Union

from madsci.common.types.action_types import ActionDefinition
from madsci.common.types.admin_command_types import AdminCommands
from madsci.common.types.base_types import BaseModel, Error, new_ulid_str
from madsci.common.types.config_types import (
    ConfigNamespaceDefinition,
    ConfigParameterDefinition,
)
from madsci.common.validators import ulid_validator
from pydantic.fields import computed_field
from pydantic.functional_validators import field_validator
from pydantic.networks import AnyUrl
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


class NodeModuleDefinition(BaseModel, extra="allow"):
    """Definition for a MADSci Node Module."""

    module_name: str = Field(
        title="Node Module Name",
        description="The name of the node module.",
    )
    module_type: Optional[NodeType] = Field(
        title="Module Type",
        description="The type of the node module.",
        default=None,
    )
    module_description: Optional[str] = Field(
        default=None,
        title="Module Description",
        description="A description of the node module.",
    )
    capabilities: "NodeCapabilities" = Field(
        default_factory=lambda: NodeCapabilities(),
        title="Module Capabilities",
        description="The capabilities of the node module.",
    )
    config: Union[
        list[Union[ConfigParameterDefinition, ConfigNamespaceDefinition]],
        dict[str, Union[ConfigParameterDefinition, ConfigNamespaceDefinition]],
    ] = Field(
        title="Module Configuration",
        description="The configuration of the node module. These are 'default' configuration parameters inherited by all child nodes.",
        default_factory=list,
    )
    commands: dict[str, str] = Field(
        title="Module Commands",
        description="The commands that the node module supports. These are 'default' commands inherited by all child nodes.",
        default_factory=dict,
    )

    @field_validator("config", mode="after")
    @classmethod
    def validate_config(
        cls,
        v: Union[
            list["ConfigParameterDefinition"], dict[str, "ConfigParameterDefinition"]
        ],
    ) -> Union[
        list["ConfigParameterDefinition"], dict[str, "ConfigParameterDefinition"]
    ]:
        """Validate the node module configuration, promoting a list of ConfigParameters to a dictionary for easier access."""
        if isinstance(v, dict):
            return v
        return {
            param.name if hasattr(param, "name") else param.namespace: param
            for param in v
        }


NODE_MODULE_CONFIG_TEMPLATES: dict[str, list[ConfigParameterDefinition]] = {
    "REST Node": [
        ConfigParameterDefinition(
            name="host",
            description="The host of the REST API.",
            default="127.0.0.1",
            required=True,
        ),
        ConfigParameterDefinition(
            name="port",
            description="The port of the REST API.",
            default=8000,
            required=True,
        ),
        ConfigParameterDefinition(
            name="protocol",
            description="The protocol of the REST API, either 'http' or 'https'.",
            default="http",
            required=True,
        ),
    ],
}


class NodeClientCapabilities(BaseModel):
    """Capabilities of a MADSci Node Client."""

    get_info: bool = Field(
        default=False,
        title="Module Info",
        description="Whether the node supports querying its info.",
    )
    get_state: bool = Field(
        default=False,
        title="Module State",
        description="Whether the node supports querying its state.",
    )
    get_status: bool = Field(
        default=False,
        title="Module Status",
        description="Whether the node supports querying its status.",
    )
    send_action: bool = Field(
        default=False,
        title="Module Send Action",
        description="Whether the node supports sending actions.",
    )
    get_action_result: bool = Field(
        default=False,
        title="Module Get Action",
        description="Whether the node supports querying the status of an action.",
    )
    get_action_history: bool = Field(
        default=False,
        title="Module Get Actions",
        description="Whether the node supports querying the history of actions.",
    )
    action_files: bool = Field(
        default=False,
        title="Module Action Files",
        description="Whether the node supports sending action files.",
    )
    send_admin_commands: bool = Field(
        default=False,
        title="Module Send Admin Commands",
        description="Whether the node supports sending admin commands.",
    )
    set_config: bool = Field(
        default=False,
        title="Module Set Config",
        description="Whether the node supports setting configuration.",
    )
    get_resources: bool = Field(
        default=False,
        title="Module Get Resources",
        description="Whether the node supports querying its resources.",
    )
    get_log: bool = Field(
        default=False,
        title="Module Get Log",
        description="Whether the node supports querying its log.",
    )


class NodeCapabilities(NodeClientCapabilities):
    """Capabilities of a MADSci Node."""

    events: bool = Field(
        default=False,
        title="Module Events",
        description="Whether the module supports raising MADSci events.",
    )
    resources: bool = Field(
        default=False,
        title="Module Resources",
        description="Whether the module supports MADSci-compatible resource management.",
    )
    admin_commands: set[AdminCommands] = Field(
        default=set(),
        title="Module Admin Commands",
        description="Which admin commands the module supports, if any.",
    )


def get_module_from_node_definition(
    node_definition: "NodeDefinition",
) -> Optional[NodeModuleDefinition]:
    """Get the module definition from a node definition.

    Args:
        node_definition: The node definition to get the module definition from

    Returns:
        The module definition, or None if not found

    Raises:
        ValueError: If the module definition path cannot be resolved
    """
    if node_definition.module_definition is None:
        return None

    # * If it's already a ModuleDefinition instance, return it
    if isinstance(node_definition.module_definition, NodeModuleDefinition):
        return node_definition.module_definition

    # * Otherwise treat it as a path
    module_path = Path(str(node_definition.module_definition))

    # * If path is relative, try to resolve it
    if not module_path.is_absolute():
        # * First try relative to node definition path if set
        if node_definition._definition_path:
            resolved_path = Path(node_definition._definition_path).parent / module_path
            if resolved_path.exists():
                return NodeModuleDefinition.from_yaml(resolved_path)

        # * Otherwise try relative to current working directory
        cwd_path = Path.cwd() / module_path
        if cwd_path.exists():
            return NodeModuleDefinition.from_yaml(cwd_path)

        raise ValueError(
            f"Could not resolve module definition path '{module_path}'. "
            f"Tried:\n"
            f"  - {resolved_path if node_definition._definition_path else 'No node definition path set'}\n"
            f"  - {cwd_path}",
        )

    # * For absolute paths, just try to load directly
    if module_path.exists():
        return NodeModuleDefinition.from_yaml(module_path)

    raise ValueError(f"Module definition file not found at '{module_path}'")


class NodeDefinition(BaseModel):
    """Definition of a MADSci Node, a unique instance of a MADSci Module."""

    node_name: str = Field(title="Node Name", description="The name of the node.")
    node_id: str = Field(
        title="Node ID",
        description="The ID of the node.",
        default_factory=new_ulid_str,
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
    module_definition: Optional[Union[NodeModuleDefinition, PathLike]] = Field(
        title="Module",
        description="Definition of the module that the node is an instance of.",
        default=None,
    )  # TODO: Add support for pointing to URL
    config: Union[
        list[Union[ConfigParameterDefinition, ConfigNamespaceDefinition]],
        dict[str, Union[ConfigParameterDefinition, ConfigNamespaceDefinition]],
    ] = Field(
        title="Node Configuration",
        description="The configuration for the node.",
        default_factory=list,
    )
    commands: dict[str, str] = Field(
        default_factory=dict,
        title="Commands",
        description="Commands for operating the node.",
    )

    is_ulid = field_validator("node_id")(ulid_validator)

    @field_validator("config", mode="after")
    @classmethod
    def validate_config(
        cls,
        v: Union[list[ConfigParameterDefinition], dict[str, ConfigParameterDefinition]],
    ) -> Union[list[ConfigParameterDefinition], dict[str, ConfigParameterDefinition]]:
        """Validate the node configuration, promoting a list of ConfigParameters to a dictionary for easier access."""
        if isinstance(v, dict):
            return v
        return {
            param.name if hasattr(param, "name") else param.namespace: param
            for param in v
        }


class Node(BaseModel, arbitrary_types_allowed=True):
    """A runtime representation of a MADSci Node used in a Workcell."""

    node_url: AnyUrl = Field(
        title="Node URL",
        description="The URL used to communicate with the module.",
    )
    status: Optional["NodeStatus"] = Field(
        default=None,
        title="Module Status",
        description="The status of the module. Set to None if the module does not support status reporting or the status is unknown (e.g. if it hasn't reported/responded to status requests).",
    )
    info: Optional["NodeInfo"] = Field(
        default=None,
        title="Node Info",
        description="Information about the node, provided by the node itself.",
    )


class NodeInfo(NodeDefinition, NodeModuleDefinition):
    """Information about a MADSci Node."""

    actions: dict[str, "ActionDefinition"] = Field(
        title="Module Actions",
        description="The actions that the module supports.",
        default_factory=dict,
    )
    config_values: dict[str, Any] = Field(
        default_factory=dict,
        title="Node Configuration",
        description="The configuration of the node.",
    )

    @classmethod
    def from_node_and_module(
        cls,
        node: NodeDefinition,
        module: Optional[NodeModuleDefinition] = None,
        config_values: Optional[dict[str, Any]] = None,
    ) -> "NodeInfo":
        """Create a NodeInfo from a NodeDefinition and a ModuleDefinition."""
        if module is None:
            module = get_module_from_node_definition(node)
        if config_values is None:
            config_values = {}
        # * Merge the node and module configs and commands, with the node config taking precedence
        config = {**module.config, **node.config}
        commands = {**module.commands, **node.commands}
        return cls(
            **node.model_dump(exclude={"config", "commands"}),
            **module.model_dump(exclude={"config", "commands"}),
            config=config,
            commands=commands,
            config_values=config_values,
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


class NodeSetConfigResponse(BaseModel):
    """Response from a Node Set Config Request"""

    success: bool
