Module madsci.common.types.datapoint_types
==========================================
Types related to datapoint types

Classes
-------

`DataManagerDefinition(**data: Any)`
:   Definition for a Squid Data Manager.

    Attributes:
        manager_type: The type of the event manager.
        host: The hostname or IP address of the Data Manager server.
        port: The port number of the Data Manager server.
        db_url: The URL of the database used by the Data Manager.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.manager_types.ManagerDefinition
    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `manager_id: str`
    :

    `manager_type: Literal[<ManagerType.DATA_MANAGER: 'data_manager'>]`
    :

    `model_config`
    :

    `name: str`
    :

`DataManagerHealth(**data: Any)`
:   Health status for Data Manager including database and storage connectivity.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.manager_types.ManagerHealth
    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `db_connected: bool | None`
    :

    `model_config`
    :

    `storage_accessible: bool | None`
    :

    `total_datapoints: int | None`
    :

`DataManagerSettings(**values: Any)`
:   Settings for the MADSci Data Manager.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.manager_types.ManagerSettings
    * madsci.common.types.base_types.MadsciBaseSettings
    * pydantic_settings.main.BaseSettings
    * pydantic.main.BaseModel

    ### Class variables

    `collection_name: str`
    :

    `database_name: str`
    :

    `file_storage_path: str | pathlib.Path`
    :

    `manager_definition: str | pathlib.Path`
    :

    `mongo_db_url: pydantic.networks.AnyUrl`
    :

    `server_url: pydantic.networks.AnyUrl`
    :

`DataPoint(**data: Any)`
:   An object to contain and locate data created during experiments.

    Attributes:
        label: The label of this data point.
        step_id: The step that generated the data point.
        workflow_id: The workflow that generated the data point.
        experiment_id: The experiment that generated the data point.
        campaign_id: The campaign of the data point.
        data_type: The type of the data point, inherited from class.
        datapoint_id: The specific ID for this data point.
        data_timestamp: The time the data point was created.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Descendants

    * madsci.common.types.datapoint_types.FileDataPoint
    * madsci.common.types.datapoint_types.ObjectStorageDataPoint
    * madsci.common.types.datapoint_types.ValueDataPoint

    ### Class variables

    `data_timestamp: datetime.datetime`
    :   time datapoint was created

    `data_type: madsci.common.types.datapoint_types.DataPointTypeEnum`
    :   type of the datapoint, inherited from class

    `datapoint_id: str`
    :   specific id for this data point

    `label: str | None`
    :   Label of this data point

    `model_config`
    :

    `ownership_info: madsci.common.types.auth_types.OwnershipInfo | None`
    :   Information about the ownership of the data point

    ### Static methods

    `discriminate(datapoint: DataPointDataModels) ‑> madsci.common.types.datapoint_types.FileDataPoint | madsci.common.types.datapoint_types.ValueDataPoint | madsci.common.types.datapoint_types.ObjectStorageDataPoint`
    :   Return the correct data point type based on the data_type attribute.

        Args:
            datapoint: The data point instance or dictionary to discriminate.

        Returns:
            The appropriate DataPoint subclass instance.

    `object_id_to_str(v: str | bson.objectid.ObjectId) ‑> str`
    :   Cast ObjectID to string.

`DataPointTypeEnum(*args, **kwds)`
:   Enumeration for the types of data points.

    Attributes:
        FILE: Represents a data point that contains a file.
        JSON: Represents a data point that contains a JSON serializable value.

    ### Ancestors (in MRO)

    * builtins.str
    * enum.Enum

    ### Class variables

    `FILE`
    :

    `JSON`
    :

    `OBJECT_STORAGE`
    :

`FileDataPoint(**data: Any)`
:   A data point containing a file.

    Attributes:
        data_type: The type of the data point, in this case a file.
        path: The path to the file.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.datapoint_types.DataPoint
    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `model_config`
    :

    `path: str | pathlib.Path`
    :   Path to the file

`ObjectStorageDataPoint(**data: Any)`
:   A data point that references an object in S3-compatible storage (MinIO/S3).

    This data point stores essential information about an object in S3-compatible
    storage without storing access credentials.

    Attributes:
        url: The accessible URL for the object (can be used in frontend).
        storage_endpoint: The endpoint of the storage service (e.g., 'minio.example.com:9000').
        bucket_name: The name of the bucket containing the object.
        object_name: The path/key of the object within the bucket.
        content_type: The MIME type of the stored object.
        size_bytes: The size of the object in bytes.
        etag: The entity tag (typically MD5) of the object.
        custom_metadata: Additional user-defined metadata for the object.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.datapoint_types.DataPoint
    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `bucket_name: str | None`
    :

    `content_type: str | None`
    :

    `custom_metadata: dict[str, str]`
    :

    `etag: str | None`
    :

    `model_config`
    :

    `object_name: str | None`
    :

    `path: str | pathlib.Path`
    :   Path to the file

    `public_endpoint: str | None`
    :

    `size_bytes: int | None`
    :

    `storage_endpoint: str`
    :

    `url: str | None`
    :

`ObjectStorageSettings(**values: Any)`
:   Settings for S3-compatible object storage.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseSettings
    * pydantic_settings.main.BaseSettings
    * pydantic.main.BaseModel

    ### Class variables

    `access_key: str`
    :

    `default_bucket: str`
    :

    `endpoint: str | None`
    :

    `region: str | None`
    :

    `secret_key: str`
    :

    `secure: bool`
    :

`ValueDataPoint(**data: Any)`
:   A data point corresponding to a single JSON serializable value.

    Attributes:
        data_type: The type of the data point, in this case a value.
        value: The value of the data point.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.datapoint_types.DataPoint
    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `model_config`
    :

    `value: Any`
    :   Value of the data point
