"""
Event types for the MADSci system.
"""

import logging
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Literal, Optional, Union

from bson.objectid import ObjectId
from madsci.common.ownership import get_current_ownership_info
from madsci.common.types.auth_types import OwnershipInfo
from madsci.common.types.base_types import MadsciBaseModel, MadsciBaseSettings, PathLike
from madsci.common.types.lab_types import ManagerDefinition, ManagerType
from madsci.common.utils import new_ulid_str
from pydantic import AliasChoices, AnyUrl, Field
from pydantic.functional_validators import field_validator


class EventLogLevel(int, Enum):
    """The log level of an event."""

    NOTSET = logging.NOTSET
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL

    @classmethod
    def _missing_(cls, value: Union[str, int]) -> "EventLogLevel":
        """Handle case-insensitive matching for log levels."""
        if isinstance(value, str):
            value = value.upper()
            value = value.replace("EVENTLOGLEVEL.", "")
        return cls[value]


class EventManagerSettings(
    MadsciBaseSettings,
    env_file=(".env", "events.env"),
    toml_file=("settings.toml", "events.settings.toml"),
    yaml_file=("settings.yaml", "events.settings.yaml"),
    json_file=("settings.json", "events.settings.json"),
    env_prefix="EVENTS_",
):
    """Handles settings and configuration for the Event Manager."""

    event_server_url: Optional[AnyUrl] = Field(
        title="Event Server URL",
        description="The URL of the Event Manager server.",
        default="http://localhost:8001",
        alias="event_server_url",  # * Don't double prefix
    )
    event_manager_definition: PathLike = Field(
        title="Event Manager Definition File",
        description="Path to the event manager definition file to use.",
        default=Path("event.manager.yaml"),
        alias="event_manager_definition",  # * Don't double prefix
    )
    db_url: str = Field(
        default="mongodb://localhost:27017",
        title="Database URL",
        description="The URL of the database used by the Event Manager.",
    )
    collection_name: str = Field(
        default="madsci_events",
        title="Collection Name",
        description="The name of the MongoDB collection where events are stored.",
    )
    alert_level: EventLogLevel = Field(
        default=EventLogLevel.ERROR,
        title="Alert Level",
        description="The log level at which to send an alert.",
    )
    # TODO: Break out email alert config into separate settings
    email_alerts: Optional["EmailAlertsConfig"] = Field(
        default=None,
        title="Email Alerts Configuration",
        description="The configuration for sending email alerts.",
    )


