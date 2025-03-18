"""
Event types for the MADSci system.
"""

import logging
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Literal, Optional

from madsci.common.types.auth_types import OwnershipInfo
from madsci.common.types.base_types import BaseModel, PathLike, new_ulid_str
from madsci.common.types.lab_types import ManagerDefinition, ManagerType
from madsci.common.validators import ulid_validator
from pydantic.functional_validators import field_validator
from sqlmodel import Field


class Event(BaseModel):
    """An event in the MADSci system."""

    event_id: str = Field(
        title="Event ID",
        description="The ID of the event.",
        default_factory=new_ulid_str,
    )
    event_type: "EventType" = Field(
        title="Event Type",
        description="The type of the event.",
        default_factory=lambda: EventType.UNKNOWN,
    )
    log_level: "EventLogLevel" = Field(
        title="Event Log Level",
        description="The log level of the event. Defaults to NOTSET. See https://docs.python.org/3/library/logging.html#logging-levels",
        default_factory=lambda: EventLogLevel.INFO,
    )
    event_timestamp: datetime = Field(
        title="Event Timestamp",
        description="The timestamp of the event.",
        default_factory=datetime.now,
    )
    source: Optional[OwnershipInfo] = Field(
        title="Source",
        description="Information about the source of the event.",
        default=None,
    )
    event_data: Any = Field(
        title="Event Data",
        description="The data associated with the event.",
        default_factory=dict,
    )

    is_ulid = field_validator("event_id", mode="after")(ulid_validator)


class EventLogLevel(int, Enum):
    """The log level of an event."""

    NOTSET = logging.NOTSET
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


class EventClientConfig(BaseModel):
    """Configuration for an Event Client."""

    name: Optional[str] = Field(
        title="Event Client Name",
        description="The name of the event client.",
        default=None,
    )
    event_server_url: Optional[str] = Field(
        title="Event Server URL",
        description="The URL of the event server.",
        default=None,
    )
    log_level: int = Field(
        title="Event Client Log Level",
        description="The log level of the event client.",
        default=EventLogLevel.INFO,
    )
    source: Optional[OwnershipInfo] = Field(
        title="Source",
        description="Information about the source of the event client.",
        default=None,
    )
    log_dir: PathLike = Field(
        title="Log Directory",
        description="The directory to store logs in.",
        default_factory=lambda: Path("~") / ".madsci" / "logs",
    )


class EventType(str, Enum):
    """The type of an event."""

    UNKNOWN = "unknown"
    LOG = "log"
    LOG_DEBUG = "log_debug"
    LOG_INFO = "log_info"
    LOG_WARNING = "log_warning"
    LOG_ERROR = "log_error"
    LOG_CRITICAL = "log_critical"
    TEST = "test"
    # *Lab Events
    LAB_CREATE = "lab_create"
    LAB_START = "lab_start"
    LAB_STOP = "lab_stop"
    # *Node Events
    NODE_CREATE = "node_create"
    NODE_START = "node_start"
    NODE_STOP = "node_stop"
    NODE_CONFIG_UPDATE = "node_config_update"
    NODE_STATUS_UPDATE = "node_status_update"
    NODE_ERROR = "node_error"
    # *Workcell Events
    WORKCELL_CREATE = "workcell_create"
    WORKCELL_START = "workcell_start"
    WORKCELL_STOP = "workcell_stop"
    WORKCELL_CONFIG_UPDATE = "workcell_config_update"
    WORKCELL_STATUS_UPDATE = "workcell_status_update"
    # *Workflow Events
    WORKFLOW_CREATE = "workflow_create"
    WORKFLOW_START = "workflow_start"
    WORKFLOW_COMPLETE = "workflow_complete"
    WORKFLOW_ABORT = "workflow_abort"
    # *Experiment Events
    EXPERIMENT_CREATE = "experiment_create"
    EXPERIMENT_START = "experiment_start"
    EXPERIMENT_COMPLETE = "experiment_complete"
    EXPERIMENT_FAILED = "experiment_failed"
    EXPERIMENT_CANCELLED = "experiment_stop"
    EXPERIMENT_PAUSE = "experiment_pause"
    EXPERIMENT_CONTINUED = "experiment_continued"
    # *Campaign Events
    CAMPAIGN_CREATE = "campaign_create"
    CAMPAIGN_START = "campaign_start"
    CAMPAIGN_COMPLETE = "campaign_complete"
    CAMPAIGN_ABORT = "campaign_abort"
    # *Action Events
    ACTION_STATUS_CHANGE = "action_status_change"

    @classmethod
    def _missing_(cls, value: str) -> "EventType":
        value = value.lower()
        for member in cls:
            if member.lower() == value:
                return member
        raise ValueError(f"Invalid ManagerTypes: {value}")


class EventManagerDefinition(ManagerDefinition):
    """Definition for a Squid Event Manager"""

    manager_type: Literal[ManagerType.EVENT_MANAGER] = Field(
        title="Manager Type",
        description="The type of the event manager",
        default=ManagerType.EVENT_MANAGER,
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
    event_client_config: "EventClientConfig" = Field(
        default_factory=lambda: EventClientConfig(),
        title="Event Client Configuration",
        description="The configuration for a MADSci event client. This is used by the event manager to log it's own events/logs. Note that the event_server_url is ignored.",
    )
