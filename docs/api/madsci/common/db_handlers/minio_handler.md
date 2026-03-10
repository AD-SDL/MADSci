Module madsci.common.db_handlers.minio_handler
==============================================
MinIO/object storage handler abstraction.

Provides an ABC for object storage access and two implementations:
- RealMinioHandler: wraps a real Minio client
- InMemoryMinioHandler: stores objects in-memory for testing

Classes
-------

`InMemoryMinioHandler()`
:   Object storage handler backed by in-memory storage for testing.
    
    Stores files as bytes in a dictionary keyed by ``(bucket, object_name)``.
    
    Usage::
    
        handler = InMemoryMinioHandler()
        handler.make_bucket("test-bucket")
        handler.upload_file("test-bucket", "data.csv", "/path/to/data.csv")
        data = handler.get_object_data("test-bucket", "data.csv")
    
    Initialize with empty in-memory storage.

    ### Ancestors (in MRO)

    * madsci.common.db_handlers.minio_handler.MinioHandler
    * abc.ABC

    ### Methods

    `bucket_exists(self, bucket: str) ‑> bool`
    :   Check if a bucket exists in in-memory storage.

    `close(self) ‑> None`
    :   No-op for in-memory storage.

    `download_file(self, bucket: str, object_name: str, output_path: Union[str, Path]) ‑> None`
    :   Download an object from in-memory storage to a local file.

    `get_object_data(self, bucket: str, object_name: str) ‑> bytes`
    :   Get object contents from in-memory storage.

    `make_bucket(self, bucket: str) ‑> None`
    :   Create a bucket in in-memory storage.

    `ping(self) ‑> bool`
    :   Always returns True for in-memory storage.

    `upload_file(self, bucket: str, object_name: str, file_path: Union[str, Path], content_type: Optional[str] = None, metadata: Optional[dict[str, str]] = None) ‑> dict[str, typing.Any]`
    :   Upload a file to in-memory storage.

`MinioHandler()`
:   Abstract interface for object storage access.
    
    Managers use this interface instead of directly depending on
    ``minio.Minio``, enabling in-memory substitution for tests.

    ### Ancestors (in MRO)

    * abc.ABC

    ### Descendants

    * madsci.common.db_handlers.minio_handler.InMemoryMinioHandler
    * madsci.common.db_handlers.minio_handler.RealMinioHandler

    ### Methods

    `bucket_exists(self, bucket: str) ‑> bool`
    :   Check if a bucket exists.
        
        Args:
            bucket: Bucket name.
        
        Returns:
            True if the bucket exists.

    `close(self) ‑> None`
    :   Release any connections or resources.

    `download_file(self, bucket: str, object_name: str, output_path: Union[str, Path]) ‑> None`
    :   Download an object to a local file.
        
        Args:
            bucket: Bucket name.
            object_name: Name/key of the object.
            output_path: Local path to write the file to.

    `ensure_bucket(self, bucket: str) ‑> None`
    :   Ensure a bucket exists, creating it if necessary.

    `get_object_data(self, bucket: str, object_name: str) ‑> bytes`
    :   Get object contents as bytes.
        
        Args:
            bucket: Bucket name.
            object_name: Name/key of the object.
        
        Returns:
            The object contents as bytes.

    `list_buckets(self) ‑> list[str]`
    :   Return names of all buckets.

    `make_bucket(self, bucket: str) ‑> None`
    :   Create a bucket.
        
        Args:
            bucket: Bucket name to create.

    `ping(self) ‑> bool`
    :   Check connectivity to the object storage service.
        
        Returns:
            True if the service is reachable, False otherwise.

    `upload_file(self, bucket: str, object_name: str, file_path: Union[str, Path], content_type: Optional[str] = None, metadata: Optional[dict[str, str]] = None) ‑> dict[str, typing.Any]`
    :   Upload a file to object storage.
        
        Args:
            bucket: Bucket name.
            object_name: Name/key for the object.
            file_path: Local file path to upload.
            content_type: MIME type (auto-detected if not provided).
            metadata: Additional metadata to attach.
        
        Returns:
            Dictionary with storage information including bucket_name,
            object_name, etag, size_bytes, and content_type.

`RealMinioHandler(client: Any)`
:   Object storage handler backed by a real MinIO/S3 server.
    
    Usage::
    
        handler = RealMinioHandler.from_settings(object_storage_settings)
        handler.upload_file("my-bucket", "data.csv", "/path/to/data.csv")
    
    Initialize with an existing Minio client.
    
    Args:
        client: A ``minio.Minio`` instance.

    ### Ancestors (in MRO)

    * madsci.common.db_handlers.minio_handler.MinioHandler
    * abc.ABC

    ### Static methods

    `from_settings(settings: Any) ‑> madsci.common.db_handlers.minio_handler.RealMinioHandler`
    :   Create a handler from ObjectStorageSettings.
        
        Args:
            settings: An ``ObjectStorageSettings`` instance with endpoint,
                access_key, secret_key, secure, and region fields.
        
        Returns:
            A new RealMinioHandler instance.

    ### Methods

    `bucket_exists(self, bucket: str) ‑> bool`
    :   Check if a bucket exists in MinIO.

    `close(self) ‑> None`
    :   No-op for MinIO client (uses HTTP, no persistent connection).

    `download_file(self, bucket: str, object_name: str, output_path: Union[str, Path]) ‑> None`
    :   Download an object from MinIO.

    `get_object_data(self, bucket: str, object_name: str) ‑> bytes`
    :   Get object contents from MinIO.

    `make_bucket(self, bucket: str) ‑> None`
    :   Create a bucket in MinIO.

    `ping(self) ‑> bool`
    :   Check connectivity by listing buckets.

    `upload_file(self, bucket: str, object_name: str, file_path: Union[str, Path], content_type: Optional[str] = None, metadata: Optional[dict[str, str]] = None) ‑> dict[str, typing.Any]`
    :   Upload a file to MinIO.