"""Types used primarily by MADSci Managers."""

from enum import Enum
from pathlib import Path
from typing import Literal, Optional

from madsci.common.types.base_types import MadsciBaseModel, MadsciBaseSettings, PathLike
from madsci.common.utils import new_ulid_str
from pydantic import AnyUrl, ConfigDict, Field


class ManagerType(str, Enum):  # pyright: ignore[reportIncompatibleMethodOverride]
    """Types of Squid Managers."""

    WORKCELL_MANAGER = "workcell_manager"
    RESOURCE_MANAGER = "resource_manager"
    EVENT_MANAGER = "event_manager"
    AUTH_MANAGER = "auth_manager"
    DATA_MANAGER = "data_manager"
    TRANSFER_MANAGER = "transfer_manager"
    EXPERIMENT_MANAGER = "experiment_manager"
    LAB_MANAGER = "lab_manager"
    LOCATION_MANAGER = "location_manager"


class ManagerSettings(MadsciBaseSettings):
    """Base settings class for MADSci Manager services.

    This class provides common configuration fields that all managers need,
    such as server URL and manager definition file path.

    Manager-specific settings classes should inherit from this class and:
    1. Add their specific configuration parameters
    2. Set appropriate env_prefix, env_file, toml_file, etc. parameters
    3. Override default values as needed (especially server_url default port)
    """

    server_url: AnyUrl = Field(
        title="Server URL",
        description="The URL where this manager's server runs.",
        default="http://localhost:8000",
    )
    manager_definition: PathLike = Field(
        title="Manager Definition File",
        description="Path to the manager definition file to use.",
        default=Path("manager.yaml"),
    )

    # Rate limiting settings
    rate_limit_enabled: bool = Field(
        title="Rate Limiting Enabled",
        description="Enable rate limiting for API endpoints.",
        default=True,
    )
    rate_limit_requests: int = Field(
        title="Rate Limit Requests",
        description="Maximum number of requests allowed per long time window.",
        default=300,
        ge=1,
    )
    rate_limit_window: int = Field(
        title="Rate Limit Window",
        description="Long time window for rate limiting in seconds.",
        default=60,
        ge=1,
    )
    rate_limit_short_requests: Optional[int] = Field(
        title="Rate Limit Short Requests",
        description="Maximum number of requests allowed per short time window for burst protection. If None, short window limiting is disabled.",
        default=50,
        ge=1,
    )
    rate_limit_short_window: Optional[int] = Field(
        title="Rate Limit Short Window",
        description="Short time window for burst protection in seconds. If None, short window limiting is disabled.",
        default=1,
        ge=1,
    )
    rate_limit_cleanup_interval: int = Field(
        title="Rate Limit Cleanup Interval",
        description="Interval in seconds between cleanup operations to prevent memory leaks.",
        default=300,
        ge=1,
    )
    rate_limit_exempt_ips: Optional[list[str]] = Field(
        title="Rate Limit Exempt IPs",
        description="List of IP addresses exempt from rate limiting. Defaults to localhost IPs (127.0.0.1, ::1) if not specified.",
        default=None,
    )

    # Server resource constraints
    uvicorn_workers: Optional[int] = Field(
        title="Uvicorn Workers",
        description="Number of uvicorn worker processes. If None, uses uvicorn default (1).",
        default=None,
        ge=1,
    )
    uvicorn_limit_concurrency: Optional[int] = Field(
        title="Uvicorn Limit Concurrency",
        description="Maximum number of concurrent connections. If None, no limit is enforced.",
        default=None,
        ge=1,
    )
    uvicorn_limit_max_requests: Optional[int] = Field(
        title="Uvicorn Limit Max Requests",
        description="Maximum number of requests a worker will process before restarting. Helps prevent memory leaks.",
        default=None,
        ge=1,
    )

    # OpenTelemetry configuration
    otel_enabled: bool = Field(
        default=False,
        title="OpenTelemetry Enabled",
        description="Enable OpenTelemetry tracing and metrics integration for this manager",
    )
    otel_service_name: Optional[str] = Field(
        default=None,
        title="OpenTelemetry Service Name",
        description="Override service name for OpenTelemetry (defaults to manager name)",
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


class ManagerHealth(MadsciBaseModel):
    """Base health status for MADSci Manager services.

    This class provides common health check fields that all managers need.
    Manager-specific health classes should inherit from this class and add
    additional fields for database connections, external dependencies, etc.
    """

    healthy: bool = Field(
        title="Manager Health Status",
        description="Whether the manager is operating normally.",
        default=True,
    )
    description: Optional[str] = Field(
        title="Health Status Description",
        description="Human-readable description of any problems or status.",
        default=None,
    )
    version: Optional[str] = Field(
        title="Manager Version",
        description="The version of the manager's package.",
        default=None,
    )

    model_config = ConfigDict(extra="allow")


class ManagerDefinition(MadsciBaseModel):
    """Definition for a MADSci Manager."""

    model_config = ConfigDict(extra="allow")

    name: str = Field(
        title="Manager Name",
        description="The name of this manager instance.",
    )
    description: Optional[str] = Field(
        default=None,
        title="Description",
        description="A description of the manager.",
    )
    manager_id: str = Field(
        default_factory=new_ulid_str,
        title="Manager ID",
        description="The unique identifier for this manager instance.",
    )
    manager_type: "ManagerType" = Field(
        title="Manager Type",
        description="The type of the manager, used by other components or managers to find matching managers.",
    )
