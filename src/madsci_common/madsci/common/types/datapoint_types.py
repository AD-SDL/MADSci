"""Types related to datapoint types"""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Annotated, Any, Literal, Optional, Union

from bson.objectid import ObjectId
from madsci.common.ownership import get_current_ownership_info
from madsci.common.types.auth_types import OwnershipInfo
from madsci.common.types.base_types import MadsciBaseModel, MadsciBaseSettings, PathLike
from madsci.common.types.lab_types import ManagerDefinition, ManagerType
from madsci.common.utils import new_ulid_str
from pydantic import (
    AliasChoices,
    AnyUrl,
    Field,
    Tag,
    field_validator,
)
from pydantic.types import Discriminator


class DataPointTypeEnum(str, Enum):
    """Enumeration for the types of data points.

    Attributes:
        FILE: Represents a data point that contains a file.
        DATA_VALUE: Represents a data point that contains a JSON serializable value.
    """

    FILE = "file"
    DATA_VALUE = "data_value"
    OBJECT_STORAGE = "object_storage"


class DataPoint(MadsciBaseModel, extra="allow"):
    """An object to contain and locate data created during experiments.

    Attributes:
        label: The label of this data point.
        step_id: The step that generated the data point.
        workflow_id: The workflow that generated the data point.
        experiment_id: The experiment that generated the data point.
        campaign_id: The campaign of the data point.
        data_type: The type of the data point, inherited from class.
        datapoint_id: The specific ID for this data point.
        data_timestamp: The time the data point was created.
    """

    label: str
    """Label of this data point"""
    ownership_info: Optional[OwnershipInfo] = Field(
        default_factory=get_current_ownership_info
    )
    """Information about the ownership of the data point"""
    data_type: DataPointTypeEnum
    """type of the datapoint, inherited from class"""
    datapoint_id: str = Field(
        default_factory=new_ulid_str,
        serialization_alias="_id",
        validation_alias=AliasChoices("_id", "datapoint_id"),
    )
    """specific id for this data point"""
    data_timestamp: datetime = Field(default_factory=datetime.now)
    """time datapoint was created"""

    @field_validator("datapoint_id", mode="before")
    @classmethod
    def object_id_to_str(cls, v: Union[str, ObjectId]) -> str:
        """Cast ObjectID to string."""
        return str(v)

    @classmethod
    def discriminate(cls, datapoint: "DataPointDataModels") -> "DataPointDataModels":
        """Return the correct data point type based on the data_type attribute.

        Args:
            datapoint: The data point instance or dictionary to discriminate.

        Returns:
            The appropriate DataPoint subclass instance.
        """
        if isinstance(datapoint, dict):
            datapoint_type = datapoint["data_type"]
            return DataPointTypeMap[datapoint_type].model_validate(datapoint)
        if isinstance(datapoint, DataPoint):
            datapoint_type = datapoint.data_type
            return DataPointTypeMap[datapoint_type].model_validate(
                datapoint.model_dump()
            )
        raise TypeError(f"Expected DataPoint or dict, got {type(datapoint).__name__}")


class FileDataPoint(DataPoint):
    """A data point containing a file.

    Attributes:
        data_type: The type of the data point, in this case a file.
        path: The path to the file.
    """

    data_type: Literal[DataPointTypeEnum.FILE] = DataPointTypeEnum.FILE
    """The type of the data point, in this case a file"""
    path: PathLike
    """Path to the file"""


class ValueDataPoint(DataPoint):
    """A data point corresponding to a single JSON serializable value.

    Attributes:
        data_type: The type of the data point, in this case a value.
        value: The value of the data point.
    """

    data_type: Literal[DataPointTypeEnum.DATA_VALUE] = DataPointTypeEnum.DATA_VALUE
    """The type of the data point, in this case a value"""
    value: Any
    """Value of the data point"""


