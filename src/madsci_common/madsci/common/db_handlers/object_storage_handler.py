"""S3-compatible object storage handler abstraction.

Provides an ABC for object storage access and two implementations:
- RealObjectStorageHandler: wraps a real Minio client for S3-compatible storage (MinIO, SeaweedFS, etc.)
- InMemoryObjectStorageHandler: stores objects in-memory for testing
"""

from __future__ import annotations

import mimetypes
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional, Union


class ObjectStorageHandler(ABC):
    """Abstract interface for S3-compatible object storage access.

    Managers use this interface instead of directly depending on
    ``minio.Minio``, enabling in-memory substitution for tests.
    """

    @abstractmethod
    def upload_file(
        self,
        bucket: str,
        object_name: str,
        file_path: Union[str, Path],
        content_type: Optional[str] = None,
        metadata: Optional[dict[str, str]] = None,
    ) -> dict[str, Any]:
        """Upload a file to object storage.

        Args:
            bucket: Bucket name.
            object_name: Name/key for the object.
            file_path: Local file path to upload.
            content_type: MIME type (auto-detected if not provided).
            metadata: Additional metadata to attach.

        Returns:
            Dictionary with storage information including bucket_name,
            object_name, etag, size_bytes, and content_type.
        """

    @abstractmethod
    def download_file(
        self,
        bucket: str,
        object_name: str,
        output_path: Union[str, Path],
    ) -> None:
        """Download an object to a local file.

        Args:
            bucket: Bucket name.
            object_name: Name/key of the object.
            output_path: Local path to write the file to.
        """

    @abstractmethod
    def get_object_data(self, bucket: str, object_name: str) -> bytes:
        """Get object contents as bytes.

        Args:
            bucket: Bucket name.
            object_name: Name/key of the object.

        Returns:
            The object contents as bytes.
        """

    @abstractmethod
    def bucket_exists(self, bucket: str) -> bool:
        """Check if a bucket exists.

        Args:
            bucket: Bucket name.

        Returns:
            True if the bucket exists.
        """

    @abstractmethod
    def make_bucket(self, bucket: str) -> None:
        """Create a bucket.

        Args:
            bucket: Bucket name to create.
        """

    @abstractmethod
    def list_buckets(self) -> list[str]:
        """Return names of all buckets."""

    @abstractmethod
    def ping(self) -> bool:
        """Check connectivity to the object storage service.

        Returns:
            True if the service is reachable, False otherwise.
        """

    @abstractmethod
    def close(self) -> None:
        """Release any connections or resources."""

    def ensure_bucket(self, bucket: str) -> None:
        """Ensure a bucket exists, creating it if necessary."""
        if not self.bucket_exists(bucket):
            self.make_bucket(bucket)


class RealObjectStorageHandler(ObjectStorageHandler):
    """Object storage handler backed by a real S3-compatible server (MinIO, SeaweedFS, etc.).

    Usage::

        handler = RealObjectStorageHandler.from_settings(object_storage_settings)
        handler.upload_file("my-bucket", "data.csv", "/path/to/data.csv")
    """

    def __init__(self, client: Any) -> None:
        """Initialize with an existing Minio client.

        Args:
            client: A ``minio.Minio`` instance.
        """
        self._client = client

    @classmethod
    def from_settings(cls, settings: Any) -> RealObjectStorageHandler:
        """Create a handler from ObjectStorageSettings.

        Args:
            settings: An ``ObjectStorageSettings`` instance with endpoint,
                access_key, secret_key, secure, and region fields.

        Returns:
            A new RealObjectStorageHandler instance.
        """
        from minio import Minio  # noqa: PLC0415

        client = Minio(
            endpoint=settings.endpoint,
            access_key=settings.access_key,
            secret_key=settings.secret_key,
            secure=settings.secure,
            region=settings.region or None,
        )
        return cls(client)

    def upload_file(
        self,
        bucket: str,
        object_name: str,
        file_path: Union[str, Path],
        content_type: Optional[str] = None,
        metadata: Optional[dict[str, str]] = None,
    ) -> dict[str, Any]:
        """Upload a file to S3-compatible object storage."""
        file_path = Path(file_path).expanduser().resolve()
        content_type = content_type or _guess_content_type(file_path)

        result = self._client.fput_object(
            bucket_name=bucket,
            object_name=object_name,
            file_path=str(file_path),
            content_type=content_type,
            metadata=metadata or {},
        )

        size_bytes = file_path.stat().st_size

        return {
            "bucket_name": bucket,
            "object_name": object_name,
            "etag": result.etag,
            "size_bytes": size_bytes,
            "content_type": content_type,
        }

    def download_file(
        self,
        bucket: str,
        object_name: str,
        output_path: Union[str, Path],
    ) -> None:
        """Download an object from S3-compatible object storage."""
        output_path = Path(output_path).expanduser()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self._client.fget_object(bucket, object_name, str(output_path))

    def get_object_data(self, bucket: str, object_name: str) -> bytes:
        """Get object contents from S3-compatible object storage."""
        response = self._client.get_object(bucket, object_name)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def bucket_exists(self, bucket: str) -> bool:
        """Check if a bucket exists in object storage."""
        return self._client.bucket_exists(bucket)

    def make_bucket(self, bucket: str) -> None:
        """Create a bucket in object storage."""
        self._client.make_bucket(bucket)

    def list_buckets(self) -> list[str]:
        """Return names of all buckets."""
        return [b.name for b in self._client.list_buckets()]

    def ping(self) -> bool:
        """Check connectivity by listing buckets."""
        try:
            self._client.list_buckets()
            return True
        except Exception:
            return False

    def close(self) -> None:
        """No-op for S3 client (uses HTTP, no persistent connection)."""


