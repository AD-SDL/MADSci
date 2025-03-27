"""Types for interacting with MADSci experiments and the Experiment Manager."""

from enum import Enum
from typing import Any, ClassVar, Literal, Optional, Union

from bson.objectid import ObjectId
from madsci.common.types.auth_types import OwnershipInfo
from madsci.common.types.base_types import BaseModel, datetime, new_ulid_str
from madsci.common.types.event_types import EventClientConfig
from madsci.common.types.lab_types import ManagerDefinition, ManagerType
from pydantic import Field, field_validator


class ExperimentManagerDefinition(ManagerDefinition):
    """Definition for an Experiment Manager."""

    _definition_file_patterns: ClassVar[list] = [
        "*experiment_manager.yaml",
        "*experiment_manager.yml",
    ]
    _definition_cli_flags: ClassVar[list] = ["--experiment-manager", "--definition"]

    manager_type: Literal[ManagerType.EXPERIMENT_MANAGER] = Field(
        title="Manager Type",
        description="The type of the event manager",
        default=ManagerType.EXPERIMENT_MANAGER,
    )
    host: str = Field(
        title="Server Host",
        description="The host of the experiment manager.",
        default="127.0.0.1",
    )
    port: int = Field(
        title="Server Port",
        description="The port of the experiment manager.",
        default=8002,
    )
    db_url: str = Field(
        title="Database URL",
        description="The URL of the database for the experiment manager.",
        default="mongodb://localhost:27017",
    )
    lab_manager_url: Optional[str] = Field(
        title="Lab Manager URL", description="URL for the lab manager", default=None
    )
    workcell_manager_url: Optional[str] = Field(
        title="Workcell Manager URL",
        description="URL for the workcell manager",
        default=None,
    )
    resource_manager_url: Optional[str] = Field(
        title="Resource Manager URL",
        description="URL for the resource manager",
        default=None,
    )
    event_client_config: Optional[EventClientConfig] = Field(
        title="Event Client Configuration",
        description="The configuration for a MADSci event client.",
        default=None,
    )


class ExperimentDesign(BaseModel):
    """A design for a MADSci experiment."""

    experiment_name: str = Field(
        title="Experiment Name",
        description="The name of the experiment.",
    )
    experiment_description: Optional[str] = Field(
        title="Experiment Description",
        description="A description of the experiment.",
        default=None,
    )
    starting_layout: Optional[dict[str, Any]] = Field(
        title="Starting Layout",
        description="The starting layout of resources required for the experiment.",
        default=None,
    )  # TODO: What does this look like?
    ownership_info: OwnershipInfo = Field(
        title="Ownership Info",
        description="Information about the users, campaigns, etc. that this design is owned by.",
        default_factory=OwnershipInfo,
    )
    event_client_config: Optional["EventClientConfig"] = Field(
        title="Event Client Configuration",
        description="The configuration for a MADSci event client.",
        default=None,
    )

    def new_experiment(
        self,
        run_name: Optional[str] = None,
        run_description: Optional[str] = None,
    ) -> "Experiment":
        """Create a new experiment from this design."""
        return Experiment.from_experiment_design(
            experiment_design=self, run_name=run_name, run_description=run_description
        )


class ExperimentRegistration(BaseModel):
    """Experiment Run Registration request body"""

    experiment_design: ExperimentDesign
    run_name: Optional[str] = None
    run_description: Optional[str] = None


class ExperimentStatus(str, Enum):
    """Current status of an experiment run."""

    IN_PROGRESS = "in_progress"
    """Experiment is currently running."""
    PAUSED = "paused"
    """Experiment is not currently running."""
    COMPLETED = "completed"
    """Experiment run has completed."""
    FAILED = "failed"
    """Experiment has failed."""
    CANCELLED = "cancelled"
    """Experiment has been cancelled."""
    UNKNOWN = "unknown"
    """Experiment status is unknown."""


class Experiment(BaseModel):
    """A MADSci experiment."""

    experiment_id: str = Field(
        title="Experiment ID",
        description="The ID of the experiment.",
        default_factory=new_ulid_str,
        alias="_id",
    )

    @field_validator("experiment_id", mode="before")
    @classmethod
    def object_id_to_str(cls, v: Union[str, ObjectId]) -> str:
        """Cast ObjectID to string."""
        if isinstance(v, ObjectId):
            return str(v)
        return v

    status: ExperimentStatus = Field(
        title="Experiment Status",
        description="The status of the experiment.",
        default=ExperimentStatus.IN_PROGRESS,
    )
    experiment_design: Optional[ExperimentDesign] = Field(
        title="Experiment Design",
        description="The design of the experiment.",
        default=None,
    )
    ownership_info: OwnershipInfo = Field(
        title="Ownership Info",
        description="Information about the ownership of the experiment.",
        default_factory=OwnershipInfo,
    )
    run_name: Optional[str] = Field(
        title="Run Name",
        description="A name for this specific experiment run.",
        default=None,
    )
    run_description: Optional[str] = Field(
        title="Run Description",
        description="A description of the experiment run.",
        default=None,
    )
    started_at: Optional[datetime] = Field(
        title="Started At",
        description="The time the experiment was started.",
        default=None,
    )
    ended_at: Optional[datetime] = Field(
        title="Ended At",
        description="The time the experiment was ended.",
        default=None,
    )

    @classmethod
    def from_experiment_design(
        cls,
        experiment_design: ExperimentDesign,
        run_name: Optional[str] = None,
        run_description: Optional[str] = None,
    ) -> "Experiment":
        """Create an experiment from an experiment design."""
        return cls(
            run_name=run_name,
            run_description=run_description,
            experiment_design=experiment_design,
            ownership_info=experiment_design.ownership_info.model_copy(),
        )


class ExperimentalCampaign(BaseModel):
    """A campaign consisting of one or more related experiments."""

    campaign_id: str = Field(
        title="Campaign ID",
        description="The ID of the campaign.",
        default_factory=new_ulid_str,
    )
    campaign_name: str = Field(
        title="Campaign Name",
        description="The name of the campaign.",
    )
    campaign_description: Optional[str] = Field(
        title="Campaign Description",
        description="A description of the campaign.",
        default=None,
    )
    experiment_ids: Optional[list[str]] = Field(
        title="Experiment IDs",
        description="The IDs of the experiments in the campaign. (Convenience field)",
        default_factory=None,
    )
    ownership_info: OwnershipInfo = Field(
        title="Ownership Info",
        description="Information about the ownership of the campaign.",
        default_factory=OwnershipInfo,
    )
    created_at: datetime = Field(
        title="Registered At",
        description="The time the campaign was registered.",
        default_factory=datetime.now,
    )
    ended_at: Optional[datetime] = Field(
        title="Ended At",
        description="The time the campaign was ended.",
        default=None,
    )
