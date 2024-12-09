"""Types related to MADSci Modules."""

from enum import Enum
from typing import Any, Optional, Union

from pydantic.functional_validators import field_validator
from sqlmodel.main import Field

from madsci.common.types.admin_command_types import AdminCommands
from madsci.common.types.base_types import BaseModel


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
    config: Union[list["ConfigParameter"], dict[str, "ConfigParameter"]] = Field(
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
        v: Union[list["ConfigParameter"], dict[str, "ConfigParameter"]],
    ) -> Union[list["ConfigParameter"], dict[str, "ConfigParameter"]]:
        """Validate the node module configuration, promoting a list of ConfigParameters to a dictionary for easier access."""
        if isinstance(v, dict):
            return v
        return {param.name: param for param in v}


class ConfigParameter(BaseModel, extra="allow"):
    """A parameter for a MADSci Module/Node Configuration."""

    name: str = Field(
        title="Parameter Name",
        description="The name of the parameter.",
    )
    description: Optional[str] = Field(
        title="Parameter Description",
        description="A description of the parameter.",
        default=None,
    )
    default: Optional[Any] = Field(
        title="Parameter Default",
        description="The default value of the parameter.",
        default=None,
    )
    required: bool = Field(
        title="Parameter Required",
        description="Whether the parameter is required.",
        default=False,
    )
    reset_on_change: bool = Field(
        title="Parameter Reset on Change",
        description="Whether the node should restart whenever the parameter changes.",
        default=True,
    )


NODE_MODULE_CONFIG_TEMPLATES: dict[str, list[ConfigParameter]] = {
    "REST Module": [
        ConfigParameter(
            name="host",
            description="The host of the REST API.",
            default="127.0.0.1",
            required=True,
        ),
        ConfigParameter(
            name="port",
            description="The port of the REST API.",
            default=8000,
            required=True,
        ),
        ConfigParameter(
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
