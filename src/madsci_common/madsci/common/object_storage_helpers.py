"""Module to create and manage an object storage client using MinIO."""

import mimetypes
import warnings
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional, Union

from madsci.common.types.datapoint_types import (
    ObjectStorageSettings,
)
from minio import Minio


class ObjectNamingStrategy(Enum):
    """Strategies for naming objects in storage."""

    FILENAME_ONLY = "filename_only"  # Just use the filename
    TIMESTAMPED_PATH = "timestamped_path"  # year/month/day/filename structure


def create_minio_client(
    object_storage_settings: Optional[ObjectStorageSettings] = None,
) -> Union[Minio, None]:
    """Initialize the object storage client using the provided configuration."""
    object_storage_settings = object_storage_settings or ObjectStorageSettings()
    if not object_storage_settings.endpoint:
        return None
    try:
        minio_client = Minio(
            endpoint=object_storage_settings.endpoint,
            access_key=object_storage_settings.access_key,
            secret_key=object_storage_settings.secret_key,
            secure=object_storage_settings.secure,
            region=object_storage_settings.region
            if object_storage_settings.region
            else None,
        )

        try:
            if not ensure_bucket_exists(
                minio_client, object_storage_settings.default_bucket
            ):
                minio_client.make_bucket(object_storage_settings.default_bucket)

        except Exception as bucket_error:
            # Bucket creation failed - this is OK for many scenarios:
            # - AWS S3: User might not have CreateBucket permissions (bucket created via console)
            # - GCS: Bucket created via GCP console
            # - Bucket already exists but bucket_exists() failed due to permissions
            warnings.warn(
                f"Could not create bucket '{object_storage_settings.default_bucket}': {bucket_error!s}. "
                f"Assuming bucket exists and continuing. If uploads fail, please ensure "
                f"the bucket exists and you have appropriate permissions.",
                UserWarning,
                stacklevel=2,
            )

        return minio_client

    except Exception as e:
        warnings.warn(
            f"Failed to initialize object storage client: {e!s}",
            UserWarning,
            stacklevel=2,
        )
        return None


def ensure_bucket_exists(minio_client: Minio, bucket_name: str) -> bool:
    """Ensure a bucket exists, creating it if necessary.

    Args:
        minio_client: The MinIO client instance
        bucket_name: Name of the bucket to check/create

    Returns:
        True if bucket exists or was created successfully, False otherwise
    """
    try:
        if not minio_client.bucket_exists(bucket_name):
            minio_client.make_bucket(bucket_name)
        return True

    except Exception as e:
        warnings.warn(
            f"Failed to check/create bucket '{bucket_name}': {e!s}",
            UserWarning,
            stacklevel=2,
        )
        return False


def get_content_type(file_path: Union[str, Path]) -> str:
    """Get the MIME content type for a file.

    Args:
        file_path: Path to the file

    Returns:
        MIME content type string
    """
    content_type, _ = mimetypes.guess_type(str(file_path))
    return content_type or "application/octet-stream"


def generate_object_name(
    filename: str,
    strategy: ObjectNamingStrategy = ObjectNamingStrategy.FILENAME_ONLY,
    prefix: Optional[str] = None,
) -> str:
    """Generate an object name using the specified strategy.

    Args:
        filename: The original filename
        strategy: Naming strategy to use
        prefix: Optional prefix to add to the object name

    Returns:
        Generated object name
    """
    if strategy == ObjectNamingStrategy.TIMESTAMPED_PATH:
        time = datetime.now()
        base_name = f"{time.year}/{time.month}/{time.day}/{filename}"
    else:  # FILENAME_ONLY
        base_name = filename

    if prefix:
        return f"{prefix}/{base_name}"
    return base_name


def construct_object_url(
    object_storage_settings: Optional[ObjectStorageSettings],
    bucket_name: str,
    object_name: str,
    public_endpoint: Optional[str] = None,
) -> str:
    """Construct a URL for accessing an object in storage.

    Args:
        object_storage_settings: Object storage configuration
        bucket_name: Name of the bucket
        object_name: Name of the object
        public_endpoint: Optional public endpoint override

    Returns:
        Complete URL to the object
    """
    object_storage_settings = object_storage_settings or ObjectStorageSettings()
    # Determine the appropriate endpoint for the URL
    if public_endpoint:
        endpoint_for_url = public_endpoint
    else:
        endpoint_for_url = object_storage_settings.endpoint
        # If this is a MinIO deployment, use port 9001 for web access instead of 9000
        if ":9000" in endpoint_for_url and (
            "localhost" in endpoint_for_url or "127.0.0.1" in endpoint_for_url
        ):
            # Only adjust for localhost/127.0.0.1 or if explicitly requested
            endpoint_for_url = endpoint_for_url.replace(":9000", ":9001")

    # Construct the object URL
    protocol = "https" if object_storage_settings.secure else "http"
    return f"{protocol}://{endpoint_for_url}/{bucket_name}/{object_name}"


