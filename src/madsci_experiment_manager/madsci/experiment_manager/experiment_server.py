"""Experiment Manager implementation using the new AbstractManagerBase class."""

import datetime
import warnings
from pathlib import Path
from typing import Any, Optional

from classy_fastapi import get, post
from fastapi import HTTPException
from madsci.common.db_handlers.document_storage_handler import (
    DocumentStorageHandler,
    PyDocumentStorageHandler,
)
from madsci.common.document_db_version_checker import DocumentDBVersionChecker
from madsci.common.manager_base import AbstractManagerBase
from madsci.common.types.document_db_migration_types import DocumentDBMigrationSettings
from madsci.common.types.event_types import EventType
from madsci.common.types.experiment_types import (
    Experiment,
    ExperimentManagerHealth,
    ExperimentManagerSettings,
    ExperimentRegistration,
    ExperimentStatus,
)
from pymongo import MongoClient
from pymongo.database import Database


class ExperimentManager(AbstractManagerBase[ExperimentManagerSettings]):
    """Experiment Manager REST Server."""

    SETTINGS_CLASS = ExperimentManagerSettings

    def __init__(
        self,
        settings: Optional[ExperimentManagerSettings] = None,
        db_client: Optional[MongoClient] = None,
        db_connection: Optional[Database] = None,
        document_handler: Optional[DocumentStorageHandler] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the Experiment Manager."""
        if db_client is not None:
            warnings.warn(
                "The 'db_client' parameter is deprecated. Use 'document_handler' instead.",
                DeprecationWarning,
                stacklevel=2,
            )
        if db_connection is not None:
            warnings.warn(
                "The 'db_connection' parameter is deprecated. Use 'document_handler' instead.",
                DeprecationWarning,
                stacklevel=2,
            )
        # Store additional dependencies before calling super().__init__
        self._document_handler = document_handler
        self._db_client = db_client
        self._db_connection = db_connection

        super().__init__(settings=settings, **kwargs)

        # Initialize database connection
        self._setup_database()

    def initialize(self, **kwargs: Any) -> None:
        """Initialize manager-specific components."""
        super().initialize(**kwargs)

        # Skip version validation if an external handler/connection was provided (e.g., in tests)
        if (
            self._document_handler is not None
            or self._db_client is not None
            or self._db_connection is not None
        ):
            # External connection provided, likely in test context - skip version validation
            self.logger.info(
                "External db_connection provided, skipping MongoDB version validation",
                event_type=EventType.MANAGER_START,
            )
            return

        self.logger.info(
            "Validating MongoDB schema version",
            event_type=EventType.MANAGER_START,
            database_name=self.settings.database_name,
        )

        schema_file_path = Path(__file__).parent / "schema.json"

        mig_cfg = DocumentDBMigrationSettings(database=self.settings.database_name)
        version_checker = DocumentDBVersionChecker(
            db_url=str(self.settings.document_db_url),
            database_name=self.settings.database_name,
            schema_file_path=str(schema_file_path),
            backup_dir=str(mig_cfg.backup_dir),
            logger=self.logger,
        )

        try:
            version_checker.validate_or_fail()
            self.logger.info(
                "MongoDB version validation completed successfully",
                event_type=EventType.MANAGER_START,
                database_name=self.settings.database_name,
            )
        except RuntimeError as e:
            self.logger.error(
                "Database version mismatch detected; server startup aborted",
                event_type=EventType.MANAGER_ERROR,
                database_name=self.settings.database_name,
            )
            raise e

    def _setup_database(self) -> None:
        """Setup database connection and collections."""
        if self._document_handler is None:
            if self._db_connection is not None:
                # Legacy path: wrap an externally provided Database object
                self._document_handler = PyDocumentStorageHandler(self._db_connection)
            elif self._db_client is not None:
                # Legacy path: wrap an externally provided MongoClient
                self._document_handler = PyDocumentStorageHandler(
                    self._db_client[self.settings.database_name]
                )
            else:
                self._document_handler = PyDocumentStorageHandler.from_url(
                    str(self.settings.document_db_url),
                    self.settings.database_name,
                )

        self.experiments = self._document_handler.get_collection(
            self.settings.collection_name
        )

    def get_health(self) -> ExperimentManagerHealth:
        """Get the health status of the Experiment Manager."""
        health = ExperimentManagerHealth()

        try:
            # Test database connection
            health.db_connected = self._document_handler.ping()

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
        with self.span(
            "experiment.get",
            attributes={"experiment.id": experiment_id},
        ):
            experiment = self.experiments.find_one({"_id": experiment_id})
            if not experiment:
                raise HTTPException(status_code=404, detail="Experiment not found")
            return Experiment.model_validate(experiment)

    @get("/experiments")
    async def get_experiments(self, number: int = 10) -> list[Experiment]:
        """Get the latest experiments."""
        with self.span("experiment.query", attributes={"experiment.limit": number}):
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
        with self.span(
            "experiment.start",
            attributes={
                "experiment.run_name": experiment_request.run_name,
            },
        ):
            experiment = Experiment.from_experiment_design(
                run_name=experiment_request.run_name,
                run_description=experiment_request.run_description,
                experiment_design=experiment_request.experiment_design,
            )
            experiment.started_at = datetime.datetime.now()

            self.experiments.insert_one(experiment.to_mongo())

            self.logger.info(
                "Experiment started",
                event_type=EventType.EXPERIMENT_START,
                experiment_id=experiment.experiment_id,
                run_name=experiment.run_name,
            )
            return experiment

    @post("/experiment/{experiment_id}/end")
    async def end_experiment(self, experiment_id: str) -> Experiment:
        """End an experiment by ID."""
        with self.span(
            "experiment.end",
            attributes={"experiment.id": experiment_id},
        ):
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
            self.logger.info(
                "Experiment completed",
                event_type=EventType.EXPERIMENT_COMPLETE,
                experiment_id=experiment.experiment_id,
                run_name=experiment.run_name,
            )
            return experiment

    @post("/experiment/{experiment_id}/continue")
    async def continue_experiment(self, experiment_id: str) -> Experiment:
        """Continue an experiment by ID."""
        with self.span(
            "experiment.continue",
            attributes={"experiment.id": experiment_id},
        ):
            experiment = self.experiments.find_one({"_id": experiment_id})
            if not experiment:
                raise HTTPException(status_code=404, detail="Experiment not found")
            experiment = Experiment.model_validate(experiment)
            experiment.status = ExperimentStatus.IN_PROGRESS
            self.experiments.update_one(
                {"_id": experiment_id},
                {"$set": experiment.to_mongo()},
            )
            self.logger.info(
                "Experiment continued",
                event_type=EventType.EXPERIMENT_CONTINUED,
                experiment_id=experiment.experiment_id,
                run_name=experiment.run_name,
            )
            return experiment

    @post("/experiment/{experiment_id}/pause")
    async def pause_experiment(self, experiment_id: str) -> Experiment:
        """Pause an experiment by ID."""
        with self.span(
            "experiment.pause",
            attributes={"experiment.id": experiment_id},
        ):
            experiment = self.experiments.find_one({"_id": experiment_id})
            if not experiment:
                raise HTTPException(status_code=404, detail="Experiment not found")
            experiment = Experiment.model_validate(experiment)
            experiment.status = ExperimentStatus.PAUSED
            self.experiments.update_one(
                {"_id": experiment_id},
                {"$set": experiment.to_mongo()},
            )
            self.logger.info(
                "Experiment paused",
                event_type=EventType.EXPERIMENT_PAUSE,
                experiment_id=experiment.experiment_id,
                run_name=experiment.run_name,
            )
            return experiment

    @post("/experiment/{experiment_id}/cancel")
    async def cancel_experiment(self, experiment_id: str) -> Experiment:
        """Cancel an experiment by ID."""
        with self.span(
            "experiment.cancel",
            attributes={"experiment.id": experiment_id},
        ):
            experiment = self.experiments.find_one({"_id": experiment_id})
            if not experiment:
                raise HTTPException(status_code=404, detail="Experiment not found")
            experiment = Experiment.model_validate(experiment)
            experiment.status = ExperimentStatus.CANCELLED
            self.experiments.update_one(
                {"_id": experiment_id},
                {"$set": experiment.to_mongo()},
            )
            self.logger.info(
                "Experiment cancelled",
                event_type=EventType.EXPERIMENT_CANCELLED,
                experiment_id=experiment.experiment_id,
                run_name=experiment.run_name,
            )
            return experiment

    @post("/experiment/{experiment_id}/fail")
    async def fail_experiment(self, experiment_id: str) -> Experiment:
        """Fail an experiment by ID."""
        with self.span(
            "experiment.fail",
            attributes={"experiment.id": experiment_id},
        ):
            experiment = self.experiments.find_one({"_id": experiment_id})
            if not experiment:
                raise HTTPException(status_code=404, detail="Experiment not found")
            experiment = Experiment.model_validate(experiment)
            experiment.status = ExperimentStatus.FAILED
            self.experiments.update_one(
                {"_id": experiment_id},
                {"$set": experiment.to_mongo()},
            )
            self.logger.error(
                "Experiment failed",
                event_type=EventType.EXPERIMENT_FAILED,
                experiment_id=experiment.experiment_id,
                run_name=experiment.run_name,
            )
            return experiment


# Main entry point for running the server
if __name__ == "__main__":
    manager = ExperimentManager()
    manager.run_server()
