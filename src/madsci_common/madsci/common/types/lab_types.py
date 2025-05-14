"""Types for MADSci Squid Lab configuration."""

from enum import Enum
from pathlib import Path
from typing import Any, ClassVar, Optional, Union

import dotenv
from madsci.common.types.base_types import (
    _T,
    MadsciBaseModel,
    MadsciBaseSettings,
    PathLike,
)
from madsci.common.utils import new_ulid_str
from pydantic import ConfigDict
from pydantic.functional_validators import field_validator
from pydantic.networks import AnyUrl
from sqlmodel.main import Field


class LabSettings(
    MadsciBaseSettings,
    env_file=(".env", "lab.env"),
    toml_file="lab.toml",
    yaml_file="lab.yaml",
    json_file="lab.json",
    env_prefix="LAB_",
):
    """Settings for the MADSci Lab."""

    name: str = Field(
        title="Lab Name",
        description="The name of the lab.",
        default="MADSci Lab",
    )
    description: Optional[str] = Field(
        default=None,
        title="Description",
        description="A description of the lab.",
    )
    lab_id: str = Field(
        title="Lab ID",
        description="The ID of the lab.",
        default=None,
        alias="lab_id",  # * Don't double prefix
    )
    lab_url: Optional[AnyUrl] = Field(
        title="Lab URL",
        description="The URL of the lab manager.",
        default=AnyUrl("http://localhost:8000"),
        alias="lab_url",  # * Don't double prefix
    )
    static_files_path: Optional[PathLike] = Field(
        default=Path("~") / "MADSci" / "src" / "madsci_squid" / "ui" / "dist",
        title="Static Files Path",
        description="Path to the static files for the dashboard. Set to None to disable the dashboard.",
    )
    lab_settings_files: Union[Optional[PathLike], list[PathLike]] = Field(
        title="Lab File",
        description="Path to the lab settings file(s) to use. Overrides the defaults.",
        default=None,
    )

    @field_validator("lab_id", mode="before")
    @classmethod
    def validate_lab_id(cls, v: Optional[str]) -> str:
        """Validate the lab ID, creating and saving if new."""
        if not v:
            v = new_ulid_str()
            env_file = dotenv.find_dotenv("lab.env") or dotenv.find_dotenv(".env")
            if not env_file:
                env_file = Path(".env")
                env_file.touch()
            dotenv.set_key(env_file, "LAB_ID", v)
        return v

    @classmethod
    def load_model(cls: _T, *args: Any, **kwargs: Any) -> _T:
        """Load the lab settings model."""
        instance = super().load_model(*args, **kwargs)
        if instance.lab_settings_files:
            kwargs["definition_files"] = instance.lab_settings_files
        return super().load_model(*args, **kwargs)


class ManagerDefinition(MadsciBaseModel):
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
