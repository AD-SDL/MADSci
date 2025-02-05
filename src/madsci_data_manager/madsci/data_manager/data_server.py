"""REST Server for the MADSci Event Manager"""

from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, Optional

import uvicorn
from fastapi import FastAPI, Form, UploadFile
from fastapi.params import Body
from fastapi.routing import APIRouter
from madsci.client.event_client import EventClient
from madsci.common.types.data_types import DataManagerDefinition, Datapoint
from pymongo import MongoClient
from pymongo.synchronous.collection import Collection
from pymongo.synchronous.database import Database


class DataServer:
    """A REST server for managing MADSci events across a lab."""

    event_manager_definition: Optional[DataManagerDefinition] = None
    db_client: MongoClient
    app = FastAPI()
    logger = EventClient()
    data: Collection

    def __init__(
        self,
        data_manager_definition: Optional[DataManagerDefinition] = None,
        db_connection: Optional[Database] = None,
    ) -> None:
        """Initialize the Event Manager Server."""
        if data_manager_definition is not None:
            self.data_manager_definition = data_manager_definition
        else:
            self.data_manager_definition = DataManagerDefinition.load_model(
                require_unique=True
            )
        if self.data_manager_definition is None:
            raise ValueError(
                "No data manager definition found, please specify a path with --definition, or add it to your lab definition's 'managers' section"
            )

        # * Logger
        data_manager_definition.event_client_config.event_server_url = (
            None  # * Remove event_server_url to prevent infinite loop
        )
        self.logger = EventClient(data_manager_definition.event_client_config)
        self.logger.log_info(self.data_manager_definition)

        # * DB Config
        if db_connection is not None:
            self.events_db = db_connection
        else:
            self.db_client = MongoClient(self.data_manager_definition.db_url)
            self.datapoints_db = self.db_client["madsci_data"]
        self.datapoints = self.events_db["datapoints"]
        self.datapoints.create_index("datapoint_id", unique=True, background=True)

        # * REST Server Config
        self._configure_routes()

    async def root(self) -> DataManagerDefinition:
        """Return the Datapoint Manager Definition"""
        return self.data_manager_definition

    async def create_datapoint(
        self, datapoint: Annotated[Datapoint, Form()], files: list[UploadFile] = []
    ) -> Datapoint:
        """Create a new datapoint."""
        for file in files:
            time = datetime.now()
            path = Path(time.year) / time.month / time.day
            path.mkdir(parents=True, exist_ok=True)
            final_path = path / datapoint.datapoint_id + "_" + file.filename
            with Path.open(final_path, "wb") as f:
                f.write(file)
            datapoint.path = final_path
        self.datapoints.insert_one(datapoint.model_dump(mode="json"))
        return datapoint

    async def get_datapoint(self, datapoint_id: str) -> Datapoint:
        """Look up an datapoint by datapoint_id"""
        return self.events.find_one({"datapoint_id": datapoint_id})

    async def get_datapoints(self, number: int = 100) -> dict[str, Datapoint]:
        """Get the latest datapoints"""
        datapoint_list = (
            self.datapoints.sort("data_timestamp", -1).limit(number).to_list()
        )
        return {datapoint["datapoint_id"]: datapoint for datapoint in datapoint_list}

    async def query_datapoints(self, selector: Any = Body()) -> dict[str, Datapoint]:  # noqa: B008
        """Query datapoints based on a selector. Note: this is a raw query, so be careful."""
        datapoint_list = self.datapoints.find(selector).to_list()
        return {datapoint["datapoint_id"]: datapoint for datapoint in datapoint_list}

    def start_server(self) -> None:
        """Start the server."""
        uvicorn.run(
            self.app,
            host=self.event_manager_definition.host,
            port=self.event_manager_definition.port,
        )

    def _configure_routes(self) -> None:
        self.router = APIRouter()
        self.router.add_api_route("/", self.root, methods=["GET"])
        self.router.add_api_route(
            "/datapoint/{datapoint_id}", self.get_datapoint, methods=["GET"]
        )
        self.router.add_api_route("/datapoint", self.get_datapoints, methods=["GET"])
        self.router.add_api_route("/datapoints", self.get_datapoints, methods=["GET"])
        self.router.add_api_route("/datapoint", self.create_datapoint, methods=["POST"])
        self.router.add_api_route(
            "/datapoints/query", self.query_datapoints, methods=["POST"]
        )
        self.router.add_api_route(
            "/datapoints/query", self.query_datapoints, methods=["POST"]
        )
        self.app.include_router(self.router)


if __name__ == "__main__":
    server = DataServer()
    server.start_server()
