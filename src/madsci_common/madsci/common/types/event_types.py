"""
Event types for the MADSci system.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, Optional, Union, get_args

from bson.objectid import ObjectId
from madsci.common.ownership import get_current_ownership_info
from madsci.common.types.auth_types import OwnershipInfo
from madsci.common.types.base_types import (
    MadsciBaseModel,
    PathLike,
    prefixed_alias_generator,
    prefixed_model_validator,
)
from madsci.common.types.client_types import MadsciClientConfig
from madsci.common.types.manager_types import (
    ManagerDefinition,
    ManagerHealth,
    ManagerSettings,
    ManagerType,
)
from madsci.common.utils import new_ulid_str
from pydantic import AliasChoices, AnyUrl, Field
from pydantic.functional_validators import field_validator
from pydantic_settings import SettingsConfigDict

if TYPE_CHECKING:
    from madsci.client.event_client import EventClient


class EventLogLevel(int, Enum):
    """The log level of an event."""

    NOTSET = logging.NOTSET
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL

    @classmethod
    def _missing_(cls, value: object) -> "EventLogLevel":
        """Handle case-insensitive matching for log levels."""
        if isinstance(value, int):
            for member in cls:
                if int(member) == value:
                    return member
            raise ValueError(f"Invalid EventLogLevel: {value}")

        if isinstance(value, str):
            name = value.upper().replace("EVENTLOGLEVEL.", "")
            try:
                return cls[name]
            except KeyError as e:
                raise ValueError(f"Invalid EventLogLevel: {value}") from e

        raise ValueError(f"Invalid EventLogLevel: {value!r}")


class EventManagerSettings(
    ManagerSettings,
    env_file=(".env", "events.env"),
    toml_file=("settings.toml", "events.settings.toml"),
    yaml_file=("settings.yaml", "events.settings.yaml"),
    json_file=("settings.json", "events.settings.json"),
    env_prefix="EVENT_",
):
    """Handles settings and configuration for the Event Manager."""

    model_config = SettingsConfigDict(
        alias_generator=prefixed_alias_generator("event"),
        populate_by_name=True,
    )
    _accept_prefixed_keys = prefixed_model_validator("event")

    server_url: AnyUrl = Field(
        title="Event Server URL",
        description="The URL of the Event Manager server.",
        default=AnyUrl("http://localhost:8001"),
    )
    manager_type: Optional[ManagerType] = Field(
        title="Manager Type",
        description="The type of manager.",
        default=ManagerType.EVENT_MANAGER,
    )
    mongo_db_url: AnyUrl = Field(
        default=AnyUrl("mongodb://localhost:27017"),
        title="MongoDB URL",
        description="The URL of the MongoDB database used by the Event Manager.",
        validation_alias=AliasChoices("mongo_db_url", "EVENT_DB_URL", "db_url"),
        json_schema_extra={"secret": True},
    )
    database_name: str = Field(
        default="madsci_events",
        title="Database Name",
        description="The name of the MongoDB database where events are stored.",
    )
    collection_name: str = Field(
        default="events",
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

    # Retention settings
    retention_enabled: bool = Field(
        default=False,
        title="Retention Enabled",
        description="Whether automatic event retention is enabled.",
    )
    soft_delete_after_days: int = Field(
        default=90,
        title="Soft Delete After Days",
        description="Days after which events are soft-deleted (archived).",
        ge=1,
    )
    hard_delete_after_days: int = Field(
        default=365,
        title="Hard Delete After Days",
        description="Days after archive when events are permanently deleted via TTL index.",
        ge=1,
    )
    retention_check_interval_hours: int = Field(
        default=24,
        title="Retention Check Interval Hours",
        description="How often to run soft-delete retention checks (in hours).",
        ge=1,
    )

    # Batch operation limits (to prevent performance impact)
    archive_batch_size: int = Field(
        default=1000,
        title="Archive Batch Size",
        description="Maximum number of events to archive in a single batch operation.",
        ge=1,
    )
    max_batches_per_run: int = Field(
        default=100,
        title="Max Batches Per Run",
        description="Maximum number of batches to process per retention run (0 = unlimited).",
        ge=0,
    )

    # Backup settings
    backup_enabled: bool = Field(
        default=False,
        title="Backup Enabled",
        description="Whether automatic event backups are enabled.",
    )
    backup_schedule: Optional[str] = Field(
        default=None,
        title="Backup Schedule",
        description="Cron expression for backup schedule (e.g., '0 2 * * *' for 2am daily).",
    )
    backup_dir: PathLike = Field(
        default_factory=lambda: Path("~") / ".madsci" / "backups" / "events",
        title="Backup Directory",
        description="Directory for event backups.",
    )
    backup_max_count: int = Field(
        default=10,
        title="Backup Max Count",
        description="Maximum number of backup files to keep.",
        ge=1,
    )

    # Error handling
    fail_on_retention_error: bool = Field(
        default=False,
        title="Fail On Retention Error",
        description="If True, raise exceptions on retention failures. If False, log and continue.",
    )


class EventManagerHealth(ManagerHealth):
    """Health status for Event Manager including database connectivity."""

    db_connected: Optional[bool] = Field(
        title="Database Connected",
        description="Whether the database connection is working.",
        default=None,
    )
    total_events: Optional[int] = Field(
        title="Total Events",
        description="Total number of events stored in the database.",
        default=None,
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
    # OpenTelemetry trace context for log correlation
    trace_id: Optional[str] = Field(
        title="Trace ID",
        description="OpenTelemetry trace ID for distributed trace correlation (32 hex characters).",
        default=None,
    )
    span_id: Optional[str] = Field(
        title="Span ID",
        description="OpenTelemetry span ID for distributed trace correlation (16 hex characters).",
        default=None,
    )

    # Archive/retention fields
    archived: bool = Field(
        title="Archived",
        description="Whether this event has been archived (soft-deleted).",
        default=False,
    )
    archived_at: Optional[datetime] = Field(
        title="Archived At",
        description="Timestamp when this event was archived. Used by MongoDB TTL index for automatic hard-deletion.",
        default=None,
    )

    @field_validator("event_id", mode="before")
    @classmethod
    def object_id_to_str(cls, v: Union[str, ObjectId]) -> str:
        """Cast ObjectID to string."""
        return str(v)


LogRotationType = Literal["size", "time", "none"]


class EventClientConfig(MadsciClientConfig):
    """Configuration for an Event Client.

    Inherits all HTTP client configuration from MadsciClientConfig including:
    - Retry configuration (retry_enabled, retry_total, retry_backoff_factor, etc.)
    - Timeout configuration (timeout_default, timeout_data_operations, etc.)
    - Connection pooling (pool_connections, pool_maxsize)
    - Rate limiting (rate_limit_tracking_enabled, rate_limit_warning_threshold, etc.)
    """

    model_config = SettingsConfigDict(
        env_prefix="EVENT_CLIENT_",
        env_file=(".env", "event_client.env"),
        toml_file="event_client.toml",
        yaml_file="event_client.yaml",
        json_file="event_client.json",
        env_file_encoding="utf-8",
        validate_assignment=True,
        validate_default=True,
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )

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

    # Log rotation settings
    log_rotation_type: LogRotationType = Field(
        default="size",
        title="Log Rotation Type",
        description="Type of log rotation: 'size' (RotatingFileHandler), 'time' (TimedRotatingFileHandler), or 'none'",
    )
    log_max_bytes: int = Field(
        default=10_485_760,  # 10MB
        title="Log Max Bytes",
        description="Maximum log file size in bytes before rotation (for size-based rotation)",
        ge=1024,  # Minimum 1KB
    )
    log_backup_count: int = Field(
        default=5,
        title="Log Backup Count",
        description="Number of backup log files to keep",
        ge=0,
    )
    log_rotation_when: str = Field(
        default="midnight",
        title="Log Rotation When",
        description="When to rotate logs (for time-based rotation): 'S', 'M', 'H', 'D', 'midnight', 'W0'-'W6'",
    )
    log_rotation_interval: int = Field(
        default=1,
        title="Log Rotation Interval",
        description="Interval for time-based rotation",
        ge=1,
    )
    log_compression_enabled: bool = Field(
        default=True,
        title="Log Compression Enabled",
        description="Whether to compress rotated log files with gzip",
    )

    # Structlog configuration
    log_output_format: Literal["json", "console"] = Field(
        default="console",
        title="Log Output Format",
        description="Log output format: 'json' for structured machine-readable, 'console' for human-readable",
    )
    fail_on_error: bool = Field(
        default=False,
        title="Fail On Error",
        description="If True, raise exceptions on logging/sending failures. If False, log errors silently and continue.",
    )

    # OpenTelemetry configuration
    otel_enabled: bool = Field(
        default=False,
        title="OpenTelemetry Enabled",
        description="Enable OpenTelemetry tracing and metrics integration",
    )
    otel_service_name: Optional[str] = Field(
        default=None,
        title="OpenTelemetry Service Name",
        description="Override service name for OpenTelemetry (defaults to client name)",
    )
    otel_exporter: Literal["console", "otlp", "none"] = Field(
        default="console",
        title="OpenTelemetry Exporter",
        description="OpenTelemetry exporter type: 'console' for development, 'otlp' for production, 'none' to disable",
    )
    otel_endpoint: Optional[str] = Field(
        default=None,
        title="OpenTelemetry Endpoint",
        description="OTLP collector endpoint (required when otel_exporter='otlp')",
    )
    otel_protocol: Literal["grpc", "http"] = Field(
        default="grpc",
        title="OpenTelemetry Protocol",
        description="OTLP transport protocol ('grpc' or 'http')",
    )
    otel_metric_export_interval_ms: int = Field(
        default=10000,
        title="OpenTelemetry Metric Export Interval",
        description="Interval in milliseconds for exporting metrics to the collector",
        ge=1000,  # Minimum 1 second
    )

    @field_validator("otel_endpoint")
    @classmethod
    def validate_otel_endpoint(cls, v: Optional[str]) -> Optional[str]:
        """Validate OTLP endpoint format and normalize trailing slash."""
        if v is None:
            return v
        if not v.startswith(("http://", "https://")):
            raise ValueError("OTLP endpoint must start with http:// or https://")
        return v.rstrip("/")

    @field_validator("log_rotation_when")
    @classmethod
    def validate_log_rotation_when(cls, v: str) -> str:
        """Validate that log_rotation_when is a valid value for TimedRotatingFileHandler."""
        valid_values = {
            "S",
            "M",
            "H",
            "D",
            "midnight",
            "W0",
            "W1",
            "W2",
            "W3",
            "W4",
            "W5",
            "W6",
        }
        if v not in valid_values:
            raise ValueError(
                f"log_rotation_when must be one of {valid_values}, got '{v}'"
            )
        return v

    @field_validator("log_rotation_type", mode="before")
    @classmethod
    def validate_log_rotation_type(cls, v: str) -> str:
        """Validate that log_rotation_type is a valid value."""
        valid_values = get_args(LogRotationType)
        if v not in valid_values:
            raise ValueError(
                f"log_rotation_type must be one of {valid_values}, got '{v}'"
            )
        return v


class EventType(str, Enum):
    """The type of an event.

    Notes:
    - Prefer the most specific type available.
    - The LOG_* types are for general logging; prefer domain-specific types when
      applicable.
    """

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
    EXPERIMENT_CANCELLED = "experiment_cancelled"
    EXPERIMENT_PAUSE = "experiment_pause"
    EXPERIMENT_CONTINUED = "experiment_continued"
    # *Campaign Events
    CAMPAIGN_CREATE = "campaign_create"
    CAMPAIGN_START = "campaign_start"
    CAMPAIGN_COMPLETE = "campaign_complete"
    CAMPAIGN_ABORT = "campaign_abort"
    # *Action Events
    ACTION_STATUS_CHANGE = "action_status_change"

    # *Resource Events
    RESOURCE_CREATE = "resource_create"
    RESOURCE_UPDATE = "resource_update"
    RESOURCE_DELETE = "resource_delete"
    RESOURCE_ALLOCATE = "resource_allocate"
    RESOURCE_RELEASE = "resource_release"

    # *Location Events
    LOCATION_CREATE = "location_create"
    LOCATION_UPDATE = "location_update"
    LOCATION_DELETE = "location_delete"
    ATTACHMENT_CREATE = "attachment_create"
    ATTACHMENT_DELETE = "attachment_delete"

    # *Data Events
    DATA_STORE = "data_store"
    DATA_QUERY = "data_query"
    DATA_EXPORT = "data_export"

    # *Manager Lifecycle Events
    MANAGER_START = "manager_start"
    MANAGER_STOP = "manager_stop"
    MANAGER_ERROR = "manager_error"
    MANAGER_HEALTH_CHECK = "manager_health_check"

    # *Workflow Step Events
    WORKFLOW_STEP_START = "workflow_step_start"
    WORKFLOW_STEP_COMPLETE = "workflow_step_complete"
    WORKFLOW_STEP_FAILED = "workflow_step_failed"

    # *Action Events
    ACTION_START = "action_start"
    ACTION_COMPLETE = "action_complete"
    ACTION_FAILED = "action_failed"

    # *Backup Events
    BACKUP_CREATE = "backup_create"
    BACKUP_RESTORE = "backup_restore"

    @classmethod
    def _missing_(cls, value: object) -> "EventType":
        if not isinstance(value, str):
            raise ValueError(f"Invalid EventType: {value!r}")

        value = value.lower()
        for member in cls:
            if member.lower() == value:
                return member
        raise ValueError(f"Invalid EventType: {value}")


EVENT_TYPE_DESCRIPTIONS: dict[EventType, str] = {
    # Generic
    EventType.UNKNOWN: "Uncategorized/unknown event type.",
    EventType.TEST: "Test-only event type used in unit/integration tests.",
    # Log events
    EventType.LOG: "Generic log event.",
    EventType.LOG_DEBUG: "Debug-level log event.",
    EventType.LOG_INFO: "Info-level log event.",
    EventType.LOG_WARNING: "Warning-level log event.",
    EventType.LOG_ERROR: "Error-level log event.",
    EventType.LOG_CRITICAL: "Critical-level log event.",
    # Lab events
    EventType.LAB_CREATE: "Lab created.",
    EventType.LAB_START: "Lab started.",
    EventType.LAB_STOP: "Lab stopped.",
    # Node events
    EventType.NODE_CREATE: "Node created/registered.",
    EventType.NODE_START: "Node started.",
    EventType.NODE_STOP: "Node stopped.",
    EventType.NODE_CONFIG_UPDATE: "Node configuration updated.",
    EventType.NODE_STATUS_UPDATE: "Node status updated.",
    EventType.NODE_ERROR: "Node error occurred.",
    # Workcell events
    EventType.WORKCELL_CREATE: "Workcell created.",
    EventType.WORKCELL_START: "Workcell started.",
    EventType.WORKCELL_STOP: "Workcell stopped.",
    EventType.WORKCELL_CONFIG_UPDATE: "Workcell configuration updated.",
    EventType.WORKCELL_STATUS_UPDATE: "Workcell status updated.",
    # Workflow events
    EventType.WORKFLOW_CREATE: "Workflow created/enqueued.",
    EventType.WORKFLOW_START: "Workflow execution started.",
    EventType.WORKFLOW_COMPLETE: "Workflow execution completed successfully.",
    EventType.WORKFLOW_ABORT: "Workflow aborted.",
    EventType.WORKFLOW_STEP_START: "Workflow step started.",
    EventType.WORKFLOW_STEP_COMPLETE: "Workflow step completed successfully.",
    EventType.WORKFLOW_STEP_FAILED: "Workflow step failed.",
    # Experiment events
    EventType.EXPERIMENT_CREATE: "Experiment created.",
    EventType.EXPERIMENT_START: "Experiment run started.",
    EventType.EXPERIMENT_COMPLETE: "Experiment run completed.",
    EventType.EXPERIMENT_FAILED: "Experiment run failed.",
    EventType.EXPERIMENT_CANCELLED: "Experiment run cancelled.",
    EventType.EXPERIMENT_PAUSE: "Experiment paused.",
    EventType.EXPERIMENT_CONTINUED: "Experiment continued/resumed.",
    # Campaign events
    EventType.CAMPAIGN_CREATE: "Campaign created.",
    EventType.CAMPAIGN_START: "Campaign started.",
    EventType.CAMPAIGN_COMPLETE: "Campaign completed.",
    EventType.CAMPAIGN_ABORT: "Campaign aborted.",
    # Action events
    EventType.ACTION_STATUS_CHANGE: "Action status changed (legacy aggregate type).",
    EventType.ACTION_START: "Action started.",
    EventType.ACTION_COMPLETE: "Action completed successfully.",
    EventType.ACTION_FAILED: "Action failed.",
    # Resource events
    EventType.RESOURCE_CREATE: "Resource created.",
    EventType.RESOURCE_UPDATE: "Resource updated.",
    EventType.RESOURCE_DELETE: "Resource deleted/removed.",
    EventType.RESOURCE_ALLOCATE: "Resource allocated/reserved.",
    EventType.RESOURCE_RELEASE: "Resource released/unreserved.",
    # Location events
    EventType.LOCATION_CREATE: "Location created.",
    EventType.LOCATION_UPDATE: "Location updated.",
    EventType.LOCATION_DELETE: "Location deleted.",
    EventType.ATTACHMENT_CREATE: "Resource attached to a location.",
    EventType.ATTACHMENT_DELETE: "Resource detached from a location.",
    # Data events
    EventType.DATA_STORE: "Data stored/ingested.",
    EventType.DATA_QUERY: "Data queried/read.",
    EventType.DATA_EXPORT: "Data exported.",
    # Manager lifecycle
    EventType.MANAGER_START: "Manager process/service started.",
    EventType.MANAGER_STOP: "Manager process/service stopped.",
    EventType.MANAGER_ERROR: "Manager encountered an error.",
    EventType.MANAGER_HEALTH_CHECK: "Manager health check performed.",
    # Backup events
    EventType.BACKUP_CREATE: "Backup created.",
    EventType.BACKUP_RESTORE: "Backup restored.",
}


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
        json_schema_extra={"secret": True},
    )
    smtp_password: Optional[str] = Field(
        default=None,
        title="SMTP Password",
        description="The password for authenticating with the SMTP server.",
        json_schema_extra={"secret": True},
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
    manager_id: str = Field(
        title="Event Manager ID",
        description="The ID of the event manager.",
        default_factory=new_ulid_str,
        validation_alias=AliasChoices("manager_id", "event_manager_id"),
    )
    manager_type: ManagerType = Field(
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


@dataclass
class EventClientContext:
    """
    Holds the current EventClient and its hierarchical context.

    This dataclass is used internally by the context management system
    to track the current EventClient and accumulated context metadata.

    Attributes:
        client: The actual EventClient instance for logging.
        hierarchy: The naming hierarchy, e.g., ["experiment", "workflow", "step"].
        metadata: Accumulated context metadata (experiment_id, workflow_id, etc.).

    Example:
        ctx = EventClientContext(
            client=event_client,
            hierarchy=["experiment", "workflow"],
            metadata={"experiment_id": "exp-123", "workflow_id": "wf-456"},
        )
        print(ctx.name)  # "experiment.workflow"
    """

    client: "EventClient"
    """The actual EventClient instance."""

    hierarchy: list[str] = field(default_factory=list)
    """The naming hierarchy, e.g., ["experiment", "workflow", "step"]."""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Accumulated context metadata (experiment_id, workflow_id, etc.)."""

    @property
    def name(self) -> str:
        """
        Get the full hierarchical name.

        Returns:
            Dot-separated hierarchy string, or "madsci" if empty.
        """
        return ".".join(self.hierarchy) if self.hierarchy else "madsci"

    def child(
        self,
        name: str,
        client: Optional["EventClient"] = None,
        **metadata: Any,
    ) -> "EventClientContext":
        """
        Create a child context with extended hierarchy.

        Args:
            name: Name for this context level, added to hierarchy.
            client: Optional explicit EventClient. If None, creates a bound
                   child from the parent's client.
            **metadata: Additional context metadata to merge.

        Returns:
            New EventClientContext with extended hierarchy and metadata.

        Example:
            parent_ctx = EventClientContext(client=client, hierarchy=["experiment"])
            child_ctx = parent_ctx.child("workflow", workflow_id="wf-123")
            # child_ctx.hierarchy == ["experiment", "workflow"]
            # child_ctx.metadata == {"workflow_id": "wf-123"}
        """
        merged_metadata = {**self.metadata, **metadata}

        if client is not None:
            child_client = client
        else:
            # Create bound child from parent's client
            child_client = self.client.bind(**metadata) if metadata else self.client

        return EventClientContext(
            client=child_client,
            hierarchy=[*self.hierarchy, name],
            metadata=merged_metadata,
        )
