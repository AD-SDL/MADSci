"""Types for MADSci Workcell configuration."""

from typing import Optional

from pydantic.functional_validators import field_validator
from sqlmodel.main import Field

from madsci.common.types import BaseModel, new_ulid_str
from madsci.common.types.validators import ulid_validator


class Workcell(BaseModel):
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
