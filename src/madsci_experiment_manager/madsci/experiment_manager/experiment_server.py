"""REST API and Server for the Experiment Manager."""

import datetime
from dataclasses import dataclass
from typing import Optional

import uvicorn
from fastapi import FastAPI
from fastapi.routing import APIRouter
from madsci.client.event_client import EventClient, EventType
from madsci.common.definition_loaders import manager_definition_loader
from madsci.common.types.event_types import Event
from madsci.common.types.experiment_types import (
    Experiment,
    ExperimentDesign,
    ExperimentManagerDefinition,
)
from madsci.common.types.lab_types import ManagerType
from nicegui import ui
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database


class ExperimentServer:
    """A REST Server for managing MADSci experiments across a lab."""

    experiment_manager_definition: Optional[ExperimentManagerDefinition] = None
    db_client: MongoClient
    app = FastAPI()
    logger = EventClient()
    experiments: Collection

    def __init__(
        self,
        experiment_manager_definition: Optional[ExperimentManagerDefinition] = None,
        db_connection: Optional[Database] = None,
        enable_ui: bool = True,
    ) -> None:
        """Initialize the Experiment Manager Server."""
        if experiment_manager_definition is not None:
            self.experiment_manager_definition = experiment_manager_definition
        else:
            # Load the experiment manager definition
            manager_definitions = manager_definition_loader()
            for manager in manager_definitions:
                if manager.manager_type == ManagerType.EXPERIMENT_MANAGER:
                    self.experiment_manager_definition = manager

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
        if enable_ui:
            self.configure_ui(self.app)
        self._configure_routes()

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
        experiment_design: ExperimentDesign,
        run_name: Optional[str] = None,
        run_description: Optional[str] = None,
    ) -> Experiment:
        """Start a new experiment."""
        experiment = Experiment.from_experiment_design(
            run_name=run_name,
            run_description=run_description,
            experiment_design=experiment_design,
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
        self.app.include_router(self.router)

    def configure_ui(self, fastapi_app: FastAPI) -> None:
        """Configure the UI for the Experiment Manager."""

        @ui.page(path="/")
        def show() -> None:
            """Show the Experiment Manager UI."""
            ui.label("Welcome to the Experiment Manager!")
            ui.label(
                f"Experiments: {[experiment.model_dump(mode='json') for experiment in self.get_experiments()]}"
            )

            def new_experiment() -> None:
                """Create a new Experiment"""
                experiment = self.start_experiment(
                    experiment_design=ExperimentDesign(
                        experiment_name="Test Experiment",
                        experiment_description="This is a test experiment.",
                    ),
                    run_name="Test Run",
                    run_description="This is a test run.",
                )
                ui.label(f"New Experiment: {experiment.model_dump(mode='json')}")

            @dataclass
            class NewExperiment:
                experiment_name: str = "Test Experiment"
                experiment_description: str = "This is a test experiment."

            ui.input("Experiment Name", model=NewExperiment, field="experiment_name")
            ui.button(text="New Experiment", on_click=new_experiment)

        ui.run_with(
            fastapi_app,
            title="Experiment Manager",
        )


if __name__ == "__main__":
    server = ExperimentServer()
    server.start_server()