def upload_file_to_object_storage(
    minio_client: Minio,
    file_path: Union[str, Path],
    bucket_name: Optional[str] = None,
    object_name: Optional[str] = None,
    content_type: Optional[str] = None,
    metadata: Optional[dict[str, str]] = None,
    naming_strategy: ObjectNamingStrategy = ObjectNamingStrategy.FILENAME_ONLY,
    public_endpoint: Optional[str] = None,
    label: Optional[str] = None,
    object_storage_settings: Optional[ObjectStorageSettings] = None,
) -> Optional[dict[str, Any]]:
    """Upload a file to object storage and return storage information.

    Args:
        minio_client: The MinIO client instance
        object_storage_settings: Object storage configuration
        file_path: Path to the file to upload
        bucket_name: Name of the bucket (defaults to config default_bucket)
        object_name: Name for the object (auto-generated if not provided)
        content_type: MIME type of the file (auto-detected if not provided)
        metadata: Additional metadata to attach to the object
        naming_strategy: Strategy for generating object names
        public_endpoint: Optional public endpoint for the object storage
        label: Label for the datapoint (defaults to filename)

    Returns:
        Dictionary with object storage information, or None if upload failed
    """
    if minio_client is None:
        warnings.warn(
            "MinIO client is not configured",
            UserWarning,
            stacklevel=2,
        )
        return None
    object_storage_settings = object_storage_settings or ObjectStorageSettings()

    # Convert to Path object and resolve
    file_path = Path(file_path).expanduser().resolve()

    if not file_path.exists():
        warnings.warn(
            f"File does not exist: {file_path}",
            UserWarning,
            stacklevel=2,
        )
        return None

    # Use defaults if not specified
    bucket_name = bucket_name or object_storage_settings.default_bucket
    object_name = object_name or generate_object_name(file_path.name, naming_strategy)
    content_type = content_type or get_content_type(file_path)
    label = label or file_path.name

    # Ensure the bucket exists
    if not ensure_bucket_exists(minio_client, bucket_name):
        return None

    # Upload the file
    try:
        result = minio_client.fput_object(
            bucket_name=bucket_name,
            object_name=object_name,
            file_path=str(file_path),
            content_type=content_type,
            metadata=metadata or {},
        )
    except Exception as e:
        warnings.warn(
            f"Failed to upload file to object storage: {e!s}",
            UserWarning,
            stacklevel=2,
        )
        return None

    # Get file size
    size_bytes = file_path.stat().st_size

    # Construct the object URL
    url = construct_object_url(
        object_storage_settings, bucket_name, object_name, public_endpoint
    )

    # Determine public endpoint for response
    final_public_endpoint = public_endpoint
    if not final_public_endpoint:
        final_public_endpoint = object_storage_settings.endpoint
        if ":9000" in final_public_endpoint and (
            "localhost" in final_public_endpoint or "127.0.0.1" in final_public_endpoint
        ):
            final_public_endpoint = final_public_endpoint.replace(":9000", ":9001")

    return {
        "bucket_name": bucket_name,
        "object_name": object_name,
        "storage_endpoint": object_storage_settings.endpoint,
        "public_endpoint": final_public_endpoint,
        "url": url,
        "label": label,
        "content_type": content_type,
        "size_bytes": size_bytes,
        "etag": result.etag,
        "custom_metadata": metadata or {},
    }


def download_file_from_object_storage(
    minio_client: Minio,
    bucket_name: str,
    object_name: str,
    output_path: Union[str, Path],
) -> bool:
    """Download a file from object storage.

    Args:
        minio_client: The MinIO client instance
        bucket_name: Name of the bucket
        object_name: Name of the object
        output_path: Path where the file should be saved

    Returns:
        True if download was successful, False otherwise
    """
    if minio_client is None:
        warnings.warn(
            "MinIO client is not configured",
            UserWarning,
            stacklevel=2,
        )
        return False

    try:
        output_path = Path(output_path).expanduser()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        minio_client.fget_object(
            bucket_name,
            object_name,
            str(output_path),
        )
        return True

    except Exception as e:
        warnings.warn(
            f"Failed to download from object storage: {e!s}",
            UserWarning,
            stacklevel=2,
        )
        return False


def get_object_data_from_storage(
    minio_client: Minio, bucket_name: str, object_name: str
) -> Optional[bytes]:
    """Get object data directly from storage.

    Args:
        minio_client: The MinIO client instance
        bucket_name: Name of the bucket
        object_name: Name of the object

    Returns:
        Object data as bytes, or None if retrieval failed
    """
    if minio_client is None:
        warnings.warn(
            "MinIO client is not configured",
            UserWarning,
            stacklevel=2,
        )
        return None

    try:
        response = minio_client.get_object(bucket_name, object_name)
        data = response.read()
        response.close()
        response.release_conn()
        return data

    except Exception as e:
        warnings.warn(
            f"Failed to get object from storage: {e!s}",
            UserWarning,
            stacklevel=2,
        )
        return None
