"""Types for managing MADSci contexts and their configurations."""

from typing import Optional

from madsci.common.types.base_types import MadsciBaseModel, MadsciBaseSettings
from madsci.common.types.lab_types import ManagerType
from madsci.common.types.node_types import NodeType
from pydantic import AnyUrl, Field


class Context(
    MadsciBaseSettings,
    env_file=(".env", "context.env"),
    toml_file="context.toml",
    yaml_file="context.yaml",
    json_file="context.json",
):
    """Base class for MADSci context settings."""

    lab_server_url: Optional[AnyUrl] = Field(
        title="Lab Server URL",
        description="The URL of the lab server.",
        default=AnyUrl("http://localhost:8000"),
    )
    managers: list["ManagerContext"] = Field(
        title="Managers",
        description="List of available_managers.",
        default_factory=list,
    )
    nodes: list["NodeContext"] = Field(
        title="Nodes",
        description="List of available nodes.",
        default_factory=list,
    )
    experiment: Optional["ExperimentContext"] = Field(
        title="Experiment",
        description="The experiment context.",
        default=None,
    )
    owner: Optional["OwnerContext"] = Field(
        title="Owner",
        description="The owner(s) in the current context.",
        default=None,
    )


class ManagerContext(
    MadsciBaseModel,
):
    """Base class for MADSci manager context settings."""

    url: AnyUrl = Field(
        title="Manager Server URL",
        description="The URL of the manager.",
    )
    manager_type: ManagerType = Field(
        title="Manager Type",
        description="The type of the manager.",
    )
    manager_name: Optional[str] = Field(
        title="Manager Name",
        description="The name of the manager.",
        default=None,
    )
    manager_id: Optional[str] = Field(
        title="Manager ID",
        description="The ID of the manager.",
        default=None,
    )


class NodeContext(
    MadsciBaseModel,
):
    """Base class for MADSci node context settings."""

    url: AnyUrl = Field(
        title="Node Server URL",
        description="The URL of the node.",
    )
    node_type: NodeType = Field(
        title="Node Type",
        description="The type of the node.",
    )
    node_name: Optional[str] = Field(
        title="Node Name",
        description="The name of the node.",
        default=None,
    )
    node_id: Optional[str] = Field(
        title="Node ID",
        description="The ID of the node.",
        default=None,
    )
