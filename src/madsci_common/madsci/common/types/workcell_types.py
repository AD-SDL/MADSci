"""Types for MADSci Workcell configuration."""

from pathlib import Path
from typing import Any, Literal, Optional, Union

from madsci.common.types.base_types import (
    Error,
    MadsciBaseModel,
    MadsciBaseSettings,
    PathLike,
)
from madsci.common.types.lab_types import ManagerType
from madsci.common.types.location_types import Location, LocationDefinition
from madsci.common.types.node_types import Node
from madsci.common.types.workflow_types import Workflow
from madsci.common.utils import new_ulid_str
from madsci.common.validators import ulid_validator
from pydantic import Field, computed_field
from pydantic.functional_validators import field_validator
from pydantic.networks import AnyUrl


class WorkcellDefinition(MadsciBaseModel, extra="allow"):
    """Definition of a MADSci Workcell."""

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
    nodes: dict[str, AnyUrl] = Field(
        default_factory=dict,
        title="Workcell Node URLs",
        description="The URL for each node in the workcell.",
    )
    locations: list[LocationDefinition] = Field(
        default_factory=list,
        title="Workcell Locations",
        description="The Locations used in the workcell.",
    )

    @property
    def workcell_directory(self) -> Path:
        """The directory for the workcell."""
        return Path(WorkcellManagerSettings().workcells_directory) / self.workcell_name

    is_ulid = field_validator("workcell_id")(ulid_validator)


class WorkcellStatus(MadsciBaseModel):
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


class WorkcellState(MadsciBaseModel):
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


class WorkcellManagerSettings(
    MadsciBaseSettings,
    env_file=(".env", "workcell.env"),
    toml_file=("settings.toml", "workcell.settings.toml"),
    yaml_file=("settings.yaml", "workcell.settings.yaml"),
    json_file=("settings.json", "workcell.settings.json"),
    env_prefix="WORKCELL_",
):
    """Settings for the MADSci Workcell Manager."""

    workcell_server_url: AnyUrl = Field(
        title="Workcell Server URL",
        description="The URL of the workcell manager server.",
        default=AnyUrl("http://localhost:8005"),
        alias="workcell_server_url",  # * Don't double prefix
    )
    workcell_definition: PathLike = Field(
        title="Workcell Definition File",
        description="Path to the workcell definition file to use.",
        default=Path("workcell.manager.yaml"),
        alias="workcell_definition",  # * Don't double prefix
    )
    workcells_directory: Optional[PathLike] = Field(
        title="Workcells Directory",
        description="Directory used to store workcell-related files in. Defaults to ~/.madsci/workcells. Workcell-related filess will be stored in a sub-folder with the workcell name.",
        default_factory=lambda: Path("~") / ".madsci" / "workcells",
        alias="workcells_directory",  # * Don't double prefix
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
        default=2.0,
        title="Scheduler Update Interval",
        description="The interval at which the scheduler runs, in seconds. Must be >= node_update_interval",
    )
    node_update_interval: float = Field(
        default=1.0,
        title="Node Update Interval",
        description="The interval at which the workcell queries its node's states, in seconds.Must be <= scheduler_update_interval",
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
    mongo_url: Optional[str] = Field(
        default=None,
        title="MongoDB URL",
        description="The URL for the mongo database.",
    )
    get_action_result_retries: int = Field(
        default=3,
        title="Get Action Result Retries",
        description="Number of times to retry getting an action result",
    )
