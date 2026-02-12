Module madsci.common.utils
==========================
Utilities for the MADSci project.

Functions
---------

`create_http_session(config: ForwardRef('MadsciClientConfig') | None = None, retry_enabled: bool | None = None) ‑> requests.Session`
:   Create a requests.Session with standardized configuration.

    This function creates a properly configured requests session with retry
    strategies, timeout defaults, connection pooling, and rate limit tracking
    based on the provided client configuration. This ensures consistency across
    all MADSci HTTP clients.

    The session includes rate limit tracking if enabled in the config. Rate limit
    information is tracked from X-RateLimit-* headers and can be accessed via
    the session.rate_limit_tracker attribute.

    Args:
        config: Client configuration object. If None, uses default MadsciClientConfig.
        retry_enabled: Override for retry_enabled from config. If None, uses config value.

    Returns:
        Configured requests.Session object with optional rate_limit_tracker attribute

    Example:
        >>> from madsci.common.types.client_types import MadsciClientConfig
        >>> from madsci.common.utils import create_http_session
        >>>
        >>> # Use default configuration
        >>> session = create_http_session()
        >>>
        >>> # Use custom configuration
        >>> config = MadsciClientConfig(retry_total=5, timeout_default=30.0)
        >>> session = create_http_session(config=config)
        >>>
        >>> # Disable retry for a specific session
        >>> session_no_retry = create_http_session(config=config, retry_enabled=False)
        >>>
        >>> # Check rate limit status
        >>> if hasattr(session, 'rate_limit_tracker'):
        ...     status = session.rate_limit_tracker.get_status()
        ...     print(f"Remaining requests: {status['remaining']}/{status['limit']}")

`extract_datapoint_ids(data: Any) ‑> list[str]`
:   Extract all datapoint IDs from a data structure.

    Recursively searches through dictionaries, lists, and objects to find
    datapoint IDs (ULID strings that are likely datapoints).

    Args:
        data: Data structure to search

    Returns:
        List of unique datapoint IDs found

`is_annotated(type_hint: Any) ‑> bool`
:   Check if a type hint is an annotated type.

`is_optional(type_hint: Any) ‑> bool`
:   Check if a type hint is Optional.

`is_valid_ulid(value: str) ‑> bool`
:   Check if a string is a valid ULID.

    Args:
        value: String to validate

    Returns:
        True if the string is a valid ULID format

`localnow() ‑> datetime.datetime`
:   Return the current local time.

`new_name_str(prefix: str = '') ‑> str`
:   Generate a new random name string, optionally with a prefix. Make a random combination of an adjective and a noun. Names are not guaranteed to be unique.

`new_ulid_str() ‑> str`
:   Generate a new ULID string.

`pretty_type_repr(type_hint: Any) ‑> str`
:   Returns a pretty string representation of a type hint, including subtypes.

`prompt_for_input(prompt: str, default: str | None = None, required: bool = False, quiet: bool = False) ‑> str`
:   Prompt the user for input.

`prompt_from_list(prompt: str, options: list[str], default: str | None = None, required: bool = False, quiet: bool = False) ‑> str`
:   Prompt the user for input from a list of options.

`prompt_from_pydantic_model(model: MadsciBaseModel, prompt: str, **kwargs: Any) ‑> str`
:   Prompt the user for input from a pydantic model.

    Args:
        model: The pydantic model to prompt for
        prompt: The prompt to display
        **kwargs: Pre-filled values to skip prompting for

    Returns:
        A dictionary of field values for the model

`prompt_yes_no(prompt: str, default: str = 'no', quiet: bool = False) ‑> bool`
:   Prompt the user for a yes or no answer.

`relative_path(source: pathlib.Path, target: pathlib.Path, walk_up: bool = True) ‑> pathlib.Path`
:   "Backport" of :meth:`pathlib.Path.relative_to` with ``walk_up=True``
    that's not available pre 3.12.

    Return the relative path to another path identified by the passed
    arguments.  If the operation is not possible (because this is not
    related to the other path), raise ValueError.

    The *walk_up* parameter controls whether `..` may be used to resolve
    the path.

    References:
        https://github.com/python/cpython/blob/8a2baedc4bcb606da937e4e066b4b3a18961cace/Lib/pathlib/_abc.py#L244-L270
    Credit: https://github.com/p2p-ld/numpydantic/blob/66fffc49f87bfaaa2f4d05bf1730c343b10c9cc6/src/numpydantic/serialization.py#L107

