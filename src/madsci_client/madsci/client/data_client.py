"""Client for the MADSci Experiment Manager."""

import shutil
from json import JSONDecodeError
from pathlib import Path
from typing import Any, Optional, Union

from madsci.client.event_client import EventClient
from madsci.common.context import get_current_madsci_context
from madsci.common.object_storage_helpers import (
    ObjectNamingStrategy,
    create_minio_client,
    download_file_from_object_storage,
    get_object_data_from_storage,
    upload_file_to_object_storage,
)
from madsci.common.ownership import get_current_ownership_info
from madsci.common.types.client_types import DataClientConfig
from madsci.common.types.datapoint_types import (
    DataPoint,
    DataPointTypeEnum,
    ObjectStorageSettings,
)
from madsci.common.utils import create_http_session, extract_datapoint_ids
from madsci.common.warnings import MadsciLocalOnlyWarning
from pydantic import AnyUrl
from ulid import ULID


class DataClient:
    """Client for the MADSci Experiment Manager."""

    data_server_url: Optional[AnyUrl]
    _minio_client: Optional[ObjectStorageSettings] = None

    def __init__(
        self,
        data_server_url: Optional[Union[str, AnyUrl]] = None,
        object_storage_settings: Optional[ObjectStorageSettings] = None,
        config: Optional[DataClientConfig] = None,
    ) -> "DataClient":
        """
        Create a new Datapoint Client.

        Args:
            data_server_url: The base URL of the Data Manager. If not provided, it will be taken from the current MadsciContext.
            object_storage_settings: Configuration for object storage (e.g., MinIO). If not provided, defaults will be used.
            config: Client configuration for retry and timeout settings. If not provided, uses default DataClientConfig.
        """
        self.data_server_url = (
            AnyUrl(data_server_url)
            if data_server_url
            else get_current_madsci_context().data_server_url
        )
        self.logger = EventClient()
        if self.data_server_url is None:
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

        # Store config and create session
        self.config = config if config is not None else DataClientConfig()
        self.session = create_http_session(config=self.config)

    def get_datapoint(
        self, datapoint_id: Union[str, ULID], timeout: Optional[float] = None
    ) -> DataPoint:
        """Get a datapoint's metadata by ID, either from local storage or server.

        Args:
            datapoint_id: The ID of the datapoint to get.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        """
        if self.data_server_url is None:
            if datapoint_id in self._local_datapoints:
                return self._local_datapoints[datapoint_id]
            raise ValueError(f"Datapoint {datapoint_id} not found in local storage")

        response = self.session.get(
            f"{self.data_server_url}datapoint/{datapoint_id}",
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return DataPoint.discriminate(response.json())

    def get_datapoint_value(
        self, datapoint_id: Union[str, ULID], timeout: Optional[float] = None
    ) -> Any:
        """Get a datapoint value by ID. If the datapoint is JSON, returns the JSON data.
        Otherwise, returns the raw data as bytes.

        Args:
            datapoint_id: The ID of the datapoint to get.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_data_operations.
        """
        # First get the datapoint metadata
        datapoint = self.get_datapoint(datapoint_id, timeout=timeout)
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
        if self.data_server_url is not None:
            response = self.session.get(
                f"{self.data_server_url}datapoint/{datapoint_id}/value",
                timeout=timeout or self.config.timeout_data_operations,
            )
            response.raise_for_status()
            try:
                return response.json()
            except JSONDecodeError:
                return response.content

        raise ValueError(f"Could not get value for datapoint {datapoint_id}")

    def save_datapoint_value(
        self,
        datapoint_id: Union[str, ULID],
        output_filepath: str,
        timeout: Optional[float] = None,
    ) -> None:
        """Get an datapoint value by ID.

        Args:
            datapoint_id: The ID of the datapoint to save.
            output_filepath: Path where the datapoint value should be saved.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_data_operations.
        """
        output_filepath = Path(output_filepath).expanduser()
        output_filepath.parent.mkdir(parents=True, exist_ok=True)

        datapoint = self.get_datapoint(datapoint_id, timeout=timeout)
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

        if self.data_server_url is None:
            if self._local_datapoints[datapoint_id].data_type == "file":
                shutil.copyfile(
                    self._local_datapoints[datapoint_id].path, output_filepath
                )
            else:
                with Path(output_filepath).open("w") as f:
                    f.write(str(self._local_datapoints[datapoint_id].value))
            return

        response = self.session.get(
            f"{self.data_server_url}datapoint/{datapoint_id}/value",
            timeout=timeout or self.config.timeout_data_operations,
        )
        response.raise_for_status()
        try:
            with Path(output_filepath).open("w") as f:
                f.write(str(response.json()["value"]))

        except Exception:
            Path(output_filepath).expanduser().parent.mkdir(parents=True, exist_ok=True)
            with Path.open(output_filepath, "wb") as f:
                f.write(response.content)

    def get_datapoints(
        self, number: int = 10, timeout: Optional[float] = None
    ) -> list[DataPoint]:
        """Get a list of the latest datapoints.

        Args:
            number: Number of datapoints to retrieve.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        """
        if self.data_server_url is None:
            return list(self._local_datapoints.values()).sort(
                key=lambda x: x.datapoint_id, reverse=True
            )[:number]
        response = self.session.get(
            f"{self.data_server_url}datapoints",
            params={number: number},
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return [
            DataPoint.discriminate(datapoint) for datapoint in response.json().values()
        ]

    def query_datapoints(
        self, selector: Any, timeout: Optional[float] = None
    ) -> dict[str, DataPoint]:
        """Query datapoints based on a selector.

        Args:
            selector: Query selector for filtering datapoints.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        """
        if self.data_server_url is None:
            return {
                datapoint_id: datapoint
                for datapoint_id, datapoint in self._local_datapoints.items()
                if selector(datapoint)
            }
        response = self.session.post(
            f"{self.data_server_url}datapoints/query",
            json=selector,
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return {
            datapoint_id: DataPoint.discriminate(datapoint)
            for datapoint_id, datapoint in response.json().items()
        }

    def submit_datapoint(
        self, datapoint: DataPoint, timeout: Optional[float] = None
    ) -> DataPoint:
        """Submit a Datapoint object.

        If object storage is configured and the datapoint is a file type,
        the file will be automatically uploaded to object storage instead
        of being sent to the Data Manager server.

        Args:
            datapoint: The datapoint to submit.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_data_operations.

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
                    timeout=timeout,
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
                    timeout=timeout,
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
        if self.data_server_url is None:
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
        response = self.session.post(
            f"{self.data_server_url}datapoint",
            data={"datapoint": datapoint.model_dump_json()},
            files=files,
            timeout=timeout or self.config.timeout_data_operations,
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
        timeout: Optional[float] = None,
    ) -> DataPoint:
        """Internal method to upload a file to object storage and create a datapoint.

        Args:
            file_path: Path to the file to upload.
            object_name: Name to use for the object in storage (defaults to file basename).
            bucket_name: Name of the bucket (defaults to config default_bucket).
            content_type: MIME type of the file (auto-detected if not provided).
            metadata: Additional metadata to attach to the object.
            label: Label for the datapoint (defaults to file basename).
            public_endpoint: Optional public endpoint for the object storage.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_data_operations.

        Returns:
            A DataPoint referencing the uploaded file.

        Raises:
            ValueError: If object storage is not configured or operation fails.
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
        if self.data_server_url is not None:
            # Use a direct POST instead of recursively calling submit_datapoint
            response = self.session.post(
                f"{self.data_server_url}datapoint",
                data={"datapoint": datapoint.model_dump_json()},
                files={},
                timeout=timeout or self.config.timeout_data_operations,
            )
            response.raise_for_status()
            return DataPoint.discriminate(response.json())

        self._local_datapoints[datapoint.datapoint_id] = datapoint
        return datapoint

    def get_datapoints_by_ids(self, datapoint_ids: list[str]) -> dict[str, DataPoint]:
        """Fetch multiple datapoints by their IDs in a batch operation.

        This method enables just-in-time fetching of datapoints when only IDs are stored
        in workflows, following the principle of efficient datapoint management.

        Args:
            datapoint_ids: List of datapoint ULID strings to fetch

        Returns:
            Dictionary mapping datapoint IDs to DataPoint objects

        Raises:
            Exception: If any datapoint cannot be fetched
        """
        if not datapoint_ids:
            return {}

        result = {}
        for datapoint_id in datapoint_ids:
            try:
                datapoint = self.get_datapoint(datapoint_id)
                result[datapoint_id] = datapoint
            except Exception as e:
                # Log warning but continue with other datapoints
                self.logger.warn(f"Failed to fetch datapoint {datapoint_id}: {e}")

        return result

    def get_datapoint_metadata(self, datapoint_id: str) -> dict[str, Any]:
        """Get basic metadata for a datapoint without fetching the full data.

        Useful for UI display where you need labels, types, timestamps, etc.
        without loading large file contents or values.

        Args:
            datapoint_id: ULID string of the datapoint

        Returns:
            Dictionary with metadata fields like label, data_type, data_timestamp
        """
        datapoint = self.get_datapoint(datapoint_id)
        return {
            "datapoint_id": datapoint.datapoint_id,
            "label": getattr(datapoint, "label", None),
            "data_type": datapoint.data_type,
            "data_timestamp": getattr(datapoint, "data_timestamp", None),
            "ownership_info": getattr(datapoint, "ownership_info", None),
            # Add additional metadata fields based on datapoint type
            **(
                {"size_bytes": datapoint.size_bytes}
                if hasattr(datapoint, "size_bytes")
                else {}
            ),
            **(
                {"content_type": datapoint.content_type}
                if hasattr(datapoint, "content_type")
                else {}
            ),
        }

    def get_datapoints_metadata(
        self, datapoint_ids: list[str]
    ) -> dict[str, dict[str, Any]]:
        """Get metadata for multiple datapoints efficiently.

        Args:
            datapoint_ids: List of datapoint ULID strings

        Returns:
            Dictionary mapping datapoint IDs to metadata dictionaries
        """
        result = {}
        for datapoint_id in datapoint_ids:
            try:
                metadata = self.get_datapoint_metadata(datapoint_id)
                result[datapoint_id] = metadata
            except Exception as e:
                self.logger.warn(
                    f"Failed to fetch metadata for datapoint {datapoint_id}: {e}"
                )

        return result

    def extract_datapoint_ids_from_action_result(self, action_result: Any) -> list[str]:
        """Extract all datapoint IDs from an ActionResult.

        Args:
            action_result: ActionResult object to extract IDs from

        Returns:
            List of unique datapoint ULID strings
        """
        ids = []
        if hasattr(action_result, "datapoints") and action_result.datapoints:
            datapoint_dict = action_result.datapoints.model_dump(mode="json")
            ids.extend(extract_datapoint_ids(datapoint_dict))

        return list(set(ids))  # Remove duplicates
