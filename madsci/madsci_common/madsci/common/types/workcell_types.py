"""Types for MADSci Workcell configuration."""

from typing import Optional, Union

from pydantic.functional_validators import field_validator
from pydantic.networks import AnyUrl
from sqlmodel.main import Field

from madsci.common.types.base_types import BaseModel, PathLike, new_ulid_str
from madsci.common.types.node_types import NodeDefinition
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
    nodes: dict[str, Union["NodeDefinition", AnyUrl, PathLike]] = Field(
        default_factory=dict,
        title="Workcell Node URLs",
        description="The URL, path, or definition for each node in the workcell.",
    )

    is_ulid = field_validator("workcell_id")(ulid_validator)


class WorkcellConfig(BaseModel):
    """Configuration for a MADSci Workcell."""
    workcell_name: str = Field(
        default="Workcell 1",
        title="Name",
        description="The name of the workcell.",
    )
    host: str = Field(
        default="127.0.0.1",
        title="Host",
        description="The host to run the workcell manager on.",
    )
    port: int = Field(
        default=8013,
        title="Port",
        description="The port to run the workcell manager on.",
    )
    workcell_directory: str = Field(
        default="/.MADsci/Workcell",
        title="Workcell Directory",
        description="Directory to save workflow files"
    )
    redis_host: str = Field(
        default="localhost",
        title="Redis Host",
        description="The hostname for the redis server .",
    )
    redis_port: int = Field(
        default=6379,
        title="Redis Port",
        description="The port for the redis server.",
    )
    redis_password: Union[str, None] = Field(
        default=None,
        title="Redis Password",
        description="The password for the redis server.",
    )
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
    clear_workflows: bool = Field(
        default=False,
        title="Clear Workflows",
        description="Whether the workcell should clear old workflows on restart",
    )
    cold_start_delay: int = Field(
        default=0,
        title="Cold Start Delay",
        description="How long the Workcell engine should sleep on startup",
    )
    scheduler: str = Field(
        default="schedulers.default_scheduler",
        title="scheduler",
        description="Scheduler module in the workcell manager scheduler folder with a Scheduler class that inherits from AbstractScheduler to use"
        
    )