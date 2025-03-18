"""REST Server for the MADSci Data Manager"""

import json
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, Optional

import uvicorn
from fastapi import FastAPI, Form, Response, UploadFile
from fastapi.params import Body
from fastapi.responses import FileResponse, JSONResponse
from madsci.common.types.datapoint_types import DataManagerDefinition, DataPoint
from pymongo import MongoClient


def create_data_server(  # noqa: C901
    data_manager_definition: Optional[DataManagerDefinition] = None,
    db_client: Optional[MongoClient] = None,
) -> FastAPI:
    """Creates a Data Manager's REST server."""

    if not data_manager_definition:
        data_manager_definition = DataManagerDefinition.load_model()
    if db_client is None:
        db_client = MongoClient(data_manager_definition.db_url)

    app = FastAPI()
    datapoints_db = db_client["madsci_data"]
    datapoints = datapoints_db["datapoints"]
    datapoints.create_index("datapoint_id", unique=True, background=True)

    @app.get("/")
    async def root() -> DataManagerDefinition:
        """Return the DataPoint Manager Definition"""
        return data_manager_definition

    @app.post("/datapoint")
    async def create_datapoint(
        datapoint: Annotated[str, Form()], files: list[UploadFile] = []
    ) -> Any:
        """Create a new datapoint."""
        data = json.loads(datapoint)
        datapoint = DataPoint.discriminate(data)
        for file in files:
            time = datetime.now()
            path = (
                Path(data_manager_definition.file_storage_path).expanduser()
                / str(time.year)
                / str(time.month)
                / str(time.day)
            )
            path.mkdir(parents=True, exist_ok=True)
            final_path = path / (datapoint.datapoint_id + "_" + file.filename)
            with Path.open(final_path, "wb") as f:
                contents = file.file.read()
                f.write(contents)
            datapoint.path = str(final_path)
        datapoints.insert_one(datapoint.model_dump(mode="json"))
        return datapoint

    @app.get("/datapoint/{datapoint_id}")
    async def get_datapoint(datapoint_id: str) -> Any:
        """Look up a datapoint by datapoint_id"""
        datapoint = datapoints.find_one({"datapoint_id": datapoint_id})
        return DataPoint.discriminate(datapoint)

    @app.get("/datapoint/{datapoint_id}/value")
    async def get_datapoint_value(datapoint_id: str) -> Response:
        """Returns a specific data point's value. If this is a file, it will return the file."""
        datapoint = datapoints.find_one({"datapoint_id": datapoint_id})
        datapoint = DataPoint.discriminate(datapoint)
        if datapoint.data_type == "file":
            return FileResponse(datapoint.path)
        return JSONResponse(datapoint.value)

    @app.get("/datapoints")
    async def get_datapoints(number: int = 100) -> dict[str, Any]:
        """Get the latest datapoints"""
        datapoint_list = (
            datapoints.find({}).sort("data_timestamp", -1).limit(number).to_list()
        )
        return {
            datapoint["datapoint_id"]: DataPoint.discriminate(datapoint)
            for datapoint in datapoint_list
        }

    @app.post("/datapoints/query")
    async def query_datapoints(selector: Any = Body()) -> dict[str, Any]:  # noqa: B008
        """Query datapoints based on a selector. Note: this is a raw query, so be careful."""
        datapoint_list = datapoints.find(selector).to_list()
        return {
            datapoint["datapoint_id"]: DataPoint.discriminate(datapoint)
            for datapoint in datapoint_list
        }

    return app


if __name__ == "__main__":
    data_manager_definition = DataManagerDefinition.load_model()
    db_client = MongoClient(data_manager_definition.db_url)
    app = create_data_server(
        data_manager_definition=data_manager_definition,
        db_client=db_client,
    )
    uvicorn.run(
        app,
        host=data_manager_definition.host,
        port=data_manager_definition.port,
    )