class Event(MadsciBaseModel):
    """An event in the MADSci system."""

    event_id: str = Field(
        title="Event ID",
        description="The ID of the event.",
        default_factory=new_ulid_str,
        serialization_alias="_id",
        validation_alias=AliasChoices("_id", "event_id"),
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
    alert: bool = Field(
        title="Alert",
        description="Forces firing an alert about this event. Defaults to False.",
        default=False,
    )
    event_timestamp: datetime = Field(
        title="Event Timestamp",
        description="The timestamp of the event.",
        default_factory=datetime.now,
    )
    source: OwnershipInfo = Field(
        title="Source",
        description="Information about the source of the event.",
        default_factory=get_current_ownership_info,
    )
    event_data: Any = Field(
        title="Event Data",
        description="The data associated with the event.",
        default_factory=dict,
    )

    @field_validator("event_id", mode="before")
    @classmethod
    def object_id_to_str(cls, v: Union[str, ObjectId]) -> str:
        """Cast ObjectID to string."""
        return str(v)


class EventClientConfig(
    MadsciBaseSettings,
    env_file=(".env", "event_client.env"),
    toml_file="event_client.toml",
    yaml_file="event_client.yaml",
    json_file="event_client.json",
    env_prefix="EVENT_CLIENT_",
):
    """Configuration for an Event Client."""

    name: Optional[str] = Field(
        title="Event Client Name",
        description="The name of the event client.",
        default=None,
    )
    event_server_url: Optional[AnyUrl] = Field(
        title="Event Server URL",
        description="The URL of the event server.",
        default=None,
        alias="event_server_url",  # * Don't prefix
    )
    log_level: Union[int, EventLogLevel] = Field(
        title="Event Client Log Level",
        description="The log level of the event client.",
        default=EventLogLevel.INFO,  # * Don't prefix
    )
    source: OwnershipInfo = Field(
        title="Source",
        description="Information about the source of the event client.",
        default_factory=get_current_ownership_info,
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


class EmailAlertsConfig(MadsciBaseModel):
    """Configuration for sending emails."""

    smtp_server: str = Field(
        default="smtp.example.com",
        title="SMTP Server",
        description="The SMTP server address used for sending emails.",
    )
    smtp_port: int = Field(
        default=587,
        title="SMTP Port",
        description="The port number used by the SMTP server.",
    )
    smtp_username: Optional[str] = Field(
        default=None,
        title="SMTP Username",
        description="The username for authenticating with the SMTP server.",
    )
    smtp_password: Optional[str] = Field(
        default=None,
        title="SMTP Password",
        description="The password for authenticating with the SMTP server.",
    )
    use_tls: bool = Field(
        default=True,
        title="Use TLS",
        description="Whether to use TLS for the SMTP connection.",
    )
    sender: str = Field(
        default="no-reply@example.com",
        title="Sender Email",
        description="The default sender email address.",
    )
    default_importance: str = Field(
        default="Normal",
        title="Default Importance",
        description="The default importance level of the email. Options are: High, Normal, Low.",
    )
    email_addresses: list[str] = Field(
        default_factory=list,
        title="Default Email Addresses",
        description="The default email addresses to send alerts to.",
    )


class EventManagerDefinition(ManagerDefinition):
    """Definition for a Squid Event Manager"""

    name: str = Field(
        title="Manager Name",
        description="The name of this manager instance.",
        default="Event Manager",
    )
    event_manager_id: str = Field(
        title="Event Manager ID",
        description="The ID of the event manager.",
        default_factory=new_ulid_str,
    )
    manager_type: Literal[ManagerType.EVENT_MANAGER] = Field(
        title="Manager Type",
        description="The type of the event manager",
        default=ManagerType.EVENT_MANAGER,
    )


class NodeUtilizationData(MadsciBaseModel):
    """Utilization data for a single node."""

    node_id: str = Field(
        title="Node ID",
        description="The unique identifier for the node.",
    )
    total_time: float = Field(
        title="Total Time",
        description="Total time tracked for this node in seconds.",
        default=0.0,
    )
    busy_time: float = Field(
        title="Busy Time",
        description="Time the node spent in busy state in seconds.",
        default=0.0,
    )
    idle_time: float = Field(
        title="Idle Time",
        description="Time the node spent in idle state in seconds.",
        default=0.0,
    )
    error_time: float = Field(
        title="Error Time",
        description="Time the node spent in error state in seconds.",
        default=0.0,
    )
    active_time: float = Field(
        title="Active Time",
        description="Time the node spent in active/available state in seconds.",
        default=0.0,
    )
    inactive_time: float = Field(
        title="Inactive Time",
        description="Time the node spent in inactive/unavailable state in seconds.",
        default=0.0,
    )
    active_state: str = Field(
        title="Active State",
        description="Current active state of the node (active, inactive, unknown).",
        default="unknown",
    )

    last_state_change: Optional[datetime] = Field(
        title="Last State Change",
        description="Timestamp of the last state change for this node.",
        default=None,
    )
    last_active_change: Optional[datetime] = Field(
        title="Last Active State Change",
        description="Timestamp of the last active state change for this node.",
        default=None,
    )
    current_state: str = Field(
        title="Current State",
        description="Current state of the node (idle, busy, error, unknown).",
        default="unknown",
    )
    active_actions: set[str] = Field(
        title="Active Actions",
        description="Set of currently active action IDs on this node.",
        default_factory=set,
    )
    utilization_percentage: float = Field(
        title="Utilization Percentage",
        description="Calculated utilization percentage for this node.",
        default=0.0,
    )


class SystemUtilizationData(MadsciBaseModel):
    """System-wide utilization data."""

    total_time: float = Field(
        title="Total Time",
        description="Total time tracked for the system in seconds.",
        default=0.0,
    )
    active_time: float = Field(
        title="Active Time",
        description="Time the system spent in active state in seconds.",
        default=0.0,
    )
    idle_time: float = Field(
        title="Idle Time",
        description="Time the system spent in idle state in seconds.",
        default=0.0,
    )
    last_state_change: Optional[datetime] = Field(
        title="Last State Change",
        description="Timestamp of the last system state change.",
        default=None,
    )
    current_state: str = Field(
        title="Current State",
        description="Current state of the system (idle, active).",
        default="idle",
    )
    active_experiments: set[str] = Field(
        title="Active Experiments",
        description="Set of currently active experiment IDs.",
        default_factory=set,
    )
    active_workflows: set[str] = Field(
        title="Active Workflows",
        description="Set of currently active workflow IDs.",
        default_factory=set,
    )
    utilization_percentage: float = Field(
        title="Utilization Percentage",
        description="Calculated system utilization percentage.",
        default=0.0,
    )
