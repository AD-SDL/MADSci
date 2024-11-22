"""
Event types for the MADSci system.
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import ConfigDict
from pydantic.functional_validators import field_validator
from sqlmodel import Field

from madsci.common.types.auth_types import OwnershipInfo
from madsci.common.types.base_types import BaseModel, new_ulid_str
from madsci.common.types.validators import ulid_validator


class Event(BaseModel):
    """An event in the MADSci system."""

    model_config = ConfigDict(extra="allow")

    event_id: str = Field(
        title="Event ID",
        description="The ID of the event.",
        default_factory=new_ulid_str,
    )
    event_type: "EventType" = Field(
        title="Event Type", description="The type of the event.", default="unknown"
    )
    log_level: "EventLogLevel" = Field(
        title="Event Log Level",
        description="The log level of the event. Defaults to NOTSET. See https://docs.python.org/3/library/logging.html#logging-levels",
        default_factory=lambda: EventLogLevel.NOTSET,
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


class EventType(str, Enum):
    """The type of an event."""

    UNKNOWN = "unknown"
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
    EXPERIMENT_STOP = "experiment_stop"
    EXPERIMENT_CONTINUED = "experiment_continued"
    EXPERIMENT_PAUSE = "experiment_pause"
    EXPERIMENT_COMPLETE = "experiment_complete"
    EXPERIMENT_ABORT = "experiment_abort"
    # *Campaign Events
    CAMPAIGN_CREATE = "campaign_create"
    CAMPAIGN_START = "campaign_start"
    CAMPAIGN_COMPLETE = "campaign_complete"
    CAMPAIGN_ABORT = "campaign_abort"
