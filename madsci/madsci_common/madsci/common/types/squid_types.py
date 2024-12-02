"""Types for MADSci Squid configuration."""

from enum import Enum
from typing import Any, Optional, Union

from pydantic.functional_validators import field_validator
from pydantic.networks import AnyUrl
from sqlmodel.main import Field

from madsci.common.types.base_types import BaseModel, PathLike, new_ulid_str
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
    server_config: "LabServerConfig" = Field(
        title="Lab Server Configuration",
        default_factory=lambda: LabServerConfig(),
        description="The configuration for the lab server.",
    )
    workcells: dict[str, Union["WorkcellDefinition", PathLike]] = Field(
        default_factory=dict,
        title="Workcells",
        description="The workcells in the lab. Keys are workcell names. Values are either paths to workcell definition files, or workcell definition objects.",
    )
    commands: dict[str, str] = Field(
        default_factory=dict,
        title="Commands",
        description="Commands for operating the lab.",
    )
    managers: dict[str, Union["ManagerDefinition", PathLike, AnyUrl]] = Field(
        default_factory=dict,
        title="Squid Manager Definitions",
        description="Squid Manager definitions used by the lab. Either a path to a manager definition file, a URL to a manager, or a manager definition object. If the manager definition is a URL, the server will attempt to fetch the manager definition from the URL.",
    )

    @field_validator("commands")
    @classmethod
    def validate_commands(cls, v: dict[str, str]) -> dict[str, str]:
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
        default="127.0.0.1",
        title="Server Host",
        description="The hostname or IP address of the Squid Lab Server.",
    )
    port: int = Field(
        default=8000,
        title="Server Port",
        description="The port number of the Squid Lab Server.",
    )


class ManagerDefinition(BaseModel):
    """Definition for a Squid Manager."""

    name: str = Field(
        title="Manager Name",
        description="The name of this manager instance.",
    )
    manager_id: Optional[str] = Field(
        title="Manager ID",
        description="The ID of the manager.",
        default=None,
    )
    description: Optional[str] = Field(
        default=None,
        title="Description",
        description="A description of the manager.",
    )
    manager_type: str = Field(
        title="Manager Type",
        description="The type of the manager, used by other components or managers to find matching managers.",
    )
    manager_config: Optional[dict[str, Any]] = Field(
        default=None,
        title="Manager Configuration",
        description="The configuration for the manager.",
    )
    url: Optional[AnyUrl] = Field(
        default=None,
        title="Manager URL",
        description="The URL of the manager server.",
    )

    is_alphanumeric = field_validator("manager_type")(
        alphanumeric_with_underscores_validator,
    )


class ManagerTypes(str, Enum):
    """Types of Squid Managers."""

    WORKCELL_MANAGER = "workcell_manager"
    RESOURCE_MANAGER = "resource_manager"
    EVENT_MANAGER = "event_manager"
    LOG_MANAGER = "log_manager"
    AUTH_MANAGER = "auth_manager"
    NOTIFICATION_MANAGER = "notification_manager"
    DATA_MANAGER = "data_manager"
    TRANSFER_MANAGER = "transfer_manager"
    DASHBOARD_MANAGER = "dashboard_manager"

    @classmethod
    def _missing_(cls, value: str) -> "ManagerTypes":
        value = value.lower()
        for member in cls:
            if member.lower() == value:
                return member
        raise ValueError(f"Invalid ManagerTypes: {value}")
