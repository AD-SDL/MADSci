"""Types for interacting with MADSci experiments and the Experiment Manager."""

from enum import Enum
from typing import Literal, Optional, Union

from bson.objectid import ObjectId
from madsci.common.ownership import get_current_ownership_info
from madsci.common.types.auth_types import OwnershipInfo
from madsci.common.types.base_types import (
    MadsciBaseModel,
    MadsciBaseSettings,
    PathLike,
    datetime,
)
from madsci.common.types.condition_types import Conditions
from madsci.common.types.lab_types import ManagerDefinition, ManagerType
from madsci.common.utils import new_ulid_str
from pydantic import AnyUrl, Field, field_validator


class ExperimentManagerSettings(
    MadsciBaseSettings,
    env_file=(".env", "experiments.env"),
    toml_file=("settings.toml", "experiments.settings.toml"),
    yaml_file=("settings.yaml", "experiments.settings.yaml"),
    json_file=("settings.json", "experiments.settings.json"),
    env_prefix="EXPERIMENTS_",
):
    """Settings for the MADSci Experiment Manager."""

    experiment_server_url: AnyUrl = Field(
        title="Experiment Server URL",
        description="The URL of the experiment manager server.",
        default="http://localhost:8002",
        alias="experiment_server_url",  # * Don't double prefix
    )
    experiment_manager_definition: PathLike = Field(
        title="Experiment Manager Definition File",
        description="Path to the experiment manager definition file to use.",
        default="experiment.manager.yaml",
        alias="experiment_manager_definition",  # * Don't double prefix
    )
    db_url: str = Field(
        title="Database URL",
        description="The URL of the database for the experiment manager.",
        default="mongodb://localhost:27017",
    )


class ExperimentManagerDefinition(ManagerDefinition):
    """Definition for an Experiment Manager."""

    name: str = Field(
        title="Manager Name",
        description="The name of this experiment manager instance.",
        default="Experiment Manager",
    )
    experiment_manager_id: str = Field(
        title="Experiment Manager ID",
        description="The ID of the experiment manager.",
        default_factory=new_ulid_str,
    )
    manager_type: Literal[ManagerType.EXPERIMENT_MANAGER] = Field(
        title="Manager Type",
        description="The type of the event manager",
        default=ManagerType.EXPERIMENT_MANAGER,
    )


class ExperimentDesign(MadsciBaseModel):
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
    resource_conditions: list[Conditions] = Field(
        title="Resource Conditions",
        description="The starting layout of resources required for the experiment.",
        default_factory=list,
    )
    ownership_info: OwnershipInfo = Field(
        title="Ownership Info",
        description="Information about the users, campaigns, etc. that this design is owned by.",
        default_factory=get_current_ownership_info,
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


class ExperimentRegistration(MadsciBaseModel):
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


class Experiment(MadsciBaseModel):
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
        return str(v)

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
        default_factory=get_current_ownership_info,
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
            ownership_info=OwnershipInfo(
                **(
                    experiment_design.ownership_info.model_dump(exclude_none=True)
                    if experiment_design.ownership_info
                    else get_current_ownership_info().model_dump(exclude_none=True)
                )
            ),
        )


class ExperimentalCampaign(MadsciBaseModel):
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
        default_factory=get_current_ownership_info,
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
