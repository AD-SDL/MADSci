"""Types related to datapoint types"""

from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Literal, Optional, Union

from madsci.common.types.auth_types import OwnershipInfo
from madsci.common.types.base_types import BaseModel, PathLike, new_ulid_str
from madsci.common.types.event_types import EventClientConfig
from madsci.common.types.lab_types import ManagerDefinition, ManagerType
from pydantic import Field, Tag
from pydantic.types import Discriminator


class DataPointTypeEnum(str, Enum):
    """Enumeration for the types of data points.

    Attributes:
        FILE: Represents a data point that contains a file.
        DATA_VALUE: Represents a data point that contains a JSON serializable value.
    """

    FILE = "file"
    DATA_VALUE = "data_value"


class DataPoint(BaseModel, extra="allow"):
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
    ownership_info: Optional[OwnershipInfo] = Field(default_factory=OwnershipInfo)
    """Information about the ownership of the data point"""
    data_type: DataPointTypeEnum
    """type of the datapoint, inherited from class"""
    datapoint_id: str = Field(default_factory=new_ulid_str)
    """specific id for this data point"""
    data_timestamp: datetime = Field(default_factory=datetime.now)
    """time datapoint was created"""

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
        else:
            datapoint_type = datapoint.data_type
        return DataPointTypeMap[datapoint_type].model_validate(datapoint)


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


DataPointDataModels = Annotated[
    Union[
        Annotated[FileDataPoint, Tag(DataPointTypeEnum.FILE)],
        Annotated[ValueDataPoint, Tag(DataPointTypeEnum.DATA_VALUE)],
    ],
    Discriminator("data_type"),
]

DataPointTypeMap = {
    DataPointTypeEnum.FILE: FileDataPoint,
    DataPointTypeEnum.DATA_VALUE: ValueDataPoint,
}


class DataManagerDefinition(ManagerDefinition):
    """Definition for a Squid Data Manager.

    Attributes:
        manager_type: The type of the event manager.
        host: The hostname or IP address of the Data Manager server.
        port: The port number of the Data Manager server.
        db_url: The URL of the database used by the Data Manager.
        event_client_config: The configuration for a MADSci event client.
    """

    manager_type: Literal[ManagerType.DATA_MANAGER] = Field(
        title="Manager Type",
        description="The type of the event manager",
        default=ManagerType.DATA_MANAGER,
    )
    host: str = Field(
        default="127.0.0.1",
        title="Server Host",
        description="The hostname or IP address of the Data Manager server.",
    )
    port: int = Field(
        default=8004,
        title="Server Port",
        description="The port number of the Data Manager server.",
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
    event_client_config: Optional[EventClientConfig] = Field(
        title="Event Client Configuration",
        description="The configuration for a MADSci event client.",
        default=None,
    )
