"""Types for MADSci Squid Lab configuration."""

from enum import Enum
from pathlib import Path
from typing import Literal, Optional

from madsci.common.types.base_types import (
    MadsciBaseModel,
    MadsciBaseSettings,
    PathLike,
)
from madsci.common.utils import new_ulid_str
from pydantic import ConfigDict, Field
from pydantic.networks import AnyUrl


class LabManagerSettings(
    MadsciBaseSettings,
    env_file=(".env", "lab.env"),
    toml_file=("settings.toml", "lab.settings.toml"),
    yaml_file=("settings.yaml", "lab.settings.yaml"),
    json_file=("settings.json", "lab.settings.json"),
    env_prefix="LAB_",
):
    """Settings for the MADSci Lab."""

    lab_server_url: AnyUrl = Field(
        title="Lab URL",
        description="The URL of the lab manager.",
        default=AnyUrl("http://localhost:8000"),
        alias="lab_server_url",  # * Don't double prefix
    )
    dashboard_files_path: Optional[PathLike] = Field(
        default=Path("~") / "MADSci" / "ui" / "dist",
        title="Dashboard Static Files Path",
        description="Path to the static files for the dashboard. Set to None to disable the dashboard.",
    )
    lab_definition: PathLike = Field(
        title="Lab Definition File",
        description="Path to the lab definition file to use.",
        default=Path("lab.manager.yaml"),
        alias="lab_definition",  # * Don't double prefix
    )


class ManagerType(str, Enum):
    """Types of Squid Managers."""

    WORKCELL_MANAGER = "workcell_manager"
    RESOURCE_MANAGER = "resource_manager"
    EVENT_MANAGER = "event_manager"
    AUTH_MANAGER = "auth_manager"
    DATA_MANAGER = "data_manager"
    TRANSFER_MANAGER = "transfer_manager"
    EXPERIMENT_MANAGER = "experiment_manager"
    LAB_MANAGER = "lab_manager"

    @classmethod
    def _missing_(cls, value: str) -> "ManagerType":
        value = value.lower()
        for member in cls:
            if member.lower() == value:
                return member
        raise ValueError(f"Invalid ManagerTypes: {value}")


class ManagerDefinition(MadsciBaseModel):
    """Definition for a MADSci Manager."""

    model_config = ConfigDict(extra="allow")

    name: str = Field(
        title="Manager Name",
        description="The name of this manager instance.",
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


class LabDefinition(ManagerDefinition):
    """Definition for a MADSci Lab."""

    name: str = Field(
        title="Lab Name",
        description="The name of the lab.",
        default="MADSci Lab Manager",
    )
    lab_id: str = Field(
        title="Lab ID",
        description="The ID of the lab.",
        default_factory=new_ulid_str,
    )
    manager_type: Literal[ManagerType.LAB_MANAGER] = Field(
        title="Manager Type",
        description="The type of the manager, used by other components or managers to find matching managers.",
        default=ManagerType.LAB_MANAGER,
    )
    description: Optional[str] = Field(
        default=None,
        title="Description",
        description="A description of the lab.",
    )
