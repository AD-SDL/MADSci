"""Types for MADSci Squid Lab configuration."""

from pathlib import Path
from typing import Literal, Optional

from madsci.common.types.base_types import PathLike
from madsci.common.types.manager_types import (
    ManagerDefinition,
    ManagerHealth,
    ManagerSettings,
    ManagerType,
)
from madsci.common.utils import new_ulid_str
from pydantic import AliasChoices, Field
from pydantic.networks import AnyUrl


class LabManagerSettings(
    ManagerSettings,
    env_file=(".env", "lab.env"),
    toml_file=("settings.toml", "lab.settings.toml"),
    yaml_file=("settings.yaml", "lab.settings.yaml"),
    json_file=("settings.json", "lab.settings.json"),
    env_prefix="LAB_",
):
    """Settings for the MADSci Lab."""

    server_url: AnyUrl = Field(
        title="Lab URL",
        description="The URL of the lab manager.",
        default=AnyUrl("http://localhost:8000"),
    )
    dashboard_files_path: Optional[PathLike] = Field(
        default=Path("~") / "MADSci" / "ui" / "dist",
        title="Dashboard Static Files Path",
        description="Path to the static files for the dashboard. Set to None to disable the dashboard.",
    )
    manager_definition: PathLike = Field(
        title="Lab Definition File",
        description="Path to the lab definition file to use.",
        default=Path("lab.manager.yaml"),
    )


class LabHealth(ManagerHealth):
    """Health status for Lab Manager including status of other managers in the lab."""

    managers: Optional[dict[str, ManagerHealth]] = Field(
        title="Manager Health Status",
        description="Health status of all managers in the lab.",
        default=None,
    )
    total_managers: Optional[int] = Field(
        title="Total Managers",
        description="Total number of managers configured in the lab.",
        default=None,
    )
    healthy_managers: Optional[int] = Field(
        title="Healthy Managers",
        description="Number of managers that are healthy.",
        default=None,
    )


class LabManagerDefinition(ManagerDefinition):
    """Definition for a MADSci Lab Manager."""

    name: str = Field(
        title="Lab Name",
        description="The name of the lab.",
        default="MADSci Lab Manager",
    )
    manager_id: str = Field(
        title="Lab ID",
        description="The ID of the lab.",
        default_factory=new_ulid_str,
        alias=AliasChoices("lab_id", "manager_id"),
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
