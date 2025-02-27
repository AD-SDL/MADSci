"""Types for MADSci Workcell configuration."""

from pathlib import Path
from typing import Annotated, ClassVar, Literal, Optional, Union

from pydantic import computed_field, field_serializer
from pydantic.functional_validators import field_validator
from pydantic.networks import AnyUrl
from sqlmodel.main import Field

from madsci.common.serializers import dict_to_list
from madsci.common.types.base_types import (
    BaseModel,
    LoadConfig,
    ModelLink,
    PathLike,
    new_ulid_str,
)
from madsci.common.types.event_types import EventClientConfig
from madsci.common.types.lab_types import ManagerType
from madsci.common.types.node_types import NodeDefinition
from madsci.common.validators import create_dict_promoter, ulid_validator


class WorkcellDefinition(BaseModel, extra="allow"):
    """Configuration for a MADSci Workcell."""

    _definition_file_patterns: ClassVar[list] = [
        "*workcell.yaml",
        "*workcell.yml",
        "*workcell.manager.yml",
        "*workcell.manager.yaml",
    ]
    _definition_cli_flag: ClassVar[list] = [
        "--workcell",
        "--workcell-definition",
        "--definition",
        "--workcell-definition-file",
        "-f",
    ]

    name: str = Field(
        title="Workcell Name",
        description="The name of the workcell.",
    )
    manager_type: Literal[ManagerType.WORKCELL_MANAGER] = Field(
        title="Manager Type",
        description="The type of manager",
        default=ManagerType.WORKCELL_MANAGER,
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
    config: Annotated[
        "WorkcellConfig",
        Field(
            title="Workcell Configuration",
            description="The configuration for the workcell.",
            default_factory=lambda: WorkcellConfig(),
        ),
        LoadConfig(use_fields_as_cli_args=True),
    ]
    nodes: dict[str, Union["NodeDefinition", AnyUrl, PathLike]] = Field(
        default_factory=dict,
        title="Workcell Node URLs",
        description="The URL, path, or definition for each node in the workcell.",
    )

    @computed_field
    @property
    def workcell_directory(self) -> Path:
        """The directory for the workcell."""
        return Path(self.config.workcells_directory) / self.name

    is_ulid = field_validator("workcell_id")(ulid_validator)
    validate_nodes_to_dict = field_validator("nodes", mode="before")(
        create_dict_promoter("node_name")
    )
    serialize_nodes_to_list = field_serializer("nodes")(dict_to_list)


class WorkcellLink(ModelLink):
    """Link to a MADSci Workcell Definition."""

    definition: Optional[WorkcellDefinition] = Field(
        title="Workcell Definition",
        description="The actual definition of the workcell.",
        default=None,
    )


class WorkcellConfig(BaseModel):
    """Configuration for a MADSci Workcell."""

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
    workcells_directory: Optional[PathLike] = Field(
        title="Workcells Directory",
        description="Directory used to store workcell-related files in. Defaults to ~/.madsci/workcells. Workcell-related filess will be stored in a sub-folder with the workcell name.",
        default_factory=lambda: Path.home() / ".madsci" / "workcells",
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
    event_client_config: Optional[EventClientConfig] = Field(
        default=None,
        title="Event Client Configuration",
        description="The configuration for a MADSci event client.",
    )
    scheduler_update_interval: float = Field(
        default=2.0,
        title="Scheduler Update Interval",
        description="The interval at which the scheduler runs, in seconds. Must be >= node_update_interval",
    )
    node_update_interval: float = Field(
        default=1.0,
        title="Node Update Interval",
        description="The interval at which the workcell queries its node's states, in seconds.Must be <= scheduler_update_interval",
    )
    heartbeat_interval: float = Field(
        default=2.0,
        title="Heartbeat Interval",
        description="The interval at which the workcell queries its node's states, in seconds.Must be <= scheduler_update_interval",
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
        default="madsci.workcell_manager.schedulers.default_scheduler",
        title="scheduler",
        description="Scheduler module that contains a Scheduler class that inherits from AbstractScheduler to use",
    )