class ObjectStorageDataPoint(DataPoint):
    """A data point that references an object in S3-compatible storage (MinIO/S3).

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
    """

    url: Optional[str] = Field(
        default=None, description="Accessible URL for the object (for frontend use)"
    )
    data_type: Literal[DataPointTypeEnum.OBJECT_STORAGE] = (
        DataPointTypeEnum.OBJECT_STORAGE
    )
    """The type of the data point, in this case an object storage"""
    storage_endpoint: str = Field(
        ..., description="S3 API endpoint (e.g., 'localhost:9000')"
    )
    public_endpoint: Optional[str] = Field(
        default=None,
        description="Public endpoint for accessing objects (e.g., 'localhost:9001')",
    )
    path: PathLike
    """Path to the file"""
    bucket_name: str = Field(
        default=None, description="Name of the bucket containing the object"
    )
    object_name: str = Field(
        default=None, description="Path/key of the object within the bucket"
    )
    content_type: Optional[str] = Field(
        None, description="MIME type of the stored object"
    )
    size_bytes: Optional[int] = Field(None, description="Size of the object in bytes")
    etag: Optional[str] = Field(
        None, description="Entity tag (typically MD5) of the object"
    )
    custom_metadata: dict[str, str] = Field(
        default_factory=dict, description="User-defined metadata for the object"
    )


DataPointDataModels = Annotated[
    Union[
        Annotated[FileDataPoint, Tag(DataPointTypeEnum.FILE)],
        Annotated[ValueDataPoint, Tag(DataPointTypeEnum.DATA_VALUE)],
        Annotated[ObjectStorageDataPoint, Tag(DataPointTypeEnum.OBJECT_STORAGE)],
    ],
    Discriminator("data_type"),
]

DataPointTypeMap = {
    DataPointTypeEnum.FILE: FileDataPoint,
    DataPointTypeEnum.DATA_VALUE: ValueDataPoint,
    DataPointTypeEnum.OBJECT_STORAGE: ObjectStorageDataPoint,
}


class ObjectStorageSettings(
    MadsciBaseSettings,
    env_file=(".env", "object_storage.env"),
    toml_file=("settings.toml", "object_storage.settings.toml"),
    yaml_file=("settings.yaml", "object_storage.settings.yaml"),
    json_file=("settings.json", "object_storage.settings.json"),
    env_prefix="OBJECT_STORAGE_",
):
    """Settings for S3-compatible object storage."""

    endpoint: Optional[str] = Field(
        default=None,
        title="Endpoint",
        description="Endpoint for S3-compatible storage (e.g., 'minio.example.com:9000')",
    )
    access_key: str = Field(
        title="Access Key", description="Access key for authentication", default=""
    )
    secret_key: str = Field(
        title="Secret Key",
        description="Secret key for authentication",
        default="",
    )
    secure: bool = Field(
        default=False,
        title="Secure",
        description="Whether to use HTTPS (True) or HTTP (False)",
    )
    default_bucket: str = Field(
        default="madsci-data",
        title="Default Bucket",
        description="Default bucket to use for storing data",
    )
    region: Optional[str] = Field(
        default=None,
        title="Region",
        description="Optional for AWS S3/other providers",
    )


class DataManagerSettings(
    MadsciBaseSettings,
    env_file=(".env", "data.env"),
    toml_file=("settings.toml", "data.settings.toml"),
    yaml_file=("settings.yaml", "data.settings.yaml"),
    json_file=("settings.json", "data.settings.json"),
    env_prefix="DATA_",
):
    """Settings for the MADSci Data Manager."""

    data_server_url: AnyUrl = Field(
        title="Lab URL",
        description="The URL of the lab manager.",
        default=AnyUrl("http://localhost:8004"),
        alias="data_server_url",  # * Don't double prefix
    )
    data_manager_definition: PathLike = Field(
        title="Data Manager Definition File",
        description="Path to the data manager definition file to use.",
        default=Path("data.manager.yaml"),
        alias="data_manager_definition",  # * Don't double prefix
    )
    db_url: str = Field(
        default="mongodb://localhost:27017",
        title="Database URL",
        description="The URL of the database used by the Data Manager.",
    )
    file_storage_path: PathLike = Field(
        title="File Storage Path",
        description="The path where files are stored on the server.",
        default="~/.madsci/datapoints",
    )


class DataManagerDefinition(ManagerDefinition):
    """Definition for a Squid Data Manager.

    Attributes:
        manager_type: The type of the event manager.
        host: The hostname or IP address of the Data Manager server.
        port: The port number of the Data Manager server.
        db_url: The URL of the database used by the Data Manager.
    """

    name: str = Field(
        title="Manager Name",
        description="The name of this manager instance.",
        default="Data Manager",
    )
    data_manager_id: str = Field(
        title="Data Manager ID",
        description="The ID of the data manager.",
        default_factory=new_ulid_str,
    )
    manager_type: Literal[ManagerType.DATA_MANAGER] = Field(
        title="Manager Type",
        description="The type of the event manager",
        default=ManagerType.DATA_MANAGER,
    )
