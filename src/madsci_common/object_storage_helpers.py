"""Module to create and manage an object storage client using MinIO."""

import warnings

from madsci.common.types.datapoint_types import ObjectStorageDefinition


def create_minio_client(object_storage_config: ObjectStorageDefinition) -> None:
    """Initialize the object storage client using the provided configuration."""
    try:
        # Defer importing minio until needed
        from minio import Minio

        minio_client = Minio(
            endpoint=object_storage_config.endpoint,
            access_key=object_storage_config.access_key,
            secret_key=object_storage_config.secret_key,
            secure=object_storage_config.secure,
            region=object_storage_config.region
            if object_storage_config.region
            else None,
        )
        try:
            # Ensure the default bucket exists
            if not minio_client.bucket_exists(object_storage_config.default_bucket):
                minio_client.make_bucket(object_storage_config.default_bucket)
        except Exception as bucket_error:
            # Bucket creation failed - this is OK for many scenarios:
            # - AWS S3: User might not have CreateBucket permissions (bucket created via console)
            # - GCS: Bucket created via GCP console
            # - Bucket already exists but bucket_exists() failed due to permissions
            warnings.warn(
                f"Could not create bucket '{object_storage_config.default_bucket}': {bucket_error!s}. "
                f"Assuming bucket exists and continuing. If uploads fail, please ensure "
                f"the bucket exists and you have appropriate permissions.",
                UserWarning,
                stacklevel=2,
            )

    except Exception as e:
        warnings.warn(
            f"Failed to initialize object storage client: {e!s}",
            UserWarning,
            stacklevel=2,
        )
        minio_client = None
        return None
    else:
        return minio_client
