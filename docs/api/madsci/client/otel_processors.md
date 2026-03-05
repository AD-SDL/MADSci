Module madsci.client.otel_processors
====================================
OpenTelemetry processors for structlog integration.

This module provides structlog processors that add OpenTelemetry trace context
to log entries, enabling correlation between logs and distributed traces.

Example usage:
    import structlog
    from madsci.client.otel_processors import add_otel_context

    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            add_otel_context,  # Add trace context to logs
            structlog.processors.JSONRenderer(),
        ],
    )

    logger = structlog.get_logger()
    logger.info("Event logged", event_id="123")
    # Output includes trace_id and span_id if within a span

Functions
---------

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

`add_otel_span_info(logger: Any, method_name: str, event_dict: MutableMapping[str, Any]) ‑> MutableMapping[str, Any]`
:   Structlog processor that adds detailed OpenTelemetry span information.
    
    This is an extended version of add_otel_context that includes additional
    span information such as the span name and whether it's sampled.
    
    Args:
        logger: The wrapped logger object (unused, required by structlog API).
        method_name: The name of the log method called (unused, required by structlog API).
        event_dict: The event dictionary being processed.
    
    Returns:
        The event dictionary with detailed span information added.