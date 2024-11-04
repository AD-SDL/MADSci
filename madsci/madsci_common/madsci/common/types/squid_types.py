"""Types for MADSci Squid configuration."""

from typing import Any, Dict, List, Optional, Union

from pydantic.functional_validators import field_validator
from pydantic.networks import AnyUrl
from sqlmodel.main import Field

from madsci.common.types import BaseModel, PathLike, new_ulid_str
from madsci.common.types.validators import (
    alphanumeric_with_underscores_validator,
    ulid_validator,
)
from madsci.common.types.workcell_types import WorkcellDefinition


class LabDefinition(BaseModel):
    """Definition for a MADSci Lab."""

    name: str = Field(title="Name", description="The name of the lab.")
    lab_id: str = Field(
        title="Lab ID",
        description="The ID of the lab.",
        default_factory=new_ulid_str,
    )
    description: Optional[str] = Field(
        default=None,
        title="Description",
        description="A description of the lab.",
    )
    lab_server: "LabServerConfig" = Field(
        title="Lab Server Configuration",
        default_factory=lambda: LabServerConfig(),
        description="The configuration for the lab server.",
    )
    workcells: List[Union["WorkcellDefinition", PathLike]] = Field(
        default_factory=list,
        title="Workcells",
        description="The workcells in the lab.",
    )
    commands: Dict[str, str] = Field(
        default_factory=dict,
        title="Commands",
        description="Commands for operating the lab.",
    )
    squid_plugins: Dict[str, Union["SquidPluginDefinition", PathLike, AnyUrl]] = Field(
        default_factory=dict,
        title="Squid Plugin Definitions",
        description="Squid Plugin definitions used by the lab. Either a path to a plugin definition file, a URL to a plugin, or a plugin definition object. If the plugin definition is a URL, the server will attempt to fetch the plugin definition from the URL.",
    )

    @field_validator("commands")
    def validate_commands(cls, v: Dict[str, str]) -> Dict[str, str]:
        """Validate the commands."""
        if v:
            for command in v:
                if not str.isalnum(command):
                    raise ValueError(f"Command '{command}' must be alphanumeric")
        return v

    is_ulid = field_validator("lab_id")(ulid_validator)


class LabServerConfig(BaseModel, extra="allow"):
    """Configuration for a MADSci Lab Server."""

    host: str = Field(
        default="localhost",
        title="Server Host",
        description="The hostname or IP address of the Squid Lab Server.",
    )
    port: int = Field(
        default=8000,
        title="Server Port",
        description="The port number of the Squid Lab Server.",
    )


class SquidPluginDefinition(BaseModel):
    """Definition for a Squid Plugin."""

    name: str = Field(
        title="Plugin Name", description="The name of this plugin instance."
    )
    plugin_id: Optional[str] = Field(
        title="Plugin ID", description="The ID of the plugin.", default=None
    )
    description: Optional[str] = Field(
        default=None,
        title="Description",
        description="A description of the plugin.",
    )
    plugin_type: str = Field(
        title="Plugin Type",
        description="The type of the plugin, used by other components or plugins to find matching plugins.",
    )
    plugin_config: Optional[Dict[str, Any]] = Field(
        default=None,
        title="Plugin Configuration",
        description="The configuration for the plugin.",
    )
    url: Optional[AnyUrl] = Field(
        default=None,
        title="Plugin URL",
        description="The URL of the plugin server.",
    )

    is_alphanumeric = field_validator("plugin_type")(
        alphanumeric_with_underscores_validator
    )
