"""REST Server for the MADSci Data Manager"""

import json
import mimetypes
import warnings
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, Optional

import uvicorn
from fastapi import FastAPI, Form, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.params import Body
from fastapi.responses import FileResponse, JSONResponse
from madsci.common.object_storage_helpers import create_minio_client
from madsci.common.types.datapoint_types import DataManagerDefinition, DataPoint
from pymongo import MongoClient


def create_data_server(  # noqa: C901, PLR0915
    data_manager_definition: Optional[DataManagerDefinition] = None,
    db_client: Optional[MongoClient] = None,
) -> FastAPI:
    """Creates a Data Manager's REST server."""

    data_manager_definition = (
        data_manager_definition or DataManagerDefinition.load_model()
    )
    if db_client is None:
        db_client = MongoClient(data_manager_definition.db_url)

    # Initialize MinIO client if configuration is provided
    minio_client = None
    if data_manager_definition.minio_client_config:
        minio_client = create_minio_client(data_manager_definition.minio_client_config)

    app = FastAPI()
    datapoints_db = db_client["madsci_data"]
    datapoints = datapoints_db["datapoints"]
    datapoints.create_index("datapoint_id", unique=True, background=True)

    @app.get("/")
    @app.get("/info")
    @app.get("/definition")
    async def root() -> DataManagerDefinition:
        """Return the DataPoint Manager Definition"""
        return data_manager_definition

    def _upload_file_to_minio(
        file_path: Path,
        filename: str,
        label: Optional[str] = None,
        metadata: Optional[dict[str, str]] = None,
    ) -> Optional[dict[str, Any]]:
        """Upload a file to MinIO object storage and return object storage info."""
        if minio_client is None:
            return None

        try:
            from minio.error import S3Error
        except ImportError:
            return None

        # Use default bucket from config
        bucket_name = data_manager_definition.minio_client_config.default_bucket

        # Create object name with timestamp and filename
        time = datetime.now()
        object_name = f"{time.year}/{time.month}/{time.day}/{filename}"

        # Auto-detect content type (file datapoints don't have content_type)
        content_type, _ = mimetypes.guess_type(str(file_path))
        content_type = content_type or "application/octet-stream"

        # Ensure the bucket exists
        try:
            if not minio_client.bucket_exists(bucket_name):
                minio_client.make_bucket(bucket_name)
        except S3Error as e:
            warnings.warn(
                f"Failed to check/create bucket: {e!s}",
                UserWarning,
                stacklevel=2,
            )
            return None

        # Upload the file
        try:
            result = minio_client.fput_object(
                bucket_name=bucket_name,
                object_name=object_name,
                file_path=str(file_path),
                content_type=content_type,
                metadata=metadata,
            )
        except S3Error as e:
            warnings.warn(
                f"Failed to upload file to object storage: {e!s}",
                UserWarning,
                stacklevel=2,
            )
            return None

        # Get file size
        size_bytes = file_path.stat().st_size

        # Determine the appropriate endpoint for the URL
        endpoint_for_url = data_manager_definition.minio_client_config.endpoint
        # If this is a MinIO deployment, use port 9001 for web access instead of 9000
        if ":9000" in endpoint_for_url and (
            "localhost" in endpoint_for_url or "127.0.0.1" in endpoint_for_url
        ):
            endpoint_for_url = endpoint_for_url.replace(":9000", ":9001")

        # Construct the object URL
        protocol = (
            "https" if data_manager_definition.minio_client_config.secure else "http"
        )
        url = f"{protocol}://{endpoint_for_url}/{bucket_name}/{object_name}"

        return {
            "bucket_name": bucket_name,
            "object_name": object_name,
            "storage_endpoint": data_manager_definition.minio_client_config.endpoint,
            "public_endpoint": endpoint_for_url,
            "url": url,
            "label": label or filename,
            "content_type": content_type,
            "size_bytes": size_bytes,
            "etag": result.etag,
            "custom_metadata": metadata or {},
        }

    @app.post("/datapoint")
    async def create_datapoint(
        datapoint: Annotated[str, Form()], files: list[UploadFile] = []
    ) -> Any:
        """Create a new datapoint."""
        data = json.loads(datapoint)
        datapoint_obj = DataPoint.discriminate(data)

        # Handle file uploads if present
        if files:
            for file in files:
                # Check if this is a file datapoint and MinIO is configured
                if (
                    datapoint_obj.data_type.value == "file"
                    and minio_client is not None
                    and data_manager_definition.minio_client_config
                ):
                    # Use MinIO object storage instead of local storage
                    # First, save file temporarily to upload to MinIO
                    import tempfile

                    with tempfile.NamedTemporaryFile(
                        delete=False, suffix=f"_{file.filename}"
                    ) as temp_file:
                        contents = file.file.read()
                        temp_file.write(contents)
                        temp_file.flush()
                        temp_path = Path(temp_file.name)

                    # Upload to MinIO object storage
                    object_storage_info = _upload_file_to_minio(
                        file_path=temp_path,
                        filename=file.filename,
                        label=datapoint_obj.label,
                        metadata={"original_datapoint_id": datapoint_obj.datapoint_id}
                        if hasattr(datapoint_obj, "datapoint_id")
                        else None,
                    )

                    # Clean up temporary file
                    temp_path.unlink()

                    # If upload was successful, store object storage information in database
                    if object_storage_info:
                        # Create a combined dictionary with both datapoint and object storage info
                        datapoint_dict = datapoint_obj.model_dump(mode="json")
                        datapoint_dict.update(object_storage_info)
                        # Update data_type to indicate this is now an object storage datapoint
                        datapoint_dict["data_type"] = "object_storage"
                        datapoints.insert_one(datapoint_dict)
                        # Return the transformed datapoint
                        return DataPoint.discriminate(datapoint_dict)
                    # If MinIO upload failed, fall back to local storage
                    warnings.warn(
                        "MinIO upload failed, falling back to local file storage",
                        UserWarning,
                        stacklevel=2,
                    )
                    # Use local storage fallback
                    time = datetime.now()
                    path = (
                        Path(data_manager_definition.file_storage_path).expanduser()
                        / str(time.year)
                        / str(time.month)
                        / str(time.day)
                    )
                    path.mkdir(parents=True, exist_ok=True)
                    final_path = path / (
                        datapoint_obj.datapoint_id + "_" + file.filename
                    )

                    # Reset file position and save locally
                    file.file.seek(0)
                    with Path.open(final_path, "wb") as f:
                        contents = file.file.read()
                        f.write(contents)
                    datapoint_obj.path = str(final_path)
                    datapoints.insert_one(datapoint_obj.model_dump(mode="json"))
                    return datapoint_obj

                # No MinIO config or not a file datapoint - use existing local storage logic
                time = datetime.now()
                path = (
                    Path(data_manager_definition.file_storage_path).expanduser()
                    / str(time.year)
                    / str(time.month)
                    / str(time.day)
                )
                path.mkdir(parents=True, exist_ok=True)
                final_path = path / (datapoint_obj.datapoint_id + "_" + file.filename)

                # Save file locally (existing functionality)
                with Path.open(final_path, "wb") as f:
                    contents = file.file.read()
                    f.write(contents)
                datapoint_obj.path = str(final_path)
                datapoints.insert_one(datapoint_obj.model_dump(mode="json"))
                return datapoint_obj
        else:
            # No files - just insert the datapoint (for ValueDataPoint, etc.)
            datapoints.insert_one(datapoint_obj.model_dump(mode="json"))
            return datapoint_obj
        return None

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

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

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