`repeat_on_interval(interval: float, func: <built-in function callable>, *args: Any, **kwargs: Any) ‑> None`
:   Repeat a function on an interval.

`save_model(path: PathLike, model: MadsciBaseModel, overwrite_check: bool = True)`
:   Save a MADSci model to a YAML file, optionally with a check to overwrite if the file already exists.

`search_for_file_pattern(pattern: str, start_dir: ForwardRef('PathLike') | None = None, parents: bool = True, children: bool = True) ‑> list[str]`
:   Search up and down the file tree for a file(s) matching a pattern.

    Args:
        pattern: The pattern to search for. Standard glob patterns are supported.
        start_dir: The directory to start the search in. Defaults to the current directory.
        parents: Whether to search in parent directories.
        children: Whether to search in subdirectories.

    Returns:
        A list of paths to the files that match the pattern.

`string_to_bool(string: str) ‑> bool`
:   Convert a string to a boolean value.

`threaded_daemon(func: <built-in function callable>) ‑> <built-in function callable>`
:   Mark a function as a threaded daemon, to be run without awaiting. Returns the thread object, so you _can_ await if needed, and stops when the calling thread terminates.

`threaded_task(func: <built-in function callable>) ‑> <built-in function callable>`
:   Mark a function as a threaded task, to be run without awaiting. Returns the thread object, so you _can_ await if needed.

`to_snake_case(name: str) ‑> str`
:   Convert a string to snake case.

    Handles conversion from camelCase and PascalCase to snake_case.

`utcnow() ‑> datetime.datetime`
:   Return the current UTC time.

Classes
-------

`RateLimitHTTPAdapter(rate_limit_tracker: madsci.common.utils.RateLimitTracker, *args: Any, **kwargs: Any)`
:   HTTP adapter that handles rate limit headers and delays.

    This adapter extends HTTPAdapter to add rate limit tracking and
    automatic delay enforcement when approaching or exceeding rate limits.

    Initialize the rate limit adapter.

    Args:
        rate_limit_tracker: Tracker to update with rate limit information
        *args: Positional arguments for HTTPAdapter
        **kwargs: Keyword arguments for HTTPAdapter

    ### Methods

    `close(self) ‑> None`
    :   Close the underlying adapter.

    `send(self, request: Any, **kwargs: Any) ‑> Any`
    :   Send a request with rate limit checking and tracking.

        Args:
            request: The request to send
            **kwargs: Additional arguments for the adapter

        Returns:
            The response from the adapter

`RateLimitTracker(warning_threshold: float = 0.8, respect_limits: bool = False)`
:   Track rate limit state from HTTP response headers.

    This class maintains rate limit information from server responses and provides
    utilities for logging warnings and determining if requests should be delayed.

    Attributes:
        limit: Maximum number of requests allowed in the time window
        remaining: Number of requests remaining in the current window
        reset: Unix timestamp when the rate limit resets
        burst_limit: Maximum number of requests allowed in short burst window (optional)
        burst_remaining: Number of burst requests remaining (optional)
        warning_threshold: Fraction of limit at which to warn (0.0 to 1.0)
        respect_limits: Whether to enforce delays when approaching limits

    Initialize the rate limit tracker.

    Args:
        warning_threshold: Threshold (0.0 to 1.0) at which to log warnings
        respect_limits: Whether to enforce delays when approaching limits

    ### Methods

    `get_delay_seconds(self) ‑> float`
    :   Calculate delay in seconds before next request if respect_limits is enabled.

        Returns:
            Number of seconds to delay, or 0.0 if no delay needed

    `get_status(self) ‑> dict[str, typing.Any]`
    :   Get current rate limit status.

        Returns:
            Dictionary with current rate limit information

    `update_from_headers(self, headers: dict[str, str]) ‑> None`
    :   Update rate limit state from response headers.

        Args:
            headers: HTTP response headers dictionary
