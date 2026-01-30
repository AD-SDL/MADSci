"""Structlog configuration for EventClient.

This module provides per-instance structlog configuration using wrap_logger()
to ensure multiple EventClient instances can have isolated configurations.
"""

import logging
from typing import Any, Literal

import structlog
from opentelemetry import trace


def add_otel_context(
    _logger: Any, _method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Structlog processor to add OpenTelemetry trace context to logs.

    Args:
        _logger: The wrapped logger object (unused, required by structlog processor interface).
        _method_name: Name of the method called on the logger (unused, required by structlog processor interface).
        event_dict: The event dictionary being processed.

    Returns:
        The event dictionary with trace context added (if available).
    """
    span = trace.get_current_span()
    if span.is_recording():
        ctx = span.get_span_context()
        event_dict["trace_id"] = format(ctx.trace_id, "032x")
        event_dict["span_id"] = format(ctx.span_id, "016x")
    return event_dict


def build_processors(
    output_format: Literal["json", "console"] = "console",
    add_timestamp: bool = True,
    include_otel_context: bool = False,
) -> list[structlog.typing.Processor]:
    """Build structlog processor pipeline.

    Args:
        output_format: Output format - "json" for machine-readable, "console" for human-readable
        add_timestamp: Whether to add ISO timestamps to logs
        include_otel_context: Whether to include OpenTelemetry trace context

    Returns:
        List of processors for structlog configuration
    """
    processors: list[structlog.typing.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
    ]

    if add_timestamp:
        processors.append(structlog.processors.TimeStamper(fmt="iso"))

    processors.extend(
        [
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
        ]
    )

    # Add OTEL context if enabled
    if include_otel_context:
        processors.append(add_otel_context)

    # Final renderer based on output format
    if output_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(
            structlog.dev.ConsoleRenderer(
                colors=True,
                exception_formatter=structlog.dev.plain_traceback,
            )
        )

    return processors


def create_instance_logger(
    name: str,
    output_format: Literal["json", "console"] = "console",
    log_level: int = logging.INFO,
    include_otel_context: bool = False,
    add_timestamp: bool = True,
) -> structlog.typing.FilteringBoundLogger:
    """Create a per-instance structlog logger.

    Uses structlog.wrap_logger() to avoid global configuration conflicts
    when multiple EventClient instances have different configurations.

    Args:
        name: Logger name (typically the client name)
        output_format: Output format for logs ("json" or "console")
        log_level: Minimum log level to emit
        include_otel_context: Whether to include OTEL trace context
        add_timestamp: Whether to add timestamps to log entries

    Returns:
        A wrapped logger instance with its own processor pipeline
    """
    processors = build_processors(
        output_format=output_format,
        include_otel_context=include_otel_context,
        add_timestamp=add_timestamp,
    )

    # Create a stdlib logger as the underlying logger
    stdlib_logger = logging.getLogger(name)
    stdlib_logger.setLevel(log_level)

    # Wrap with structlog processors - this is instance-specific
    # and does NOT modify global structlog configuration
    return structlog.wrap_logger(
        stdlib_logger,
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        cache_logger_on_first_use=False,  # Don't cache to allow different configs
    )


def get_log_level_value(level: Any) -> int:
    """Convert various log level representations to integer value.

    Args:
        level: Log level as int, string, or EventLogLevel enum

    Returns:
        Integer log level value
    """
    if isinstance(level, int):
        return level
    if hasattr(level, "value"):
        return level.value
    if isinstance(level, str):
        return getattr(logging, level.upper(), logging.INFO)
    return logging.INFO
