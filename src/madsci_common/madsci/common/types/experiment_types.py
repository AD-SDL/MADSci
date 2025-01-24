"""Types for interacting with MADSci experiments and the Experiment Manager."""

from typing import Literal, Optional

from madsci.common.types.base_types import BaseModel, datetime, new_ulid_str
from madsci.common.types.lab_types import ManagerDefinition, ManagerType
from pydantic import Field


class ExperimentManagerDefinition(ManagerDefinition):
    """Definition for an Experiment Manager."""

    manager_type: Literal[ManagerType.EXPERIMENT_MANAGER] = Field(
        title="Manager Type",
        description="The type of the event manager",
        default=ManagerType.EVENT_MANAGER,
    )
    manager_config: "ExperimentManagerConfig" = Field(
        default_factory=lambda: ExperimentManagerConfig(),
        title="Manager Configuration",
        description="The configuration for an experiment manager",
    )


class ExperimentManagerConfig(BaseModel):
    """Configuration for an Experiment Manager."""

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


class ExperimentDesign(BaseModel):
    """A design for a MADSci experiment."""

    experiment_design_id: str = Field(
        title="Experiment Design ID",
        description="The ID of the experiment design.",
        default_factory=new_ulid_str,
    )
    experiment_name: str = Field(
        title="Experiment Name",
        description="The name of the experiment.",
    )
    experiment_description: Optional[str] = Field(
        title="Experiment Description",
        description="A description of the experiment.",
        default=None,
    )
    campaign_id: Optional[str] = Field(
        title="Campaign ID",
        description="The ID of the campaign the experiment is part of.",
        default=None,
    )
    registered_at: Optional[datetime] = Field(
        title="Registered At",
        description="The time the experiment design was registered.",
        default=None,
    )


class Experiment(BaseModel):
    """A MADSci experiment."""

    experiment_id: str = Field(
        title="Experiment ID",
        description="The ID of the experiment.",
        default_factory=new_ulid_str,
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
    experiment_design_id: str = Field(
        title="Experiment Design ID", description="The ID of the experiment design."
    )
    experiment_design: Optional[ExperimentDesign] = Field(
        title="Experiment Design",
        description="The design of the experiment.",
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
            experiment_id=new_ulid_str(),
            run_name=run_name,
            run_description=run_description,
            experiment_design_id=experiment_design.experiment_design_id,
            experiment_design=experiment_design,
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
    experiment_ids: list[str] = Field(
        title="Experiment IDs",
        description="The IDs of the experiments in the campaign.",
        default_factory=list,
    )
    experiments: Optional[dict[str, Experiment]] = Field(
        title="Experiments",
        description="The experiments in the campaign.",
        default=None,
    )
    registered_at: datetime = Field(
        title="Registered At",
        description="The time the campaign was registered.",
        default_factory=datetime.now,
    )
    started_at: Optional[datetime] = Field(
        title="Started At",
        description="The time the campaign was started.",
        default=None,
    )
    ended_at: Optional[datetime] = Field(
        title="Ended At",
        description="The time the campaign was ended.",
        default=None,
    )
