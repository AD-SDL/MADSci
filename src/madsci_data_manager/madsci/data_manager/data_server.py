"""Data Manager implementation using the new AbstractManagerBase class."""

import json
import tempfile
import warnings
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, Dict, Optional

from classy_fastapi import get, post
from fastapi import Form, Response, UploadFile
from fastapi.params import Body
from fastapi.responses import FileResponse, JSONResponse
from madsci.common.manager_base import AbstractManagerBase
from madsci.common.object_storage_helpers import (
    ObjectNamingStrategy,
    create_minio_client,
    upload_file_to_object_storage,
)
from madsci.common.types.datapoint_types import (
    DataManagerDefinition,
    DataManagerHealth,
    DataManagerSettings,
    DataPoint,
    ObjectStorageSettings,
)
from minio import Minio
from pymongo import MongoClient


class DataManager(AbstractManagerBase[DataManagerSettings, DataManagerDefinition]):
    """Data Manager REST Server."""

    SETTINGS_CLASS = DataManagerSettings
    DEFINITION_CLASS = DataManagerDefinition

    def __init__(
        self,
        settings: Optional[DataManagerSettings] = None,
        definition: Optional[DataManagerDefinition] = None,
        object_storage_settings: Optional[ObjectStorageSettings] = None,
        db_client: Optional[MongoClient] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the Data Manager."""
        # Store additional dependencies before calling super().__init__
        self._object_storage_settings = object_storage_settings
        self._db_client = db_client

        super().__init__(settings=settings, definition=definition, **kwargs)

        # Initialize database and storage
        self._setup_database()
        self._setup_storage()

    def _setup_database(self) -> None:
        """Setup database connection and collections."""
        if self._db_client is None:
            self._db_client = MongoClient(self.settings.db_url)

        self.datapoints_db = self._db_client["madsci_data"]
        self.datapoints = self.datapoints_db["datapoints"]

    def _setup_storage(self) -> None:
        """Setup MinIO client if configuration is provided."""
        self.minio_client = create_minio_client(
            object_storage_settings=self._object_storage_settings
        )

    def get_health(self) -> DataManagerHealth:
        """Get the health status of the Data Manager."""
        health = DataManagerHealth()

        try:
            # Test database connection
            self._db_client.admin.command("ping")
            health.db_connected = True

            # Test storage accessibility
            storage_path = Path(self.settings.file_storage_path).expanduser()
            storage_path.mkdir(parents=True, exist_ok=True)
            test_file = storage_path / ".health_check"
            test_file.touch(exist_ok=True)
            test_file.write_text("health_check")
            test_file.unlink()
            health.storage_accessible = True

            # Get total datapoints count
            health.total_datapoints = self.datapoints.count_documents({})

            health.healthy = True
            health.description = "Data Manager is running normally"

        except Exception as e:
            health.healthy = False
            if hasattr(e, "__contains__") and "mongo" in str(e).lower():
                health.db_connected = False
            if hasattr(e, "__contains__") and (
                "file" in str(e).lower() or "path" in str(e).lower()
            ):
                health.storage_accessible = False
            health.description = f"Health check failed: {e!s}"

        return health

    @get("/health")
    def health_endpoint(self) -> DataManagerHealth:
        """Health check endpoint for the Data Manager."""
        return self.get_health()

    @get("/")
    def get_definition(self) -> DataManagerDefinition:
        """Return the manager definition."""
        return self.definition

    @get("/definition")
    def get_definition_alt(self) -> DataManagerDefinition:
        """Return the manager definition."""
        return self.definition

    def _upload_file_to_minio(
        self,
        minio_client: Minio,
        file_path: Path,
        filename: str,
        label: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Upload a file to MinIO object storage and return object storage info."""
        if minio_client is None:
            return None

        # Use the helper function with server's timestamped naming strategy
        return upload_file_to_object_storage(
            minio_client=minio_client,
            file_path=file_path,
            bucket_name=(
                self._object_storage_settings or ObjectStorageSettings()
            ).default_bucket,
            metadata=metadata,
            naming_strategy=ObjectNamingStrategy.TIMESTAMPED_PATH,
            label=label or filename,
            object_storage_settings=self._object_storage_settings,
        )

    @post("/datapoint")
    async def create_datapoint(
        self, datapoint: Annotated[str, Form()], files: list[UploadFile] = []
    ) -> Any:
        """Create a new datapoint."""
        datapoint_obj = DataPoint.discriminate(json.loads(datapoint))

        # Handle file uploads if present
        if files:
            for file in files:
                # Check if this is a file datapoint and MinIO is configured
                if (
                    datapoint_obj.data_type.value == "file"
                    and self.minio_client is not None
                ):
                    # Use MinIO object storage instead of local storage
                    # First, save file temporarily to upload to MinIO

                    with tempfile.NamedTemporaryFile(
                        delete=False, suffix=f"_{file.filename}"
                    ) as temp_file:
                        contents = file.file.read()
                        temp_file.write(contents)
                        temp_file.flush()
                        temp_path = Path(temp_file.name)

                    # Upload to MinIO object storage
                    object_storage_info = self._upload_file_to_minio(
                        minio_client=self.minio_client,
                        file_path=temp_path,
                        filename=file.filename,
                        label=datapoint_obj.label,
                        metadata={"original_datapoint_id": datapoint_obj.datapoint_id},
                    )

                    # Clean up temporary file
                    temp_path.unlink()

                    # If upload was successful, store object storage information in database
                    if object_storage_info:
                        # Create a combined dictionary with both datapoint and object storage info
                        datapoint_dict = datapoint_obj.to_mongo()
                        datapoint_dict.update(object_storage_info)
                        # Update data_type to indicate this is now an object storage datapoint
                        datapoint_dict["data_type"] = "object_storage"
                        self.datapoints.insert_one(datapoint_dict)
                        # Return the transformed datapoint
                        return DataPoint.discriminate(datapoint_dict)
                    # If MinIO upload failed, fall back to local storage
                    warnings.warn(
                        "MinIO upload failed, falling back to local file storage",
                        UserWarning,
                        stacklevel=2,
                    )
                # Fallback to local storage
                time = datetime.now()
                path = (
                    Path(self.settings.file_storage_path).expanduser()
                    / str(time.year)
                    / str(time.month)
                    / str(time.day)
                )
                path.mkdir(parents=True, exist_ok=True)
                final_path = path / (datapoint_obj.datapoint_id + "_" + file.filename)

                # Reset file position and save locally
                file.file.seek(0)
                with Path.open(final_path, "wb") as f:
                    contents = file.file.read()
                    f.write(contents)
                datapoint_obj.path = str(final_path)
                self.datapoints.insert_one(datapoint_obj.to_mongo())
                return datapoint_obj
        else:
            # No files - just insert the datapoint (for ValueDataPoint, etc.)
            self.datapoints.insert_one(datapoint_obj.to_mongo())
            return datapoint_obj

        return None

    @get("/datapoint/{datapoint_id}")
    async def get_datapoint(self, datapoint_id: str) -> Any:
        """Look up a datapoint by datapoint_id"""
        datapoint = self.datapoints.find_one({"_id": datapoint_id})
        if not datapoint:
            return JSONResponse(
                status_code=404,
                content={"message": f"Datapoint with id {datapoint_id} not found."},
            )
        return DataPoint.discriminate(datapoint)

    @get("/datapoint/{datapoint_id}/value")
    async def get_datapoint_value(self, datapoint_id: str) -> Response:
        """Returns a specific data point's value. If this is a file, it will return the file."""
        datapoint = self.datapoints.find_one({"_id": datapoint_id})
        datapoint = DataPoint.discriminate(datapoint)
        if datapoint.data_type == "file":
            return FileResponse(datapoint.path)
        return JSONResponse(datapoint.value)

    @get("/datapoints")
    async def get_datapoints(self, number: int = 100) -> Dict[str, Any]:
        """Get the latest datapoints"""
        datapoint_list = (
            self.datapoints.find({}).sort("data_timestamp", -1).limit(number).to_list()
        )
        return {
            datapoint["_id"]: DataPoint.discriminate(datapoint)
            for datapoint in datapoint_list
        }

    @post("/datapoints/query")
    async def query_datapoints(self, selector: Any = Body()) -> Dict[str, Any]:  # noqa: B008
        """Query datapoints based on a selector. Note: this is a raw query, so be careful."""
        datapoint_list = self.datapoints.find(selector).to_list()
        return {
            datapoint["_id"]: DataPoint.discriminate(datapoint)
            for datapoint in datapoint_list
        }


# Main entry point for running the server
if __name__ == "__main__":
    manager = DataManager()
    manager.run_server()
