"""Types for MADSci Workcell configuration."""

from pathlib import Path
from typing import Annotated, Any, ClassVar, Literal, Optional, Union

from madsci.common.types.base_types import (
    BaseModel,
    Error,
    LoadConfig,
    ModelLink,
    PathLike,
    new_ulid_str,
)
from madsci.common.types.event_types import EventClientConfig
from madsci.common.types.lab_types import ManagerType
from madsci.common.types.location_types import Location, LocationDefinition
from madsci.common.types.node_types import Node, NodeDefinition
from madsci.common.types.workflow_types import Workflow
from madsci.common.validators import ulid_validator
from pydantic import computed_field
from pydantic.functional_validators import field_validator
from pydantic.networks import AnyUrl
from sqlmodel.main import Field


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

    workcell_name: str = Field(
        title="Workcell Name", description="The name of the workcell."
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
    locations: list[LocationDefinition] = Field(
        default_factory=list,
        title="Workcell Locations",
        description="The Locations used in the workcell.",
    )

    @computed_field
    @property
    def workcell_directory(self) -> Path:
        """The directory for the workcell."""
        return Path(self.config.workcells_directory) / self.workcell_name

    is_ulid = field_validator("workcell_id")(ulid_validator)


class WorkcellLink(ModelLink[WorkcellDefinition]):
    """Link to a MADSci Workcell Definition."""

    definition: Optional[WorkcellDefinition] = Field(
        title="Workcell Definition",
        description="The actual definition of the workcell.",
        default=None,
    )


class WorkcellStatus(BaseModel):
    """Represents the status of a MADSci workcell."""

    paused: bool = Field(
        default=False,
        title="Workcell Paused",
        description="Whether the workcell is paused.",
    )
    errored: bool = Field(
        default=False,
        title="Workcell Errored",
        description="Whether the workcell is in an error state.",
    )
    errors: list[Error] = Field(
        default_factory=list,
        title="Workcell Errors",
        description="A list of errors the workcell has encountered.",
    )
    initializing: bool = Field(
        default=False,
        title="Workcell Initializing",
        description="Whether the workcell is initializing.",
    )
    shutdown: bool = Field(
        default=False,
        title="Workcell Shutdown",
        description="Whether the workcell is shutting down.",
    )
    locked: bool = Field(
        default=False,
        title="Workcell Locked",
        description="Whether the workcell is locked.",
    )

    @computed_field
    @property
    def ok(self) -> bool:
        """Whether the workcell is in a good state."""
        return not any(
            [
                self.paused,
                self.errored,
                self.initializing,
                self.shutdown,
                self.locked,
            ]
        )

    @field_validator("errors", mode="before")
    @classmethod
    def ensure_list_of_errors(cls, v: Any) -> Any:
        """Ensure that errors is a list of MADSci Errors"""
        if isinstance(v, str):
            return [Error(message=v)]
        if isinstance(v, Error):
            return [v]
        if isinstance(v, Exception):
            return [Error.from_exception(v)]
        if isinstance(v, list):
            for i, item in enumerate(v):
                if isinstance(item, str):
                    v[i] = Error(message=item)
                elif isinstance(item, Exception):
                    v[i] = Error.from_exception(item)
        return v


class WorkcellState(BaseModel):
    """Represents the live state of a MADSci workcell."""

    status: WorkcellStatus = Field(
        default_factory=WorkcellStatus,
        title="Workcell Status",
        description="The status of the workcell.",
    )
    workflow_queue: list[Workflow] = Field(
        default_factory=list,
        title="Workflow Queue",
        description="The queue of workflows in non-terminal states.",
    )
    workcell_definition: WorkcellDefinition = Field(
        title="Workcell Definition",
        description="The definition of the workcell.",
    )
    nodes: dict[str, Node] = Field(
        default_factory=dict,
        title="Workcell Nodes",
        description="The nodes in the workcell.",
    )
    locations: dict[str, Location] = Field(
        default_factory=dict,
        title="Workcell Locations",
        description="The locations in the workcell.",
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
        default_factory=lambda: Path("~") / ".madsci" / "workcells",
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
    data_server_url: Optional[AnyUrl] = Field(
        default=None,
        title="Data Client URL",
        description="The URL for the data client.",
    )
    resource_server_url: Optional[AnyUrl] = Field(
        default=None,
        title="Resource Server URL",
        description="The URL for the resource server.",
    )
    static_files_path: Optional[str] = Field(
        default=None,
        title="Static Files Path",
        description="Path to the static dashboard files",
    )
    get_action_result_retries: int = Field(
        default=3,
        title="Get Action Result Retries",
        description="Number of times to retry getting an action result",
    )
