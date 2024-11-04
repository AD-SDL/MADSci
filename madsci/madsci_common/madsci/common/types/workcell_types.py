"""Types for MADSci Workcell configuration."""

from typing import Dict, Optional

from pydantic.functional_validators import field_validator
from pydantic.networks import AnyUrl
from sqlmodel.main import Field

from madsci.common.types import BaseModel, new_ulid_str
from madsci.common.types.validators import ulid_validator


class WorkcellDefinition(BaseModel, extra="allow"):
    """Configuration for a MADSci Workcell."""

    name: str = Field(
        title="Workcell Name",
        description="The name of the workcell.",
    )
    workcell_id: str = Field(
        title="Workcell ID",
        description="The ID of the workcell.",
        default_factory=new_ulid_str,
    )
    description: Optional[str] = Field(
        default=None,
        title="Workcell Description",
        description="A description of the workcell.",
    )
    config: "WorkcellConfig" = Field(
        title="Workcell Configuration",
        description="The configuration for the workcell.",
        default_factory=lambda: WorkcellConfig(),
    )
    modules: Dict[str, AnyUrl] = Field(
        default_factory=dict,
        title="Workcell Module URL",
        description="The URL for each module in the workcell.",
    )
    # resources: Dict[str, Union["ResourceDefinition"]] = Field(
    #     default_factory=dict,
    #     title="Workcell Resource Definitions",
    #     description="Any definitions for default resources used by the workcell. If they are defined here, they will be created when the workcell is started, if they don't already exist.",
    # )

    is_ulid = field_validator("workcell_id")(ulid_validator)


class WorkcellConfig(BaseModel):
    """Configuration for a MADSci Workcell."""

    scheduler_update_interval: float = Field(
        default=0.1,
        title="Scheduler Update Interval",
        description="The interval at which the scheduler runs, in seconds.",
    )
    module_update_interval: float = Field(
        default=1.0,
        title="Module Update Interval",
        description="The interval at which the workcell queries its modules' states, in seconds.",
    )
