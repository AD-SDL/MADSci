"""Types used primarily by MADSci Managers."""

from enum import Enum
from pathlib import Path
from typing import Optional

from madsci.common.types.base_types import MadsciBaseModel, MadsciBaseSettings, PathLike
from madsci.common.utils import new_ulid_str
from pydantic import AnyUrl, ConfigDict, Field


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


class ManagerSettings(MadsciBaseSettings):
    """Base settings class for MADSci Manager services.

    This class provides common configuration fields that all managers need,
    such as server URL and manager definition file path.

    Manager-specific settings classes should inherit from this class and:
    1. Add their specific configuration parameters
    2. Set appropriate env_prefix, env_file, toml_file, etc. parameters
    3. Override default values as needed (especially server_url default port)
    """

    server_url: AnyUrl = Field(
        title="Server URL",
        description="The URL where this manager's server runs.",
        default="http://localhost:8000",
    )
    manager_definition: PathLike = Field(
        title="Manager Definition File",
        description="Path to the manager definition file to use.",
        default=Path("manager.yaml"),
    )


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
    manager_id: str = Field(
        default_factory=new_ulid_str,
        title="Manager ID",
        description="The unique identifier for this manager instance.",
    )
    manager_type: "ManagerType" = Field(
        title="Manager Type",
        description="The type of the manager, used by other components or managers to find matching managers.",
    )
