"""REST API and Server for the Experiment Manager."""

import datetime
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from madsci.client.event_client import EventClient, EventType
from madsci.common.ownership import global_ownership_info
from madsci.common.types.event_types import Event
from madsci.common.types.experiment_types import (
    Experiment,
    ExperimentManagerDefinition,
    ExperimentManagerSettings,
    ExperimentRegistration,
    ExperimentStatus,
)
from pymongo import MongoClient
from pymongo.database import Database


def create_experiment_server(  # noqa: C901, PLR0915
    experiment_manager_definition: Optional[ExperimentManagerDefinition] = None,
    experiment_manager_settings: Optional[ExperimentManagerSettings] = None,
    db_connection: Optional[Database] = None,
) -> FastAPI:
    """Creates an Experiment Manager's REST server."""
    logger = EventClient()
    experiment_manager_settings = (
        experiment_manager_settings or ExperimentManagerSettings()
    )
    logger.log_info(experiment_manager_settings)
    if not experiment_manager_definition:
        def_path = Path(
            experiment_manager_settings.experiment_manager_definition
        ).expanduser()
        if def_path.exists():
            experiment_manager_definition = ExperimentManagerDefinition.from_yaml(
                def_path,
            )
        else:
            experiment_manager_definition = ExperimentManagerDefinition()
        logger.log_info(f"Writing to experiment manager definition file: {def_path}")
        experiment_manager_definition.to_yaml(def_path)
    logger = EventClient(
        name=f"experiment_manager.{experiment_manager_definition.name}",
    )
    # Set global ownership info directly
    global_ownership_info.manager_id = (
        experiment_manager_definition.experiment_manager_id
    )
    logger.log_info(experiment_manager_definition)

    # * DB Config
    if db_connection is None:
        db_client = MongoClient(experiment_manager_settings.db_url)
        db_connection = db_client["experiment_manager"]
    experiments = db_connection["experiments"]

    app = FastAPI()

    @app.get("/")
    @app.get("/info")
    @app.get("/definition")
    async def definition() -> Optional[ExperimentManagerDefinition]:
        """Get the definition for the Experiment Manager."""
        return experiment_manager_definition

    @app.get("/experiment/{experiment_id}")
    async def get_experiment(experiment_id: str) -> Experiment:
        """Get an experiment by ID."""
        experiment = experiments.find_one({"_id": experiment_id})
        if not experiment:
            raise HTTPException(status_code=404, detail="Experiment not found")
        return Experiment.model_validate(experiment)

    @app.get("/experiments")
    async def get_experiments(number: int = 10) -> list[Experiment]:
        """Get the latest experiments."""
        experiments_list = (
            experiments.find().sort("started_at", -1).limit(number).to_list()
        )
        return [
            Experiment.model_validate(experiment) for experiment in experiments_list
        ]

    @app.post("/experiment")
    async def start_experiment(
        experiment_request: ExperimentRegistration,
    ) -> Experiment:
        """Start a new experiment."""
        experiment = Experiment.from_experiment_design(
            run_name=experiment_request.run_name,
            run_description=experiment_request.run_description,
            experiment_design=experiment_request.experiment_design,
        )
        experiment.started_at = datetime.datetime.now()

        experiments.insert_one(experiment.to_mongo())
        logger.log(
            event=Event(
                event_type=EventType.EXPERIMENT_START,
                event_data={"experiment": experiment},
            )
        )
        return experiment

    @app.post("/experiment/{experiment_id}/end")
    async def end_experiment(experiment_id: str) -> Experiment:
        """End an experiment by ID."""
        experiment = experiments.find_one({"_id": experiment_id})
        if not experiment:
            raise HTTPException(status_code=404, detail="Experiment not found")
        experiment = Experiment.model_validate(experiment)
        experiment.ended_at = datetime.datetime.now()
        experiment.status = ExperimentStatus.COMPLETED
        experiments.update_one(
            {"_id": experiment_id},
            {"$set": experiment.to_mongo()},
        )
        logger.log(
            event=Event(
                event_type=EventType.EXPERIMENT_COMPLETE,
                event_data={"experiment": experiment},
            )
        )
        return experiment

    @app.post("/experiment/{experiment_id}/continue")
    async def continue_experiment(experiment_id: str) -> Experiment:
        """Continue an experiment by ID."""
        experiment = experiments.find_one({"_id": experiment_id})
        if not experiment:
            raise HTTPException(status_code=404, detail="Experiment not found")
        experiment = Experiment.model_validate(experiment)
        experiment.status = ExperimentStatus.IN_PROGRESS
        experiments.update_one(
            {"_id": experiment_id},
            {"$set": experiment.to_mongo()},
        )
        logger.log(
            event=Event(
                event_type=EventType.EXPERIMENT_CONTINUED,
                event_data={"experiment": experiment},
            )
        )
        return experiment

    @app.post("/experiment/{experiment_id}/pause")
    async def pause_experiment(experiment_id: str) -> Experiment:
        """Pause an experiment by ID."""
        experiment = experiments.find_one({"_id": experiment_id})
        if not experiment:
            raise HTTPException(status_code=404, detail="Experiment not found")
        experiment = Experiment.model_validate(experiment)
        experiment.status = ExperimentStatus.PAUSED
        experiments.update_one(
            {"_id": experiment_id},
            {"$set": experiment.to_mongo()},
        )
        logger.log(
            event=Event(
                event_type=EventType.EXPERIMENT_PAUSE,
                event_data={"experiment": experiment},
            )
        )
        return experiment

    @app.post("/experiment/{experiment_id}/cancel")
    async def cancel_experiment(experiment_id: str) -> Experiment:
        """Cancel an experiment by ID."""
        experiment = experiments.find_one({"_id": experiment_id})
        if not experiment:
            raise HTTPException(status_code=404, detail="Experiment not found")
        experiment = Experiment.model_validate(experiment)
        experiment.status = ExperimentStatus.CANCELLED
        experiments.update_one(
            {"_id": experiment_id},
            {"$set": experiment.to_mongo()},
        )
        logger.log(
            event=Event(
                event_type=EventType.EXPERIMENT_CANCELLED,
                event_data={"experiment": experiment},
            )
        )
        return experiment

    @app.post("/experiment/{experiment_id}/fail")
    async def fail_experiment(experiment_id: str) -> Experiment:
        """Fail an experiment by ID."""
        experiment = experiments.find_one({"_id": experiment_id})
        if not experiment:
            raise HTTPException(status_code=404, detail="Experiment not found")
        experiment = Experiment.model_validate(experiment)
        experiment.status = ExperimentStatus.FAILED
        experiments.update_one(
            {"_id": experiment_id},
            {"$set": experiment.to_mongo()},
        )
        logger.log(
            event=Event(
                event_type=EventType.EXPERIMENT_FAILED,
                event_data={"experiment": experiment},
            )
        )
        return experiment

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app


if __name__ == "__main__":
    experiment_manager_settings = ExperimentManagerSettings()
    app = create_experiment_server(
        experiment_manager_settings=experiment_manager_settings,
    )
    uvicorn.run(
        app,
        host=experiment_manager_settings.experiment_server_url.host,
        port=experiment_manager_settings.experiment_server_url.port,
    )
