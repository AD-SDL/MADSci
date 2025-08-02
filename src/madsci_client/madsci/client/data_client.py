"""Client for the MADSci Experiment Manager."""

import shutil
from json import JSONDecodeError
from pathlib import Path
from typing import Any, Optional, Union

import requests
from madsci.client.event_client import EventClient
from madsci.common.object_storage_helpers import (
    ObjectNamingStrategy,
    create_minio_client,
    download_file_from_object_storage,
    get_object_data_from_storage,
    upload_file_to_object_storage,
)
from madsci.common.ownership import get_current_ownership_info
from madsci.common.types.context_types import MadsciContext
from madsci.common.types.datapoint_types import (
    DataPoint,
    DataPointTypeEnum,
    ObjectStorageSettings,
)
from madsci.common.warnings import MadsciLocalOnlyWarning
from pydantic import AnyUrl
from ulid import ULID


class DataClient:
    """Client for the MADSci Experiment Manager."""

    url: AnyUrl
    context: MadsciContext
    _minio_client: Optional[ObjectStorageSettings] = None

    def __init__(
        self,
        url: Optional[Union[str, AnyUrl]] = None,
        object_storage_settings: Optional[ObjectStorageSettings] = None,
    ) -> "DataClient":
        """Create a new Datapoint Client."""
        self.context = MadsciContext(data_server_url=url) if url else MadsciContext()
        self.url = self.context.data_server_url
        self.logger = EventClient()
        if self.url is None:
            self.logger.warn(
                "No URL provided for the data client. Cannot persist datapoints.",
                warning_category=MadsciLocalOnlyWarning,
            )
        self._local_datapoints = {}
        self.object_storage_settings = (
            object_storage_settings or ObjectStorageSettings()
        )
        self._minio_client = create_minio_client(
            object_storage_settings=self.object_storage_settings
        )

    def get_datapoint(self, datapoint_id: Union[str, ULID]) -> DataPoint:
        """Get a datapoint's metadata by ID, either from local storage or server."""
        if self.url is None:
            if datapoint_id in self._local_datapoints:
                return self._local_datapoints[datapoint_id]
            raise ValueError(f"Datapoint {datapoint_id} not found in local storage")

        response = requests.get(f"{self.url}datapoint/{datapoint_id}", timeout=10)
        response.raise_for_status()
        return DataPoint.discriminate(response.json())

    def get_datapoint_value(self, datapoint_id: Union[str, ULID]) -> Any:
        """Get a datapoint value by ID. If the datapoint is JSON, returns the JSON data.
        Otherwise, returns the raw data as bytes."""
        # First get the datapoint metadata
        datapoint = self.get_datapoint(datapoint_id)
        # Handle based on datapoint type (regardless of URL configuration)
        if self._minio_client is not None:
            # Use MinIO client if configured
            if datapoint.data_type == DataPointTypeEnum.OBJECT_STORAGE:
                data = get_object_data_from_storage(
                    self._minio_client, datapoint.bucket_name, datapoint.object_name
                )
                if data is not None:
                    return data
                # Fall back to server API if object storage fails
            else:
                self.logger.warn(
                    "Cannot access object_storage datapoint: MinIO client not configured",
                )

        # Handle file datapoints
        elif datapoint.data_type == DataPointTypeEnum.FILE:
            if hasattr(datapoint, "path"):
                try:
                    with Path(datapoint.path).resolve().expanduser().open("rb") as f:
                        return f.read()
                except Exception as e:
                    self.logger.warn(
                        f"Failed to read file from path: {e!s}",
                    )

        # Handle value datapoints
        elif hasattr(datapoint, "value"):
            return datapoint.value

        # Fall back to server API if we have a URL
        if self.url is not None:
            response = requests.get(
                f"{self.url}datapoint/{datapoint_id}/value", timeout=10
            )
            response.raise_for_status()
            try:
                return response.json()
            except JSONDecodeError:
                return response.content

        raise ValueError(f"Could not get value for datapoint {datapoint_id}")

    def save_datapoint_value(
        self, datapoint_id: Union[str, ULID], output_filepath: str
    ) -> None:
        """Get an datapoint value by ID."""
        output_filepath = Path(output_filepath).expanduser()
        output_filepath.parent.mkdir(parents=True, exist_ok=True)

        datapoint = self.get_datapoint(datapoint_id)
        # Handle object storage datapoints specifically
        if (
            self._minio_client is not None
            and datapoint.data_type == DataPointTypeEnum.OBJECT_STORAGE
            and download_file_from_object_storage(
                self._minio_client,
                datapoint.bucket_name,
                datapoint.object_name,
                output_filepath,
            )
        ):
            return
            # If download failed, fall back to server API

        if self.url is None:
            if self._local_datapoints[datapoint_id].data_type == "file":
                shutil.copyfile(
                    self._local_datapoints[datapoint_id].path, output_filepath
                )
            else:
                with Path(output_filepath).open("w") as f:
                    f.write(str(self._local_datapoints[datapoint_id].value))
            return

        response = requests.get(f"{self.url}datapoint/{datapoint_id}/value", timeout=10)
        response.raise_for_status()
        try:
            with Path(output_filepath).open("w") as f:
                f.write(str(response.json()["value"]))

        except Exception:
            Path(output_filepath).expanduser().parent.mkdir(parents=True, exist_ok=True)
            with Path.open(output_filepath, "wb") as f:
                f.write(response.content)

    def get_datapoints(self, number: int = 10) -> list[DataPoint]:
        """Get a list of the latest datapoints."""
        if self.url is None:
            return list(self._local_datapoints.values()).sort(
                key=lambda x: x.datapoint_id, reverse=True
            )[:number]
        response = requests.get(
            f"{self.url}datapoints", params={number: number}, timeout=10
        )
        response.raise_for_status()
        return [
            DataPoint.discriminate(datapoint) for datapoint in response.json().values()
        ]

    def query_datapoints(self, selector: Any) -> dict[str, DataPoint]:
        """Query datapoints based on a selector."""
        if self.url is None:
            return {
                datapoint_id: datapoint
                for datapoint_id, datapoint in self._local_datapoints.items()
                if selector(datapoint)
            }
        response = requests.post(
            f"{self.url}datapoints/query", json=selector, timeout=10
        )
        response.raise_for_status()
        return {
            datapoint_id: DataPoint.discriminate(datapoint)
            for datapoint_id, datapoint in response.json().items()
        }

    def submit_datapoint(self, datapoint: DataPoint) -> DataPoint:
        """Submit a Datapoint object.

        If object storage is configured and the datapoint is a file type,
        the file will be automatically uploaded to object storage instead
        of being sent to the Data Manager server.

        Args:
            datapoint: The datapoint to submit

        Returns:
            The submitted datapoint with server-assigned IDs if applicable
        """
        # Case 1: Handle ObjectStorageDataPoint with path directly
        if (
            datapoint.data_type == DataPointTypeEnum.OBJECT_STORAGE
            and hasattr(datapoint, "path")
            and self._minio_client is not None
        ):
            try:
                # Use parameters from the datapoint itself
                return self._upload_to_object_storage(
                    file_path=datapoint.path,
                    public_endpoint=datapoint.public_endpoint,
                    label=datapoint.label,
                    object_name=getattr(datapoint, "object_name", None),
                    bucket_name=getattr(datapoint, "bucket_name", None),
                    metadata=getattr(datapoint, "custom_metadata", None),
                )
            except Exception as e:
                self.logger.warn(
                    f"Failed to upload ObjectStorageDataPoint: {e!s}",
                )
        # Case2: check if this is a file datapoint and object storage is configured
        if (
            datapoint.data_type == DataPointTypeEnum.FILE
            and self._minio_client is not None
        ):
            try:
                # Use the internal _upload_to_object_storage method
                object_datapoint = self._upload_to_object_storage(
                    file_path=datapoint.path,
                    label=datapoint.label,
                    metadata={"original_datapoint_id": datapoint.datapoint_id},
                )

                # If object storage upload was successful, return the result
                if object_datapoint is not None:
                    return object_datapoint
            except Exception as e:
                self.logger.warn(
                    f"Failed to upload to object storage, falling back: {e!s}",
                )
                # Fall back to regular submission if object storage fails

        # Handle regular submission (non-object storage or fallback)
        if self.url is None:
            # Store locally if no server URL is provided
            self._local_datapoints[datapoint.datapoint_id] = datapoint
            return datapoint

        if datapoint.data_type == DataPointTypeEnum.FILE:
            files = {
                (
                    "files",
                    (
                        str(Path(datapoint.path).name),
                        Path.open(Path(datapoint.path).expanduser(), "rb"),
                    ),
                )
            }
        else:
            files = {}
        response = requests.post(
            f"{self.url}datapoint",
            data={"datapoint": datapoint.model_dump_json()},
            files=files,
            timeout=10,
        )
        response.raise_for_status()
        return DataPoint.discriminate(response.json())

    def _upload_to_object_storage(
        self,
        file_path: Union[str, Path],
        object_name: Optional[str] = None,
        bucket_name: Optional[str] = None,
        content_type: Optional[str] = None,
        metadata: Optional[dict[str, str]] = None,
        label: Optional[str] = None,
        public_endpoint: Optional[str] = None,
    ) -> DataPoint:
        """Internal method to upload a file to object storage and create a datapoint.

        Args:
            file_path: Path to the file to upload
            object_name: Name to use for the object in storage (defaults to file basename)
            bucket_name: Name of the bucket (defaults to config default_bucket)
            content_type: MIME type of the file (auto-detected if not provided)
            metadata: Additional metadata to attach to the object
            label: Label for the datapoint (defaults to file basename)
            public_endpoint: Optional public endpoint for the object storage

        Returns:
            A DataPoint referencing the uploaded file

        Raises:
            ValueError: If object storage is not configured or operation fails
        """
        if self._minio_client is None:
            raise ValueError("Object storage is not configured.")

        # Use the helper function to upload the file
        object_storage_info = upload_file_to_object_storage(
            minio_client=self._minio_client,
            object_storage_settings=self.object_storage_settings,
            file_path=file_path,
            bucket_name=bucket_name,
            object_name=object_name,
            content_type=content_type,
            metadata=metadata,
            naming_strategy=ObjectNamingStrategy.FILENAME_ONLY,  # Client uses simple naming
            public_endpoint=public_endpoint,
            label=label,
        )

        if object_storage_info is None:
            raise ValueError("Failed to upload file to object storage")

        # Create the datapoint dictionary
        datapoint_dict = {
            "data_type": "object_storage",
            "path": str(Path(file_path).expanduser().resolve()),
            "ownership_info": get_current_ownership_info().model_dump(mode="json"),
            **object_storage_info,  # Unpack all the storage info
        }

        # Use discriminate to get the proper datapoint type
        datapoint = DataPoint.discriminate(datapoint_dict)

        # Submit the datapoint to the Data Manager (metadata only)
        if self.url is not None:
            # Use a direct POST instead of recursively calling submit_datapoint
            response = requests.post(
                f"{self.url}datapoint",
                data={"datapoint": datapoint.model_dump_json()},
                files={},
                timeout=10,
            )
            response.raise_for_status()
            return DataPoint.discriminate(response.json())

        self._local_datapoints[datapoint.datapoint_id] = datapoint
        return datapoint
