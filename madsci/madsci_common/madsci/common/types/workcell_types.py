"""Types for MADSci Workcell configuration."""

from typing import Optional, Union

from pydantic.functional_validators import field_validator
from pydantic.networks import AnyUrl
from sqlmodel.main import Field

from madsci.common.types.base_types import BaseModel, PathLike, new_ulid_str
from madsci.common.types.node_types import NodeDefinition
from madsci.common.validators import ulid_validator


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
    nodes: dict[str, Union[AnyUrl, "NodeDefinition", PathLike]] = Field(
        default_factory=dict,
        title="Workcell Node URLs",
        description="The URL, path, or definition for each node in the workcell.",
    )

    is_ulid = field_validator("workcell_id")(ulid_validator)


class WorkcellConfig(BaseModel):
    """Configuration for a MADSci Workcell."""

    scheduler_update_interval: float = Field(
        default=0.1,
        title="Scheduler Update Interval",
        description="The interval at which the scheduler runs, in seconds.",
    )
    node_update_interval: float = Field(
        default=1.0,
        title="Node Update Interval",
        description="The interval at which the workcell queries its node's states, in seconds.",
    )
    auto_start: bool = Field(
        default=True,
        title="Auto Start",
        description="Whether the workcell should automatically create a new Workcell Manager and start it when the lab starts, registering it with the Lab Server.",
    )
