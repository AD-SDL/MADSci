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
from madsci.common.db_handlers.document_storage_handler import (
    DocumentStorageHandler,
    PyDocumentStorageHandler,
)
from madsci.common.db_handlers.object_storage_handler import (
    ObjectStorageHandler,
    RealObjectStorageHandler,
)
from madsci.common.document_db_version_checker import DocumentDBVersionChecker
from madsci.common.manager_base import AbstractManagerBase
from madsci.common.object_storage_helpers import (
    ObjectNamingStrategy,
    create_object_storage_client,
    generate_object_name,
)
from madsci.common.types.datapoint_types import (
    DataManagerHealth,
    DataManagerSettings,
    DataPoint,
    ObjectStorageSettings,
)
from madsci.common.types.event_types import EventType
from pymongo import MongoClient


class DataManager(AbstractManagerBase[DataManagerSettings]):
    """Data Manager REST Server."""

    SETTINGS_CLASS = DataManagerSettings

    def __init__(
        self,
        settings: Optional[DataManagerSettings] = None,
        object_storage_settings: Optional[ObjectStorageSettings] = None,
        db_client: Optional[MongoClient] = None,
        document_handler: Optional[DocumentStorageHandler] = None,
        object_storage_handler: Optional[ObjectStorageHandler] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the Data Manager."""
        if db_client is not None:
            warnings.warn(
                "The 'db_client' parameter is deprecated. Use 'document_handler' instead.",
                DeprecationWarning,
                stacklevel=2,
            )
        # Store additional dependencies before calling super().__init__
        self._object_storage_settings = object_storage_settings
        self._db_client = db_client
        self._document_handler = document_handler
        self._object_storage_handler = object_storage_handler

        super().__init__(settings=settings, **kwargs)

        # Initialize database and storage
        self._setup_database()
        self._setup_object_storage()

    def initialize(self, **kwargs: Any) -> None:
        """Initialize manager-specific components."""
        super().initialize(**kwargs)

        # Skip version validation if an external handler/connection was provided (e.g., in tests)
        if self._document_handler is not None or self._db_client is not None:
            return

        self.logger.info(
            "Validating MongoDB schema version",
            event_type=EventType.MANAGER_START,
            database_name=self.settings.database_name,
        )

        schema_file_path = Path(__file__).parent / "schema.json"
        version_checker = DocumentDBVersionChecker(
            db_url=str(self.settings.document_db_url),
            database_name=self.settings.database_name,
            schema_file_path=str(schema_file_path),
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
            if self._db_client is not None:
                # Legacy path: wrap an externally provided MongoClient
                db = self._db_client[self.settings.database_name]
                self._document_handler = PyDocumentStorageHandler(db)
            else:
                self._document_handler = PyDocumentStorageHandler.from_url(
                    str(self.settings.document_db_url),
                    self.settings.database_name,
                )

        self.datapoints = self._document_handler.get_collection(
            self.settings.collection_name
        )

    def _setup_object_storage(self) -> None:
        """Setup object storage handler."""
        if self._object_storage_handler is not None:
            # Handler provided directly (e.g., InMemoryObjectStorageHandler for tests)
            return

        storage_client = create_object_storage_client(
            object_storage_settings=self._object_storage_settings
        )
        if storage_client is not None:
            self._object_storage_handler = RealObjectStorageHandler(storage_client)

    def get_health(self) -> DataManagerHealth:
        """Get the health status of the Data Manager."""
        health = DataManagerHealth()

        try:
            # Test database connection via handler
            health.db_connected = self._document_handler.ping()

            # Get total datapoints count
            health.total_datapoints = self.datapoints.count_documents({})

            # Test storage accessibility
            try:
                if self._object_storage_handler is not None:
                    health.storage_accessible = self._object_storage_handler.ping()
                else:
                    # No object storage configured, but file storage should be accessible
                    storage_path = Path(self.settings.file_storage_path).expanduser()
                    storage_path.mkdir(parents=True, exist_ok=True)
                    health.storage_accessible = (
                        storage_path.exists() and storage_path.is_dir()
                    )
            except Exception:
                health.storage_accessible = False

            health.healthy = True
            health.description = "Data Manager is running normally"

        except Exception as e:
            health.healthy = False
            health.db_connected = False
            health.storage_accessible = False
            health.description = f"Database connection failed: {e!s}"

        return health

    def _upload_file_to_object_storage(
        self,
        file_path: Path,
        filename: str,
        datapoint_id: str,
        label: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Upload a file to object storage via the handler and return storage info."""
        if self._object_storage_handler is None:
            return None

        oss = self._object_storage_settings or ObjectStorageSettings()
        bucket_name = oss.default_bucket
        self._object_storage_handler.ensure_bucket(bucket_name)
        object_name = generate_object_name(
            label or filename,
            ObjectNamingStrategy.ULID_PREFIXED,
            ulid=datapoint_id,
        )
        result = self._object_storage_handler.upload_file(
            bucket=bucket_name,
            object_name=object_name,
            file_path=file_path,
            metadata=metadata,
        )

        # Add application-level fields expected by ObjectStorageDataPoint
        endpoint = oss.endpoint or ""
        public_endpoint = oss.public_endpoint or endpoint
        protocol = "https" if oss.secure else "http"
        result["storage_endpoint"] = endpoint
        result["public_endpoint"] = public_endpoint
        result["url"] = f"{protocol}://{public_endpoint}/{bucket_name}/{object_name}"

        return result

    @staticmethod
    def _cleanup_temp_file(path: Path) -> None:
        """Remove a temporary file (sync helper for async methods)."""
        path.unlink()

    @staticmethod
    def _get_storage_path(base_path: str, time: datetime) -> Path:
        """Resolve and create the date-based storage path (sync helper for async methods)."""
        path = (
            Path(base_path).expanduser()
            / str(time.year)
            / str(time.month)
            / str(time.day)
        )
        path.mkdir(parents=True, exist_ok=True)
        return path

    @post("/datapoint")
    async def create_datapoint(
        self, datapoint: Annotated[str, Form()], files: list[UploadFile] = []
    ) -> Any:
        """Create a new datapoint."""
        datapoint_obj = DataPoint.discriminate(json.loads(datapoint))

        with self.span(
            "data.save",
            attributes={
                "datapoint.type": str(datapoint_obj.data_type),
                "datapoint.label": datapoint_obj.label,
                "datapoint.has_files": bool(files),
            },
        ):
            # Handle file uploads if present
            if files:
                for file in files:
                    # Check if this is a file datapoint and object storage is configured
                    if (
                        datapoint_obj.data_type.value == "file"
                        and self._object_storage_handler is not None
                    ):
                        # Use object storage instead of local storage
                        # First, save file temporarily to upload to object storage

                        with tempfile.NamedTemporaryFile(
                            delete=False, suffix=f"_{file.filename}"
                        ) as temp_file:
                            contents = file.file.read()
                            temp_file.write(contents)
                            temp_file.flush()
                            temp_path = Path(temp_file.name)

                        # Upload to object storage
                        object_storage_info = self._upload_file_to_object_storage(
                            file_path=temp_path,
                            filename=file.filename,
                            datapoint_id=datapoint_obj.datapoint_id,
                            label=datapoint_obj.label,
                            metadata={
                                "original_datapoint_id": datapoint_obj.datapoint_id
                            },
                        )

                        # Clean up temporary file
                        self._cleanup_temp_file(temp_path)

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
                        # If object storage upload failed, fall back to local storage
                        warnings.warn(
                            "Object storage upload failed, falling back to local file storage",
                            UserWarning,
                            stacklevel=2,
                        )
                    # Fallback to local storage
                    time = datetime.now()
                    path = self._get_storage_path(self.settings.file_storage_path, time)
                    final_path = path / (
                        datapoint_obj.datapoint_id + "_" + file.filename
                    )

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
        with self.span("data.get", attributes={"datapoint.id": datapoint_id}):
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
        with self.span("data.value", attributes={"datapoint.id": datapoint_id}):
            datapoint = self.datapoints.find_one({"_id": datapoint_id})
            datapoint = DataPoint.discriminate(datapoint)
            if datapoint.data_type == "file":
                return FileResponse(datapoint.path)
            return JSONResponse(datapoint.value)

    @get("/datapoints")
    async def get_datapoints(self, number: int = 100) -> Dict[str, Any]:
        """Get the latest datapoints"""
        with self.span("data.list", attributes={"datapoint.limit": number}):
            datapoint_list = (
                self.datapoints.find({})
                .sort("data_timestamp", -1)
                .limit(number)
                .to_list()
            )
            return {
                datapoint["_id"]: DataPoint.discriminate(datapoint)
                for datapoint in datapoint_list
            }

    @post("/datapoints/query")
    async def query_datapoints(self, selector: Any = Body()) -> Dict[str, Any]:  # noqa: B008
        """Query datapoints based on a selector. Note: this is a raw query, so be careful."""
        with self.span("data.query"):
            datapoint_list = self.datapoints.find(selector).to_list()
            return {
                datapoint["_id"]: DataPoint.discriminate(datapoint)
                for datapoint in datapoint_list
            }


# Main entry point for running the server
if __name__ == "__main__":
    manager = DataManager()
    manager.run_server()
