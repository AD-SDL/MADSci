"""OpenTelemetry processors for structlog integration.

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
"""

from typing import Any

import structlog
from opentelemetry import trace


def add_otel_context(
    logger: Any,  # noqa: ARG001
    method_name: str,  # noqa: ARG001
    event_dict: structlog.typing.EventDict,
) -> structlog.typing.EventDict:
    """Structlog processor that adds OpenTelemetry trace context to log events.

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
    """
    span = trace.get_current_span()
    if not span.is_recording():
        return event_dict

    ctx = span.get_span_context()

    # Add trace context in standard OTEL format
    event_dict["trace_id"] = format(ctx.trace_id, "032x")
    event_dict["span_id"] = format(ctx.span_id, "016x")

    # Optionally add parent span if available
    parent = getattr(span, "parent", None)
    if parent:
        event_dict["parent_span_id"] = format(parent.span_id, "016x")

    return event_dict


def add_otel_span_info(
    logger: Any,  # noqa: ARG001
    method_name: str,  # noqa: ARG001
    event_dict: structlog.typing.EventDict,
) -> structlog.typing.EventDict:
    """Structlog processor that adds detailed OpenTelemetry span information.

    This is an extended version of add_otel_context that includes additional
    span information such as the span name and whether it's sampled.

    Args:
        logger: The wrapped logger object (unused, required by structlog API).
        method_name: The name of the log method called (unused, required by structlog API).
        event_dict: The event dictionary being processed.

    Returns:
        The event dictionary with detailed span information added.
    """
    span = trace.get_current_span()
    if not span.is_recording():
        return event_dict

    ctx = span.get_span_context()

    # Add span as nested dict for more detailed info
    event_dict["otel"] = {
        "trace_id": format(ctx.trace_id, "032x"),
        "span_id": format(ctx.span_id, "016x"),
        "trace_flags": ctx.trace_flags,
        "is_remote": ctx.is_remote,
    }

    # Add span name if available
    if hasattr(span, "name"):
        event_dict["otel"]["span_name"] = span.name

    # Add parent info
    parent = getattr(span, "parent", None)
    if parent:
        event_dict["otel"]["parent_span_id"] = format(parent.span_id, "016x")

    return event_dict
