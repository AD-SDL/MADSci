"""MADSci Node Types."""

from os import PathLike
from typing import List, Optional, Tuple, Union

from pydantic import Field
from pydantic.functional_validators import field_validator
from pydantic.networks import AnyUrl

from madsci.common.types.base_types import BaseModel, Error, new_ulid_str
from madsci.common.types.module_types import ConfigParameter, ModuleDefinition
from madsci.common.types.validators import ulid_validator


class NodeDefinition(BaseModel):
    """Definition of a MADSci Node, a unique instance of a MADSci Module."""

    node_name: str = Field(title="Node Name", description="The name of the node.")
    node_id: str = Field(
        title="Node ID",
        description="The ID of the node.",
        default_factory=new_ulid_str,
    )
    description: Optional[str] = Field(
        title="Description",
        description="A description of the node.",
        default=None,
    )
    module: Union[ModuleDefinition, PathLike] = Field(
        title="Module",
        description="The module that the node is an instance of.",
    )
    node_config: List[ConfigParameter] = Field(
        title="Node Configuration",
        description="The configuration for the node.",
        default_factory=list,
    )

    is_ulid = field_validator("node_id")(ulid_validator)


class Node(NodeDefinition, arbitrary_types_allowed=True):
    """A runtime representation of a MADSci Node used in a Workcell."""

    node_url: Optional[AnyUrl] = Field(
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


class NodeInfo(NodeDefinition):
    """Information about a MADSci Node."""

    pass


class NodeStatus(BaseModel):
    """Status of a MADSci Node."""

    ready: bool = Field(
        default=False,
        title="Node Ready",
        description="Whether the node is ready to accept actions.",
    )
    running_actions: set[str] = Field(
        default_factory=set,
        title="Running Actions",
        description="The IDs of the actions that are currently running on the node.",
    )
    completed_actions: set[str] = Field(
        default_factory=set,
        title="Completed Actions",
        description="The IDs of the actions that have completed on the node.",
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
    errors: List[Error] = Field(
        default_factory=list,
        title="Node Errors",
        description="A list of errors that the node has encountered.",
    )
    initializing: bool = Field(
        default=False,
        title="Node Initializing",
        description="Whether the node is currently initializing.",
    )
    waiting_for_config: bool = Field(
        default=False,
        title="Node Waiting for Configuration",
        description="Whether the node is waiting for configuration to be set.",
    )

    @property
    def is_ready(self) -> Tuple[bool, str]:
        """Whether the node is ready to accept actions."""
        if not self.ready:
            return False, "Node is not ready"
        if self.locked:
            return False, "Node is locked"
        if self.errored:
            return False, "Node is in an error state"
        if self.initializing:
            return False, "Node is initializing"
        if self.waiting_for_config:
            return False, "Node is waiting for configuration"
        if self.paused:
            return False, "Node is paused"
        return True, "Node is ready"


class NodeSetConfigResponse(BaseModel):
    """Response from a Node Set Config Request"""

    success: bool
