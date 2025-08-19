"""Types for MADSci Transfer Manager configuration."""

from pathlib import Path
from typing import Literal, Optional

from madsci.common.types.base_types import (
    MadsciBaseModel,
    MadsciBaseSettings,
    PathLike,
)
from madsci.common.types.lab_types import ManagerType
from madsci.common.utils import new_ulid_str
from madsci.common.validators import ulid_validator
from pydantic import Field
from pydantic.functional_validators import field_validator
from pydantic.networks import AnyUrl


class TransferManagerDefinition(MadsciBaseModel, extra="allow"):
    """Definition of a MADSci Transfer Manager."""

    transfer_manager_name: str = Field(
        title="Transfer Manager Name", 
        description="The name of the transfer manager."
    )
    manager_type: Literal[ManagerType.TRANSFER_MANAGER] = Field(
        title="Manager Type",
        description="The type of manager",
        default="transfer_manager",  # Add this to ManagerType enum
    )
    transfer_manager_id: str = Field(
        title="Transfer Manager ID",
        description="The ID of the transfer manager.",
        default_factory=new_ulid_str,
    )
    description: Optional[str] = Field(
        default=None,
        title="Transfer Manager Description",
        description="A description of the transfer manager.",
    )
    robot_definitions_path: PathLike = Field(
        title="Robot Definitions File",
        description="Path to the robot definitions YAML file.",
        default=Path("robot_definitions.yaml"),
    )
    location_constraints_path: PathLike = Field(
        title="Location Constraints File", 
        description="Path to the location constraints YAML file.",
        default=Path("location_constraints.yaml"),
    )

    @property
    def transfer_manager_directory(self) -> Path:
        """The directory for the transfer manager."""
        return Path(TransferManagerSettings().transfer_managers_directory) / self.transfer_manager_name

    is_ulid = field_validator("transfer_manager_id")(ulid_validator)


class TransferManagerSettings(
    MadsciBaseSettings,
    env_file=(".env", "transfer_manager.env"),
    toml_file=("settings.toml", "transfer_manager.settings.toml"),
    yaml_file=("settings.yaml", "transfer_manager.settings.yaml"),
    json_file=("settings.json", "transfer_manager.settings.json"),
    env_prefix="TRANSFER_MANAGER_",
):
    """Settings for the MADSci Transfer Manager."""

    transfer_manager_server_url: AnyUrl = Field(
        title="Transfer Manager Server URL",
        description="The URL of the transfer manager server.",
        default=AnyUrl("http://localhost:8006"),
        alias="transfer_manager_server_url",  # Don't double prefix
    )
    transfer_manager_definition: PathLike = Field(
        title="Transfer Manager Definition File",
        description="Path to the transfer manager definition file to use.",
        default=Path("transfer.manager.yaml"),
        alias="transfer_manager_definition",  # Don't double prefix
    )
    transfer_managers_directory: Optional[PathLike] = Field(
        title="Transfer Managers Directory",
        description="Directory used to store transfer manager-related files. Defaults to ~/.madsci/transfer_managers.",
        default_factory=lambda: Path("~") / ".madsci" / "transfer_managers",
        alias="transfer_managers_directory",  # Don't double prefix
    )