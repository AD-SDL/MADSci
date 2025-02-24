"""Types related to datapoint types"""

from datetime import datetime
from typing import Any, Literal, Optional

from madsci.common.types.base_types import BaseModel, new_ulid_str
from madsci.common.types.event_types import EventClientConfig
from madsci.common.types.lab_types import ManagerDefinition, ManagerType
from pydantic import Field


class DataPoint(BaseModel, extra="allow"):
    """An object to contain and locate data identified by modules"""

    label: str
    """label of this data point"""
    step_id: Optional[str] = None
    """step that generated the data point"""
    workflow_id: Optional[str] = None
    """workflow that generated the data point"""
    experiment_id: Optional[str] = None
    """experiment that generated the data point"""
    campaign_id: Optional[str] = None
    """campaign of the data point"""
    type: str
    """type of the datapoint, inherited from class"""
    datapoint_id: str = Field(default_factory=new_ulid_str)
    """specific id for this data point"""
    data_timestamp: datetime = Field(default_factory=datetime.now)
    """time datapoint was created"""


class LocalFileDataPoint(DataPoint):
    """a datapoint containing a file"""

    type: Literal["local_file"] = "local_file"
    """local file"""
    path: str
    """path to the file"""


class ValueDataPoint(DataPoint):
    """a datapoint contained in the Json value"""

    type: Literal["data_value"] = "data_value"
    """data_value"""
    value: Any
    """value of the data point"""


data_types = {
    "local_file": LocalFileDataPoint,
    "data_value": ValueDataPoint,
}


class DataManagerDefinition(ManagerDefinition):
    """Definition for a Squid Event Manager"""

    manager_type: Literal[ManagerType.DATA_MANAGER] = Field(
        title="Manager Type",
        description="The type of the event manager",
        default=ManagerType.DATA_MANAGER,
    )
    host: str = Field(
        default="127.0.0.1",
        title="Server Host",
        description="The hostname or IP address of the Event Manager server.",
    )
    port: int = Field(
        default=8001,
        title="Server Port",
        description="The port number of the Event Manager server.",
    )
    db_url: str = Field(
        default="mongodb://localhost:27017",
        title="Database URL",
        description="The URL of the database used by the Event Manager.",
    )
    event_client_config: Optional[EventClientConfig] = Field(
        title="Event Client Configuration",
        description="The configuration for a MADSci event client.",
        default=None,
    )
