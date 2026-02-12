Module madsci.client.structlog_config
=====================================
Structlog configuration for EventClient.

This module provides per-instance structlog configuration using wrap_logger()
to ensure multiple EventClient instances can have isolated configurations.

Functions
---------

`add_event_client_hierarchy(_logger: logging.Logger, _method_name: str, event_dict: dict[str, typing.Any]) ‑> dict[str, typing.Any]`
:   Add EventClient hierarchy information to log events.

    This processor adds madsci.hierarchy and madsci.* metadata fields
    when an EventClientContext is active.

    Args:
        _logger: The stdlib logger (unused but required by structlog API)
        _method_name: The log method name (unused but required by structlog API)
        event_dict: The event dictionary to enrich

    Returns:
        The enriched event dictionary with hierarchy and metadata fields.

`add_otel_context(logger: Any, method_name: str, event_dict: MutableMapping[str, Any]) ‑> MutableMapping[str, Any]`
:   Structlog processor that adds OpenTelemetry trace context to log events.

    This processor extracts the current span's trace context and adds trace_id
    and span_id fields to the log event dictionary. This enables correlation
    between logs and distributed traces in observability backends.

    If no active span exists or the span is not recording, the trace context
    fields will not be added.

    Args:
        logger: The wrapped logger object (unused, required by structlog API).
        method_name: The name of the log method called (unused, required by structlog API).
        event_dict: The event dictionary being processed.

    Returns:
        The event dictionary with trace context added.

    Example:
        # Configure structlog with this processor
        import structlog

        structlog.configure(
            processors=[
                structlog.processors.add_log_level,
                add_otel_context,
                structlog.dev.ConsoleRenderer(),
            ],
        )

        # Create a span and log within it
        from opentelemetry import trace

        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("my-operation"):
            logger = structlog.get_logger()
            logger.info("Processing request")
            # Log includes trace_id and span_id

`build_processors(output_format: Literal['json', 'console'] = 'console', add_timestamp: bool = True, include_otel_context: bool = False, include_hierarchy_context: bool = False) ‑> list[typing.Callable[[typing.Any, str, typing.MutableMapping[str, typing.Any]], Mapping[str, Any] | str | bytes | bytearray | Tuple[Any, ...]]]`
:   Build structlog processor pipeline.

    Args:
        output_format: Output format - "json" for machine-readable, "console" for human-readable
        add_timestamp: Whether to add ISO timestamps to logs
        include_otel_context: Whether to include OpenTelemetry trace context
        include_hierarchy_context: Whether to include EventClient hierarchy context

    Returns:
        List of processors for structlog configuration

`create_instance_logger(name: str, output_format: Literal['json', 'console'] = 'console', log_level: int = 20, include_otel_context: bool = False, include_hierarchy_context: bool = False, add_timestamp: bool = True) ‑> structlog.typing.FilteringBoundLogger`
:   Create a per-instance structlog logger.

    Uses structlog.wrap_logger() to avoid global configuration conflicts
    when multiple EventClient instances have different configurations.

    Args:
        name: Logger name (typically the client name)
        output_format: Output format for logs ("json" or "console")
        log_level: Minimum log level to emit
        include_otel_context: Whether to include OTEL trace context
        include_hierarchy_context: Whether to include EventClient hierarchy context
        add_timestamp: Whether to add timestamps to log entries

    Returns:
        A wrapped logger instance with its own processor pipeline

`get_log_level_value(level: Any) ‑> int`
:   Convert various log level representations to integer value.

    Args:
        level: Log level as int, string, or EventLogLevel enum

    Returns:
        Integer log level value
