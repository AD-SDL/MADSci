Module madsci.common.object_storage_helpers
===========================================
Module to create and manage an object storage client using MinIO.

Functions
---------

`construct_object_url(object_storage_settings: madsci.common.types.datapoint_types.ObjectStorageSettings | None, bucket_name: str, object_name: str, public_endpoint: str | None = None) ‑> str`
:   Construct a URL for accessing an object in storage.

    Args:
        object_storage_settings: Object storage configuration
        bucket_name: Name of the bucket
        object_name: Name of the object
        public_endpoint: Optional public endpoint override

    Returns:
        Complete URL to the object

`create_minio_client(object_storage_settings: madsci.common.types.datapoint_types.ObjectStorageSettings | None = None) ‑> minio.api.Minio | None`
:   Initialize the object storage client using the provided configuration.

`download_file_from_object_storage(minio_client: minio.api.Minio, bucket_name: str, object_name: str, output_path: str | pathlib.Path) ‑> bool`
:   Download a file from object storage.

    Args:
        minio_client: The MinIO client instance
        bucket_name: Name of the bucket
        object_name: Name of the object
        output_path: Path where the file should be saved

    Returns:
        True if download was successful, False otherwise

`ensure_bucket_exists(minio_client: minio.api.Minio, bucket_name: str) ‑> bool`
:   Ensure a bucket exists, creating it if necessary.

    Args:
        minio_client: The MinIO client instance
        bucket_name: Name of the bucket to check/create

    Returns:
        True if bucket exists or was created successfully, False otherwise

`generate_object_name(filename: str, strategy: madsci.common.object_storage_helpers.ObjectNamingStrategy = ObjectNamingStrategy.FILENAME_ONLY, prefix: str | None = None) ‑> str`
:   Generate an object name using the specified strategy.

    Args:
        filename: The original filename
        strategy: Naming strategy to use
        prefix: Optional prefix to add to the object name

    Returns:
        Generated object name

`get_content_type(file_path: str | pathlib.Path) ‑> str`
:   Get the MIME content type for a file.

    Args:
        file_path: Path to the file

    Returns:
        MIME content type string

`get_object_data_from_storage(minio_client: minio.api.Minio, bucket_name: str, object_name: str) ‑> bytes | None`
:   Get object data directly from storage.

    Args:
        minio_client: The MinIO client instance
        bucket_name: Name of the bucket
        object_name: Name of the object

    Returns:
        Object data as bytes, or None if retrieval failed

`upload_file_to_object_storage(minio_client: minio.api.Minio, file_path: str | pathlib.Path, bucket_name: str | None = None, object_name: str | None = None, content_type: str | None = None, metadata: dict[str, str] | None = None, naming_strategy: madsci.common.object_storage_helpers.ObjectNamingStrategy = ObjectNamingStrategy.FILENAME_ONLY, public_endpoint: str | None = None, label: str | None = None, object_storage_settings: madsci.common.types.datapoint_types.ObjectStorageSettings | None = None) ‑> dict[str, typing.Any] | None`
:   Upload a file to object storage and return storage information.

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

Classes
-------

`ObjectNamingStrategy(*args, **kwds)`
:   Strategies for naming objects in storage.

    ### Ancestors (in MRO)

    * enum.Enum

    ### Class variables

    `FILENAME_ONLY`
    :

    `TIMESTAMPED_PATH`
    :