class InMemoryObjectStorageHandler(ObjectStorageHandler):
    """Object storage handler backed by in-memory storage for testing.

    Stores files as bytes in a dictionary keyed by ``(bucket, object_name)``.

    Usage::

        handler = InMemoryObjectStorageHandler()
        handler.make_bucket("test-bucket")
        handler.upload_file("test-bucket", "data.csv", "/path/to/data.csv")
        data = handler.get_object_data("test-bucket", "data.csv")
    """

    def __init__(self) -> None:
        """Initialize with empty in-memory storage."""
        self._objects: dict[tuple[str, str], bytes] = {}
        self._metadata: dict[tuple[str, str], dict[str, Any]] = {}
        self._buckets: set[str] = set()

    def upload_file(
        self,
        bucket: str,
        object_name: str,
        file_path: Union[str, Path],
        content_type: Optional[str] = None,
        metadata: Optional[dict[str, str]] = None,
    ) -> dict[str, Any]:
        """Upload a file to in-memory storage."""
        file_path = Path(file_path).expanduser().resolve()
        content_type = content_type or _guess_content_type(file_path)
        data = file_path.read_bytes()
        size_bytes = len(data)

        key = (bucket, object_name)
        self._objects[key] = data
        self._metadata[key] = {
            "content_type": content_type,
            "custom_metadata": metadata or {},
        }
        self._buckets.add(bucket)

        return {
            "bucket_name": bucket,
            "object_name": object_name,
            "etag": f"inmemory-{hash(data) & 0xFFFFFFFF:08x}",
            "size_bytes": size_bytes,
            "content_type": content_type,
        }

    def download_file(
        self,
        bucket: str,
        object_name: str,
        output_path: Union[str, Path],
    ) -> None:
        """Download an object from in-memory storage to a local file."""
        key = (bucket, object_name)
        if key not in self._objects:
            raise FileNotFoundError(
                f"Object not found: bucket={bucket}, object_name={object_name}"
            )
        output_path = Path(output_path).expanduser()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(self._objects[key])

    def get_object_data(self, bucket: str, object_name: str) -> bytes:
        """Get object contents from in-memory storage."""
        key = (bucket, object_name)
        if key not in self._objects:
            raise FileNotFoundError(
                f"Object not found: bucket={bucket}, object_name={object_name}"
            )
        return self._objects[key]

    def bucket_exists(self, bucket: str) -> bool:
        """Check if a bucket exists in in-memory storage."""
        return bucket in self._buckets

    def make_bucket(self, bucket: str) -> None:
        """Create a bucket in in-memory storage."""
        self._buckets.add(bucket)

    def list_buckets(self) -> list[str]:
        """Return names of all buckets."""
        return sorted(self._buckets)

    def ping(self) -> bool:
        """Always returns True for in-memory storage."""
        return True

    def close(self) -> None:
        """No-op for in-memory storage."""


def _guess_content_type(file_path: Path) -> str:
    """Guess the MIME content type for a file."""
    content_type, _ = mimetypes.guess_type(str(file_path))
    return content_type or "application/octet-stream"
