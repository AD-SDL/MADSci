"""Types used primarily by MADSci Managers."""

from enum import Enum
from typing import Optional

from madsci.common.types.base_types import MadsciBaseModel
from madsci.common.utils import new_ulid_str
from pydantic import ConfigDict, Field


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
    manager_id: str = Field(
        default_factory=new_ulid_str,
        title="Manager ID",
        description="The unique identifier for this manager instance.",
    )
    manager_type: "ManagerType" = Field(
        title="Manager Type",
        description="The type of the manager, used by other components or managers to find matching managers.",
    )
