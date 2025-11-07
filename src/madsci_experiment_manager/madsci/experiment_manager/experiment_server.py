"""Experiment Manager implementation using the new AbstractManagerBase class."""

import datetime
from pathlib import Path
from typing import Any, Optional

from classy_fastapi import get, post
from fastapi import HTTPException
from madsci.client.event_client import EventType
from madsci.common.manager_base import AbstractManagerBase
from madsci.common.mongodb_version_checker import MongoDBVersionChecker
from madsci.common.types.event_types import Event
from madsci.common.types.experiment_types import (
    Experiment,
    ExperimentManagerDefinition,
    ExperimentManagerHealth,
    ExperimentManagerSettings,
    ExperimentRegistration,
    ExperimentStatus,
)
from pymongo import MongoClient
from pymongo.database import Database


class ExperimentManager(
    AbstractManagerBase[ExperimentManagerSettings, ExperimentManagerDefinition]
):
    """Experiment Manager REST Server."""

    SETTINGS_CLASS = ExperimentManagerSettings
    DEFINITION_CLASS = ExperimentManagerDefinition

    def __init__(
        self,
        settings: Optional[ExperimentManagerSettings] = None,
        definition: Optional[ExperimentManagerDefinition] = None,
        db_client: Optional[MongoClient] = None,
        db_connection: Optional[Database] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the Experiment Manager."""
        # Store additional dependencies before calling super().__init__
        self._db_client = db_client
        self._db_connection = db_connection

        super().__init__(settings=settings, definition=definition, **kwargs)

        # Initialize database connection
        self._setup_database()

    def initialize(self, **kwargs: Any) -> None:
        """Initialize manager-specific components."""
        super().initialize(**kwargs)

        # Skip version validation if external db_client or db_connection was provided (e.g., in tests)
        # This is commonly done in tests where a mock or containerized MongoDB is used
        if self._db_client is not None or self._db_connection is not None:
            # External connection provided, likely in test context - skip version validation
            self.logger.info(
                "External db_client or db_connection provided, skipping MongoDB version validation"
            )
            return

        self.logger.info("Validating MongoDB schema version...")

        schema_file_path = Path(__file__).parent / "schema.json"

        version_checker = MongoDBVersionChecker(
            db_url=str(self.settings.mongo_db_url),
            database_name=self.settings.database_name,
            schema_file_path=str(schema_file_path),
            logger=self.logger,
        )

        try:
            version_checker.validate_or_fail()
            self.logger.info("MongoDB version validation completed successfully")
        except RuntimeError as e:
            self.logger.error(
                "DATABASE VERSION MISMATCH DETECTED! SERVER STARTUP ABORTED!"
            )
            raise e

    def _setup_database(self) -> None:
        """Setup database connection and collections."""
        if self._db_connection is None:
            if self._db_client is None:
                self._db_client = MongoClient(str(self.settings.mongo_db_url))
            self._db_connection = self._db_client[self.settings.database_name]

        self.experiments = self._db_connection[self.settings.collection_name]

    def get_health(self) -> ExperimentManagerHealth:
        """Get the health status of the Experiment Manager."""
        health = ExperimentManagerHealth()

        try:
            # Test database connection
            if self._db_client is not None:
                self._db_client.admin.command("ping")
            elif self._db_connection is not None:
                # Use the database connection directly to ping
                self._db_connection.client.admin.command("ping")
            else:
                raise Exception("No database connection available")
            health.db_connected = True

            # Get total experiments count
            health.total_experiments = self.experiments.count_documents({})

            health.healthy = True
            health.description = "Experiment Manager is running normally"

        except Exception as e:
            health.healthy = False
            health.db_connected = False
            health.description = f"Database connection failed: {e!s}"

        return health

    @get("/experiment/{experiment_id}")
    async def get_experiment(self, experiment_id: str) -> Experiment:
        """Get an experiment by ID."""
        experiment = self.experiments.find_one({"_id": experiment_id})
        if not experiment:
            raise HTTPException(status_code=404, detail="Experiment not found")
        return Experiment.model_validate(experiment)

    @get("/experiments")
    async def get_experiments(self, number: int = 10) -> list[Experiment]:
        """Get the latest experiments."""
        experiments_list = (
            self.experiments.find().sort("started_at", -1).limit(number).to_list()
        )
        return [
            Experiment.model_validate(experiment) for experiment in experiments_list
        ]

    @post("/experiment")
    async def start_experiment(
        self, experiment_request: ExperimentRegistration
    ) -> Experiment:
        """Start a new experiment."""
        experiment = Experiment.from_experiment_design(
            run_name=experiment_request.run_name,
            run_description=experiment_request.run_description,
            experiment_design=experiment_request.experiment_design,
        )
        experiment.started_at = datetime.datetime.now()

        self.experiments.insert_one(experiment.to_mongo())

        # Log the experiment start event
        self.logger.log(
            event=Event(
                event_type=EventType.EXPERIMENT_START,
                event_data={"experiment": experiment},
            )
        )
        return experiment

    @post("/experiment/{experiment_id}/end")
    async def end_experiment(self, experiment_id: str) -> Experiment:
        """End an experiment by ID."""
        experiment = self.experiments.find_one({"_id": experiment_id})
        if not experiment:
            raise HTTPException(status_code=404, detail="Experiment not found")
        experiment = Experiment.model_validate(experiment)
        experiment.ended_at = datetime.datetime.now()
        experiment.status = ExperimentStatus.COMPLETED
        self.experiments.update_one(
            {"_id": experiment_id},
            {"$set": experiment.to_mongo()},
        )
        self.logger.log(
            event=Event(
                event_type=EventType.EXPERIMENT_COMPLETE,
                event_data={"experiment": experiment},
            )
        )
        return experiment

    @post("/experiment/{experiment_id}/continue")
    async def continue_experiment(self, experiment_id: str) -> Experiment:
        """Continue an experiment by ID."""
        experiment = self.experiments.find_one({"_id": experiment_id})
        if not experiment:
            raise HTTPException(status_code=404, detail="Experiment not found")
        experiment = Experiment.model_validate(experiment)
        experiment.status = ExperimentStatus.IN_PROGRESS
        self.experiments.update_one(
            {"_id": experiment_id},
            {"$set": experiment.to_mongo()},
        )
        self.logger.log(
            event=Event(
                event_type=EventType.EXPERIMENT_CONTINUED,
                event_data={"experiment": experiment},
            )
        )
        return experiment

    @post("/experiment/{experiment_id}/pause")
    async def pause_experiment(self, experiment_id: str) -> Experiment:
        """Pause an experiment by ID."""
        experiment = self.experiments.find_one({"_id": experiment_id})
        if not experiment:
            raise HTTPException(status_code=404, detail="Experiment not found")
        experiment = Experiment.model_validate(experiment)
        experiment.status = ExperimentStatus.PAUSED
        self.experiments.update_one(
            {"_id": experiment_id},
            {"$set": experiment.to_mongo()},
        )
        self.logger.log(
            event=Event(
                event_type=EventType.EXPERIMENT_PAUSE,
                event_data={"experiment": experiment},
            )
        )
        return experiment

    @post("/experiment/{experiment_id}/cancel")
    async def cancel_experiment(self, experiment_id: str) -> Experiment:
        """Cancel an experiment by ID."""
        experiment = self.experiments.find_one({"_id": experiment_id})
        if not experiment:
            raise HTTPException(status_code=404, detail="Experiment not found")
        experiment = Experiment.model_validate(experiment)
        experiment.status = ExperimentStatus.CANCELLED
        self.experiments.update_one(
            {"_id": experiment_id},
            {"$set": experiment.to_mongo()},
        )
        self.logger.log(
            event=Event(
                event_type=EventType.EXPERIMENT_CANCELLED,
                event_data={"experiment": experiment},
            )
        )
        return experiment

    @post("/experiment/{experiment_id}/fail")
    async def fail_experiment(self, experiment_id: str) -> Experiment:
        """Fail an experiment by ID."""
        experiment = self.experiments.find_one({"_id": experiment_id})
        if not experiment:
            raise HTTPException(status_code=404, detail="Experiment not found")
        experiment = Experiment.model_validate(experiment)
        experiment.status = ExperimentStatus.FAILED
        self.experiments.update_one(
            {"_id": experiment_id},
            {"$set": experiment.to_mongo()},
        )
        self.logger.log(
            event=Event(
                event_type=EventType.EXPERIMENT_FAILED,
                event_data={"experiment": experiment},
            )
        )
        return experiment


# Main entry point for running the server
if __name__ == "__main__":
    manager = ExperimentManager()
    manager.run_server()
