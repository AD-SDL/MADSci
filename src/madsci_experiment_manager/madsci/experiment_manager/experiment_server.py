"""REST API and Server for the Experiment Manager."""

import datetime
from typing import Optional

import uvicorn
from fastapi import FastAPI
from madsci.client.event_client import EventClient
from madsci.common.types.experiment_types import (
    Experiment,
    ExperimentDesign,
    ExperimentManagerDefinition,
)
from madsci.common.types.lab_types import EventManagerDefinition
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database


class ExperimentManagerServer:
    """A REST Server for managing MADSci experiments across a lab."""

    experiment_manager_definition: ExperimentManagerDefinition
    db_client: MongoClient
    db_connection: Database
    experiment_designs: Collection
    experiments: Collection
    app = FastAPI()
    logger = EventClient(name=__name__)


@ExperimentManagerServer.app.get("/")
def root() -> Optional[EventManagerDefinition]:
    """Get the root endpoint for the Experiment Manager's server."""
    return ExperimentManagerServer.experiment_manager_definition


@ExperimentManagerServer.app.post("/experiment_design")
def register_experiment_design(experiment_design: ExperimentDesign) -> ExperimentDesign:
    """Register a new experiment_design."""
    # * Lookup experiment_design by ID
    experiment_design.registered_at = datetime.now()
    ExperimentManagerServer.experiment_designs.insert_one(
        experiment_design.model_dump(mode="json")
    )
    return experiment_design


@ExperimentManagerServer.app.get("/experiment_design/{experiment_design_id}")
def get_experiment_design(experiment_design_id: str) -> Optional[ExperimentDesign]:
    """Get an experiment_design by ID."""
    return ExperimentManagerServer.experiment_designs.find_one(
        {"experiment_design": experiment_design_id}
    )


@ExperimentManagerServer.app.get("/experiment/{experiment_id}")
def get_experiment(experiment_id: str) -> Experiment:
    """Get an experiment by ID."""
    return ExperimentManagerServer.experiments.find_one({"experiment": experiment_id})


@ExperimentManagerServer.app.get("/experiments")
def get_experiments(number: int = 10) -> list[Experiment]:
    """Get the latest experiments."""
    return list(
        ExperimentManagerServer.experiments.find().sort("started_at", -1).limit(number)
    )


@ExperimentManagerServer.app.get("/experiment_designs")
def get_experiment_designs(number: int = 10) -> list[ExperimentDesign]:
    """Get the latest experiment designs."""
    return list(
        ExperimentManagerServer.experiment_designs.find()
        .sort("registered_at", -1)
        .limit(number)
    )


if __name__ == "__main__":
    uvicorn.run(
        ExperimentManagerServer.app,
        host=ExperimentManagerServer.host,
        port=ExperimentManagerServer.port,
    )


@ExperimentManagerServer.app.post("/experiment")
def start_experiment(
    experiment_design_id: str,
    run_name: Optional[str] = None,
    run_description: Optional[str] = None,
) -> Experiment:
    """Start a new experiment."""
    experiment_design = ExperimentManagerServer.experiment_designs.find_one(
        {"experiment_design": experiment_design_id}
    )
    if experiment_design is None:
        raise ValueError(f"Experiment Design {experiment_design_id} not found.")
    experiment = Experiment.from_experiment_design(
        run_name=run_name,
        run_description=run_description,
        experiment_design=experiment_design,
    )
    experiment.started_at = datetime.now()
    ExperimentManagerServer.experiments.insert_one(
        experiment.model_dump(mode="json", exclude={"experiment_design"})
    )
    return experiment


@ExperimentManagerServer.app.post("/experiment/{experiment_id}/end")
def end_experiment(experiment_id: str) -> Experiment:
    """End an experiment by ID."""
    experiment = ExperimentManagerServer.experiments.find_one(
        {"experiment": experiment_id}
    )
    if experiment is None:
        raise ValueError(f"Experiment {experiment_id} not found.")
    experiment.ended_at = datetime.now()
    ExperimentManagerServer.experiments.update_one(
        {"experiment": experiment_id},
        {"$set": experiment.model_dump(mode="json", exclude={"experiment_design"})},
    )
    return experiment
