"""Types for MADSci Squid configuration."""

from typing import Dict, List, Optional, Union

from pydantic.functional_validators import field_validator
from sqlmodel.main import Field

from madsci.common.types import BaseModel, PathLike, new_ulid_str
from madsci.common.types.validators import ulid_validator
from madsci.common.types.workcell_types import WorkcellConfig


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
    workcells: List[Union["WorkcellConfig", PathLike]] = Field(
        default_factory=list,
        title="Workcells",
        description="The workcells in the lab.",
    )
    commands: Dict[str, str] = Field(
        default_factory=dict,
        title="Commands",
        description="Commands for operating the lab.",
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


class LabServerConfig(BaseModel):
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
