Module madsci.common.types.client_types
=======================================
Client configuration types for MADSci.

This module provides Pydantic settings models for configuring HTTP clients
across the MADSci ecosystem, including retry strategies, timeout values,
and backoff algorithms.

Classes
-------

`DataClientConfig(**values: Any)`
:   Configuration for the Data Manager client.

    The Data Manager handles data uploads and downloads that may require extended timeouts.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.client_types.MadsciClientConfig
    * madsci.common.types.base_types.MadsciBaseSettings
    * pydantic_settings.main.BaseSettings
    * pydantic.main.BaseModel

`ExperimentClientConfig(**values: Any)`
:   Configuration for the Experiment Manager client.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.client_types.MadsciClientConfig
    * madsci.common.types.base_types.MadsciBaseSettings
    * pydantic_settings.main.BaseSettings
    * pydantic.main.BaseModel

`LabClientConfig(**values: Any)`
:   Configuration for the Lab (Squid) client.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.client_types.MadsciClientConfig
    * madsci.common.types.base_types.MadsciBaseSettings
    * pydantic_settings.main.BaseSettings
    * pydantic.main.BaseModel

`LocationClientConfig(**values: Any)`
:   Configuration for the Location Manager client.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.client_types.MadsciClientConfig
    * madsci.common.types.base_types.MadsciBaseSettings
    * pydantic_settings.main.BaseSettings
    * pydantic.main.BaseModel

`MadsciClientConfig(**values: Any)`
:   Base configuration for MADSci HTTP clients.

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

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseSettings
    * pydantic_settings.main.BaseSettings
    * pydantic.main.BaseModel

    ### Descendants

    * madsci.common.types.client_types.DataClientConfig
    * madsci.common.types.client_types.ExperimentClientConfig
    * madsci.common.types.client_types.LabClientConfig
    * madsci.common.types.client_types.LocationClientConfig
    * madsci.common.types.client_types.ResourceClientConfig
    * madsci.common.types.client_types.RestNodeClientConfig
    * madsci.common.types.client_types.WorkcellClientConfig
    * madsci.common.types.event_types.EventClientConfig

    ### Class variables

    `pool_connections: int`
    :

    `pool_maxsize: int`
    :

    `rate_limit_respect_limits: bool`
    :

    `rate_limit_tracking_enabled: bool`
    :

    `rate_limit_warning_threshold: float`
    :

    `retry_allowed_methods: list[str] | None`
    :

    `retry_backoff_factor: float`
    :

    `retry_enabled: bool`
    :

    `retry_status_forcelist: list[int]`
    :

    `retry_total: int`
    :

    `timeout_data_operations: float`
    :

    `timeout_default: float`
    :

    `timeout_long_operations: float`
    :

`ResourceClientConfig(**values: Any)`
:   Configuration for the Resource Manager client.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.client_types.MadsciClientConfig
    * madsci.common.types.base_types.MadsciBaseSettings
    * pydantic_settings.main.BaseSettings
    * pydantic.main.BaseModel

`RestNodeClientConfig(**values: Any)`
:   Configuration for Node REST clients.

    Node clients handle action operations (create, upload, start, download)
    that may require extended timeouts.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.client_types.MadsciClientConfig
    * madsci.common.types.base_types.MadsciBaseSettings
    * pydantic_settings.main.BaseSettings
    * pydantic.main.BaseModel

    ### Class variables

    `timeout_data_operations: float`
    :

`WorkcellClientConfig(**values: Any)`
:   Configuration for the Workcell Manager client.

    The Workcell Manager handles workflow queries that may require extended timeouts.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.client_types.MadsciClientConfig
    * madsci.common.types.base_types.MadsciBaseSettings
    * pydantic_settings.main.BaseSettings
    * pydantic.main.BaseModel
