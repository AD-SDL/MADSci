"""REST API and Server for the Experiment Manager."""

import datetime
from dataclasses import dataclass
from typing import Optional

import uvicorn
from fastapi import FastAPI
from fastapi.routing import APIRouter
from madsci.client.event_client import EventClient, EventType
from madsci.common.types.event_types import Event
from madsci.common.types.experiment_types import (
    Experiment,
    ExperimentDesign,
    ExperimentManagerDefinition,
    ExperimentRegistration,
    ExperimentStatus,
)
from nicegui import ui
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database


class ExperimentServer:
    """A REST Server for managing MADSci experiments across a lab."""

    experiment_manager_definition: Optional[ExperimentManagerDefinition] = None
    db_client: MongoClient
    app = None
    logger = EventClient()
    experiments: Collection

    def __init__(
        self,
        experiment_manager_definition: Optional[ExperimentManagerDefinition] = None,
        db_connection: Optional[Database] = None,
        enable_ui: bool = True,
    ) -> None:
        """Initialize the Experiment Manager Server."""
        self.app = FastAPI()
        if experiment_manager_definition is not None:
            self.experiment_manager_definition = experiment_manager_definition
        else:
            self.experiment_manager_definition = ExperimentManagerDefinition.load_model(
                require_unique=True
            )

        if self.experiment_manager_definition is None:
            raise ValueError(
                "No experiment manager definition found, please specify a path with --definition, or add it to your lab definition's 'managers' section"
            )

        # * Logger
        self.logger = EventClient(
            self.experiment_manager_definition.event_client_config
        )
        self.logger.log_info(self.experiment_manager_definition)

        # * DB Config
        if db_connection is not None:
            self.db_connection = db_connection
        else:
            self.db_client = MongoClient(self.experiment_manager_definition.db_url)
            self.db_connection = self.db_client["experiment_manager"]
        self.experiments = self.db_connection["experiments"]

        # * REST Server Config
        self._configure_routes()
        if enable_ui:
            self._configure_ui(self.app)

    async def definition(self) -> Optional[ExperimentManagerDefinition]:
        """Get the definition for the Experiment Manager."""
        return self.experiment_manager_definition

    async def get_experiment(self, experiment_id: str) -> Experiment:
        """Get an experiment by ID."""
        return Experiment.model_validate(
            self.experiments.find_one({"_id": experiment_id})
        )

    async def get_experiments(self, number: int = 10) -> list[Experiment]:
        """Get the latest experiments."""
        experiments = (
            self.experiments.find().sort("started_at", -1).limit(number).to_list()
        )
        return [Experiment.model_validate(experiment) for experiment in experiments]

    async def start_experiment(
        self,
        experiment_request: ExperimentRegistration,
    ) -> Experiment:
        """Start a new experiment."""
        experiment = Experiment.from_experiment_design(
            run_name=experiment_request.run_name,
            run_description=experiment_request.run_description,
            experiment_design=experiment_request.experiment_design,
        )
        experiment.started_at = datetime.datetime.now()
        self.experiments.insert_one(experiment.to_mongo())
        self.logger.log(
            event=Event(
                event_type=EventType.EXPERIMENT_START,
                event_data={"experiment": experiment},
            )
        )
        return experiment

    async def end_experiment(self, experiment_id: str) -> Experiment:
        """End an experiment by ID."""
        experiment = Experiment.model_validate(
            self.experiments.find_one({"_id": experiment_id})
        )
        if experiment is None:
            raise ValueError(f"Experiment {experiment_id} not found.")
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

    async def continue_experiment(self, experiment_id: str) -> Experiment:
        """Continue an experiment by ID."""
        experiment = Experiment.model_validate(
            self.experiments.find_one({"_id": experiment_id})
        )
        if experiment is None:
            raise ValueError(f"Experiment {experiment_id} not found.")
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

    async def pause_experiment(self, experiment_id: str) -> Experiment:
        """Pause an experiment by ID."""
        experiment = Experiment.model_validate(
            self.experiments.find_one({"_id": experiment_id})
        )
        if experiment is None:
            raise ValueError(f"Experiment {experiment_id} not found.")
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

    async def cancel_experiment(self, experiment_id: str) -> Experiment:
        """Cancel an experiment by ID."""
        experiment = Experiment.model_validate(
            self.experiments.find_one({"_id": experiment_id})
        )
        if experiment is None:
            raise ValueError(f"Experiment {experiment_id} not found.")
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

    async def fail_experiment(self, experiment_id: str) -> Experiment:
        """Fail an experiment by ID."""
        experiment = Experiment.model_validate(
            self.experiments.find_one({"_id": experiment_id})
        )
        if experiment is None:
            raise ValueError(f"Experiment {experiment_id} not found.")
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

    def start_server(self) -> None:
        """Start the server."""
        uvicorn.run(
            self.app,
            host=self.experiment_manager_definition.host,
            port=self.experiment_manager_definition.port,
        )

    def _configure_routes(self) -> None:
        self.router = APIRouter()
        self.router.add_api_route("/definition", self.definition, methods=["GET"])
        self.router.add_api_route(
            "/experiment/{experiment_id}", self.get_experiment, methods=["GET"]
        )
        self.router.add_api_route("/experiments", self.get_experiments, methods=["GET"])
        self.router.add_api_route(
            "/experiment", self.start_experiment, methods=["POST"]
        )
        self.router.add_api_route(
            "/experiment/{experiment_id}/end", self.end_experiment, methods=["POST"]
        )
        self.router.add_api_route(
            "/experiment/{experiment_id}/continue",
            self.continue_experiment,
            methods=["POST"],
        )
        self.router.add_api_route(
            "/experiment/{experiment_id}/pause", self.pause_experiment, methods=["POST"]
        )
        self.router.add_api_route(
            "/experiment/{experiment_id}/cancel",
            self.cancel_experiment,
            methods=["POST"],
        )
        self.router.add_api_route(
            "/experiment/{experiment_id}/fail",
            self.fail_experiment,
            methods=["POST"],
        )
        self.app.include_router(self.router)

    def _configure_ui(self, fastapi_app: FastAPI) -> None:
        """Configure the UI for the Experiment Manager."""

        @ui.page(path="/")
        async def show() -> None:
            """Show the Experiment Manager UI."""
            ui.label("Welcome to the Experiment Manager!")
            experiment_dump = ui.label(
                f"Experiments: {[experiment.model_dump(mode='json') for experiment in await self.get_experiments()]}"
            )

            async def new_experiment() -> None:
                """Create a new Experiment"""
                experiment = await self.start_experiment(
                    experiment_design=ExperimentDesign(**experiment_form.__dict__),
                    run_name="Test Run",
                    run_description="This is a test run.",
                )
                ui.label(f"New Experiment: {experiment.model_dump(mode='json')}")
                experiment_dump.set_text(
                    f"Experiments: {[experiment.model_dump(mode='json') for experiment in await self.get_experiments()]}"
                )

            @dataclass
            class ExperimentForm:
                experiment_name: str = "New Experiment"
                experiment_description: str = "Describe your new experiment."

            experiment_form = ExperimentForm()
            ui.input("Experiment Name").bind_value(experiment_form, "experiment_name")
            ui.input("Experiment Description").bind_value(
                experiment_form, "experiment_description"
            )
            ui.button(text="New Experiment", on_click=new_experiment)

        ui.run_with(
            fastapi_app,
            title="Experiment Manager",
        )


if __name__ == "__main__":
    server = ExperimentServer()
    server.start_server()
