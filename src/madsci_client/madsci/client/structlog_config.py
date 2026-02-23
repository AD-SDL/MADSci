"""Structlog configuration for EventClient.

This module provides per-instance structlog configuration using wrap_logger()
to ensure multiple EventClient instances can have isolated configurations.
"""

import logging
import re
from typing import Any, Literal

import structlog

# Import the canonical OTEL context processor from otel_processors
# This provides trace_id and span_id injection into log events
from madsci.client.otel_processors import add_otel_context


def add_event_client_hierarchy(
    _logger: logging.Logger,
    _method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """
    Add EventClient hierarchy information to log events.

    This processor adds madsci.hierarchy and madsci.* metadata fields
    when an EventClientContext is active.

    Args:
        _logger: The stdlib logger (unused but required by structlog API)
        _method_name: The log method name (unused but required by structlog API)
        event_dict: The event dictionary to enrich

    Returns:
        The enriched event dictionary with hierarchy and metadata fields.
    """
    from madsci.common.context import get_event_client_context  # noqa: PLC0415

    ctx = get_event_client_context()
    if ctx is not None:
        if ctx.hierarchy:
            event_dict["madsci.hierarchy"] = ctx.name
        for key, value in ctx.metadata.items():
            event_dict[f"madsci.{key}"] = value

    return event_dict


class AnsiStrippingFormatter(logging.Formatter):
    """Logging formatter that strips ANSI escape codes for clean file output.

    Use this on file handlers to prevent color codes from polluting log files
    when structlog's ConsoleRenderer is used with colors=True.
    """

    _ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record, stripping any ANSI escape codes."""
        formatted = super().format(record)
        return self._ANSI_RE.sub("", formatted)


__all__ = [
    "AnsiStrippingFormatter",
    "add_event_client_hierarchy",
    "add_otel_context",
    "build_processors",
    "create_instance_logger",
    "get_log_level_value",
]


def build_processors(
    output_format: Literal["json", "console"] = "console",
    add_timestamp: bool = True,
    include_otel_context: bool = False,
    include_hierarchy_context: bool = False,
) -> list[structlog.typing.Processor]:
    """Build structlog processor pipeline.

    Args:
        output_format: Output format - "json" for machine-readable, "console" for human-readable
        add_timestamp: Whether to add ISO timestamps to logs
        include_otel_context: Whether to include OpenTelemetry trace context
        include_hierarchy_context: Whether to include EventClient hierarchy context

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

    # Add EventClient hierarchy context if enabled
    if include_hierarchy_context:
        processors.append(add_event_client_hierarchy)

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
    include_hierarchy_context: bool = False,
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
        include_hierarchy_context: Whether to include EventClient hierarchy context
        add_timestamp: Whether to add timestamps to log entries

    Returns:
        A wrapped logger instance with its own processor pipeline
    """
    processors = build_processors(
        output_format=output_format,
        include_otel_context=include_otel_context,
        include_hierarchy_context=include_hierarchy_context,
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
