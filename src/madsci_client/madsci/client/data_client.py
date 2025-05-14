"""Client for the MADSci Experiment Manager."""

import mimetypes
import warnings
from json import JSONDecodeError
from pathlib import Path
from typing import Any, Optional, Union

import requests
from madsci.common.types.auth_types import OwnershipInfo
from madsci.common.types.datapoint_types import DataPoint, ObjectStorageDefinition
from pydantic import AnyUrl
from ulid import ULID


class DataClient:
    """Client for the MADSci Experiment Manager."""

    url: AnyUrl

    def __init__(
        self,
        url: Optional[Union[str, AnyUrl]] = None,
        ownership_info: Optional[OwnershipInfo] = None,
        object_storage_config: Optional[ObjectStorageDefinition] = None,
    ) -> "DataClient":
        """Create a new Datapoint Client."""
        self.url = AnyUrl(url) if url is not None else None
        if self.url is None:
            warnings.warn(
                "No URL provided for the data client. Cannot persist datapoints.",
                UserWarning,
                stacklevel=2,
            )
        self._local_datapoints = {}
        self.ownership_info = ownership_info if ownership_info else OwnershipInfo()
        self.object_storage_config = object_storage_config
        self._minio_client = None

        if object_storage_config:
            self._init_object_storage()

    def _init_object_storage(self) -> None:
        """Initialize the object storage client using the provided configuration."""
        try:
            # Defer importing minio until needed
            from minio import Minio

            self._minio_client = Minio(
                endpoint=self.object_storage_config.endpoint,
                access_key=self.object_storage_config.access_key,
                secret_key=self.object_storage_config.secret_key,
                secure=self.object_storage_config.secure,
            )

            # Ensure the default bucket exists
            if not self._minio_client.bucket_exists(
                self.object_storage_config.default_bucket
            ):
                self._minio_client.make_bucket(
                    self.object_storage_config.default_bucket
                )

        except Exception as e:
            warnings.warn(
                f"Failed to initialize object storage client: {e!s}",
                UserWarning,
                stacklevel=2,
            )
            self._minio_client = None

    def get_datapoint(self, datapoint_id: Union[str, ULID]) -> dict:
        """Get an datapoint by ID."""
        if self.url is None:
            return self._local_datapoints[datapoint_id]
        response = requests.get(f"{self.url}datapoint/{datapoint_id}", timeout=10)
        response.raise_for_status()
        return DataPoint.discriminate(response.json())

    def get_datapoint_value(self, datapoint_id: Union[str, ULID]) -> Any:
        """Get an datapoint value by ID. If the datapoint is JSON, returns the JSON data.
        Otherwise, returns the raw data as bytes."""
        if self.url is None:
            datapoint = self._local_datapoints[datapoint_id]
            if hasattr(datapoint, "value"):
                return datapoint.value
            if hasattr(datapoint, "path"):
                with Path(datapoint.path).resolve().expanduser().open("rb") as f:
                    return f.read()
            # Handle ObjectStorageDataPoint locally if MinIO client is available
            if (
                hasattr(datapoint, "data_type")
                and datapoint.data_type == "object_storage"
                and self._minio_client is not None
            ):
                try:
                    response = self._minio_client.get_object(
                        datapoint.bucket_name, datapoint.object_name
                    )
                    data = response.read()
                    response.close()
                    response.release_conn()
                    return data
                except Exception as e:
                    warnings.warn(
                        f"Failed to get object from storage, falling back to URL: {e!s}",
                        UserWarning,
                        stacklevel=2,
                    )
                    # Fall back to URL if direct access fails
                    response = requests.get(datapoint.url, timeout=10)
                    response.raise_for_status()
                    return response.content

        response = requests.get(f"{self.url}datapoint/{datapoint_id}/value", timeout=10)
        response.raise_for_status()
        try:
            return response.json()
        except JSONDecodeError:
            return response.content

    def save_datapoint_value(
        self, datapoint_id: Union[str, ULID], output_filepath: str
    ) -> None:
        """Get an datapoint value by ID."""
        output_filepath = Path(output_filepath).expanduser()
        if self.url is None:
            if self._local_datapoints[datapoint_id].data_type == "file":
                import shutil

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
        return [DataPoint.discriminate(datapoint) for datapoint in response.json()]

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

        if self.url is None:
            self._local_datapoints[datapoint.datapoint_id] = datapoint
            return datapoint

        # If this is a file datapoint and object storage is configured, use object storage
        if datapoint.data_type == "file" and self._minio_client is not None:
            try:
                # Use the internal _upload_to_object_storage method with the file path
                object_datapoint = self._upload_to_object_storage(
                    file_path=datapoint.path,
                    label=datapoint.label,
                    metadata={"original_datapoint_id": datapoint.datapoint_id}
                    if hasattr(datapoint, "datapoint_id")
                    else None,
                )

                # If successful, return the object storage datapoint
                if object_datapoint is not None:
                    return object_datapoint

            except Exception as e:
                warnings.warn(
                    f"Failed to upload to object storage, falling back to regular file upload: {e!s}",
                    UserWarning,
                    stacklevel=2,
                )
                # Fall back to regular file upload if object storage fails

        if datapoint.data_type == "file":
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

    def _upload_to_object_storage(
        self,
        file_path: Union[str, Path],
        object_name: Optional[str] = None,
        bucket_name: Optional[str] = None,
        content_type: Optional[str] = None,
        metadata: Optional[dict[str, str]] = None,
        label: Optional[str] = None,
    ) -> DataPoint:
        """Internal method to upload a file to object storage and create a datapoint.

        Args:
            file_path: Path to the file to upload
            object_name: Name to use for the object in storage (defaults to file basename)
            bucket_name: Name of the bucket (defaults to config default_bucket)
            content_type: MIME type of the file (auto-detected if not provided)
            metadata: Additional metadata to attach to the object
            label: Label for the datapoint (defaults to file basename)

        Returns:
            A DataPoint referencing the uploaded file

        Raises:
            ValueError: If object storage is not configured or operation fails
        """
        if self._minio_client is None:
            raise ValueError(
                "Object storage is not configured. Initialize DataClient with object_storage_config."
            )

        # Import minio modules only when needed
        from minio.error import S3Error

        # Convert to Path object and resolve
        file_path = Path(file_path).expanduser().resolve()

        # Use defaults if not specified
        object_name = object_name or file_path.name
        bucket_name = bucket_name or self.object_storage_config.default_bucket
        label = label or file_path.name

        # Auto-detect content type if not provided
        if content_type is None:
            content_type, _ = mimetypes.guess_type(str(file_path))
            content_type = content_type or "application/octet-stream"

        # Ensure the bucket exists
        try:
            if not self._minio_client.bucket_exists(bucket_name):
                self._minio_client.make_bucket(bucket_name)
        except S3Error as e:
            warnings.warn(
                f"Failed to check/create bucket: {e!s}",
                UserWarning,
                stacklevel=2,
            )
            return None
        # Upload the file
        try:
            result = self._minio_client.fput_object(
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

        # Construct the object URL
        protocol = "https" if self.object_storage_config.secure else "http"
        url = f"{protocol}://{self.object_storage_config.endpoint}/{bucket_name}/{object_name}"

        # Create the datapoint dictionary
        datapoint_dict = {
            "data_type": "object_storage",
            "label": label,
            "url": url,
            "bucket_name": bucket_name,
            "object_name": object_name,
            "storage_endpoint": self.object_storage_config.endpoint,
            "content_type": content_type,
            "size_bytes": size_bytes,
            "etag": result.etag,
            "custom_metadata": metadata or {},
            "ownership_info": self.ownership_info.model_dump()
            if self.ownership_info
            else {},
        }

        # Use discriminate to get the proper datapoint type
        datapoint = DataPoint.discriminate(datapoint_dict)

        # Submit the datapoint to the Data Manager (metadata only)
        if self.url is not None:
            # Use a direct POST instead of recursively calling submit_datapoint
            response = requests.post(
                f"{self.url}datapoint",
                json={"datapoint": datapoint.model_dump_json()},
                timeout=10,
            )
            response.raise_for_status()
            return DataPoint.discriminate(response.json())
        self._local_datapoints[datapoint.datapoint_id] = datapoint
        return datapoint
