"""Types for MADSci Squid Lab configuration."""

from enum import Enum
from pathlib import Path
from typing import ClassVar, Optional

from madsci.common.types.base_types import BaseModel, PathLike, new_ulid_str
from madsci.common.validators import (
    ulid_validator,
)
from pydantic import ConfigDict
from pydantic.functional_validators import field_validator
from pydantic.networks import AnyUrl
from sqlmodel.main import Field


class LabUrls(BaseModel):
    """urls for the lab manager"""

    workcell_manager: Optional[AnyUrl] = Field(
        title="Workcell Manager URL",
        description="The Workcell Manager Url",
        default=None,
    )

    resource_manager: Optional[AnyUrl] = Field(
        title="Resource Manager URL",
        description="The Resource Manager URL for this lab.",
        default=None,
    )


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
    commands: dict[str, str] = Field(
        default_factory=dict,
        title="Commands",
        description="Commands for operating the lab.",
    )
    static_files_path: str = Field(
        default=None,
        title="Static Files Path",
        description="Path to the static files for the lab manager",
    )
    managers: "LabUrls" = Field(
        default_factory=LabUrls,
        title="Manager Model Links",
        description="Links to definitions for Managers used by the lab.",
    )

    @field_validator("commands")
    @classmethod
    def validate_commands(cls, v: dict[str, str]) -> dict[str, str]:
        """Validate the command names."""
        if v:
            for command in v:
                if not str(command).replace("_", "").isalnum():
                    raise ValueError(
                        f"Command '{command}' must consist only of alphanumeric characters or underscores."
                    )
        return v

    is_ulid = field_validator("lab_id")(ulid_validator)

    def resolve_managers(self, path_origin: Optional[PathLike] = None) -> None:
        """Resolve the manager definition links."""
        if path_origin is not None:
            if self._definition_path:
                path_origin = Path(self._definition_path)
            else:
                path_origin = Path("./")
        for manager in self.managers.values():
            manager.resolve(path_origin=path_origin)


class ManagerDefinition(BaseModel):
    """Definition for a Squid Manager."""

    model_config = ConfigDict(extra="allow")
    _definition_file_patterns: ClassVar[list[str]] = ["*.manager.yaml"]

    name: str = Field(
        title="Manager Name",
        description="The name of this manager instance.",
    )
    manager_id: Optional[str] = Field(
        title="Manager ID",
        description="The ID of the manager.",
        default_factory=new_ulid_str,
    )
    description: Optional[str] = Field(
        default=None,
        title="Description",
        description="A description of the manager.",
    )
    manager_type: "ManagerType" = Field(
        title="Manager Type",
        description="The type of the manager, used by other components or managers to find matching managers.",
    )
    url: Optional[AnyUrl] = Field(
        default=None,
        title="Manager URL",
        description="The URL of the manager's API.",
    )


class ManagerType(str, Enum):
    """Types of Squid Managers."""

    WORKCELL_MANAGER = "workcell_manager"
    RESOURCE_MANAGER = "resource_manager"
    EVENT_MANAGER = "event_manager"
    AUTH_MANAGER = "auth_manager"
    NOTIFICATION_MANAGER = "notification_manager"
    DATA_MANAGER = "data_manager"
    TRANSFER_MANAGER = "transfer_manager"
    DASHBOARD_MANAGER = "dashboard_manager"
    EXPERIMENT_MANAGER = "experiment_manager"

    @classmethod
    def _missing_(cls, value: str) -> "ManagerType":
        value = value.lower()
        for member in cls:
            if member.lower() == value:
                return member
        raise ValueError(f"Invalid ManagerTypes: {value}")
