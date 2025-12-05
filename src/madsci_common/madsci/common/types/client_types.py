"""
Client configuration types for MADSci.

This module provides Pydantic settings models for configuring HTTP clients
across the MADSci ecosystem, including retry strategies, timeout values,
and backoff algorithms.
"""

from typing import Optional

from madsci.common.types.base_types import MadsciBaseSettings
from pydantic import Field
from pydantic_settings import SettingsConfigDict


class MadsciClientConfig(MadsciBaseSettings):
    """
    Base configuration for MADSci HTTP clients.

    This class provides standardized configuration for requests library usage,
    including retry strategies, timeout values, and backoff algorithms.
    All MADSci clients should use this configuration to ensure consistency.

    Attributes
    ----------
    retry_enabled : bool
        Whether to enable automatic retries for failed requests. Default: True.
    retry_total : int
        Total number of retry attempts. Default: 3.
    retry_backoff_factor : float
        Backoff factor between retries (in seconds). The actual delay is calculated
        as {backoff factor} * (2 ** ({retry number} - 1)). Default: 0.3.
    retry_status_forcelist : list[int]
        HTTP status codes that should trigger a retry. Default: [429, 500, 502, 503, 504].
    retry_allowed_methods : Optional[list[str]]
        HTTP methods that are allowed to be retried. If None, uses urllib3 defaults
        (HEAD, GET, PUT, DELETE, OPTIONS, TRACE). Default: None.
    timeout_default : float
        Default timeout in seconds for standard requests. Default: 10.
    timeout_data_operations : float
        Timeout in seconds for data-heavy operations (e.g., uploads, downloads). Default: 60.
    timeout_long_operations : float
        Timeout in seconds for long-running operations (e.g., workflow queries, utilization). Default: 100.
    pool_connections : int
        Number of connection pool entries for the session. Default: 10.
    pool_maxsize : int
        Maximum size of the connection pool. Default: 10.
    rate_limit_tracking_enabled : bool
        Whether to track rate limit headers from server responses. Default: True.
    rate_limit_warning_threshold : float
        Threshold (0.0 to 1.0) at which to log warnings about approaching rate limits. Default: 0.8.
    rate_limit_respect_limits : bool
        Whether to proactively delay requests when approaching rate limits. Default: False.
    """

    model_config = SettingsConfigDict(
        env_prefix="MADSCI_CLIENT_",
        env_file=None,
        env_file_encoding="utf-8",
        validate_assignment=True,
        validate_default=True,
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )

    # Retry configuration
    retry_enabled: bool = Field(
        default=True,
        description="Whether to enable automatic retries for failed requests",
    )
    retry_total: int = Field(
        default=3,
        ge=0,
        description="Total number of retry attempts",
    )
    retry_backoff_factor: float = Field(
        default=0.3,
        ge=0.0,
        description="Backoff factor between retries in seconds",
    )
    retry_status_forcelist: list[int] = Field(
        default=[429, 500, 502, 503, 504],
        description="HTTP status codes that should trigger a retry",
    )
    retry_allowed_methods: Optional[list[str]] = Field(
        default=None,
        description="HTTP methods allowed to be retried (None uses urllib3 defaults)",
    )

    # Timeout configuration
    timeout_default: float = Field(
        default=10.0,
        gt=0.0,
        description="Default timeout in seconds for standard requests",
    )
    timeout_data_operations: float = Field(
        default=60.0,
        gt=0.0,
        description="Timeout in seconds for data-heavy operations",
    )
    timeout_long_operations: float = Field(
        default=100.0,
        gt=0.0,
        description="Timeout in seconds for long-running operations",
    )

    # Connection pooling configuration
    pool_connections: int = Field(
        default=10,
        ge=1,
        description="Number of connection pool entries",
    )
    pool_maxsize: int = Field(
        default=10,
        ge=1,
        description="Maximum size of the connection pool",
    )

    # Rate limit handling configuration
    rate_limit_tracking_enabled: bool = Field(
        default=True,
        description="Whether to track rate limit headers from server responses",
    )
    rate_limit_warning_threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Threshold (as fraction of limit) at which to log warnings about approaching rate limits",
    )
    rate_limit_respect_limits: bool = Field(
        default=False,
        description="Whether to proactively delay requests when approaching rate limits",
    )


class ExperimentClientConfig(MadsciClientConfig):
    """Configuration for the Experiment Manager client."""

    model_config = SettingsConfigDict(
        env_prefix="EXPERIMENT_CLIENT_",
        env_file=None,
        env_file_encoding="utf-8",
    )


class DataClientConfig(MadsciClientConfig):
    """
    Configuration for the Data Manager client.

    The Data Manager handles data uploads and downloads that may require extended timeouts.
    """

    model_config = SettingsConfigDict(
        env_prefix="DATA_CLIENT_",
        env_file=None,
        env_file_encoding="utf-8",
    )


class LocationClientConfig(MadsciClientConfig):
    """Configuration for the Location Manager client."""

    model_config = SettingsConfigDict(
        env_prefix="LOCATION_CLIENT_",
        env_file=None,
        env_file_encoding="utf-8",
    )


class WorkcellClientConfig(MadsciClientConfig):
    """
    Configuration for the Workcell Manager client.

    The Workcell Manager handles workflow queries that may require extended timeouts.
    """

    model_config = SettingsConfigDict(
        env_prefix="WORKCELL_CLIENT_",
        env_file=None,
        env_file_encoding="utf-8",
    )


class ResourceClientConfig(MadsciClientConfig):
    """Configuration for the Resource Manager client."""

    model_config = SettingsConfigDict(
        env_prefix="RESOURCE_CLIENT_",
        env_file=None,
        env_file_encoding="utf-8",
    )


class LabClientConfig(MadsciClientConfig):
    """Configuration for the Lab (Squid) client."""

    model_config = SettingsConfigDict(
        env_prefix="LAB_CLIENT_",
        env_file=None,
        env_file_encoding="utf-8",
    )


class RestNodeClientConfig(MadsciClientConfig):
    """
    Configuration for Node REST clients.

    Node clients handle action operations (create, upload, start, download)
    that may require extended timeouts.
    """

    model_config = SettingsConfigDict(
        env_prefix="NODE_CLIENT_",
        env_file=None,
        env_file_encoding="utf-8",
    )

    # Override default timeout for action operations
    timeout_data_operations: float = Field(
        default=60.0,
        gt=0.0,
        description="Timeout for node action operations",
    )
