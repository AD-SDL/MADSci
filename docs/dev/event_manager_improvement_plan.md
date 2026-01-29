# EventClient/EventManager Improvements Development Plan

> **Meta Issue:** [#218 - Meta: Event Client/Manager Improvements](https://github.com/AD-SDL/MADSci/issues/218)
> **Created:** January 2026
> **Status:** In Progress (Phase 3 Complete)

## Overview

This document outlines a phased, test-driven development plan for improving MADSci's EventClient and EventManager components. The work addresses four related GitHub issues:

| Issue | Title | Type | Priority |
|-------|-------|------|----------|
| [#217](https://github.com/AD-SDL/MADSci/issues/217) | Feature: Automatic Logging Info | Enhancement | High |
| [#216](https://github.com/AD-SDL/MADSci/issues/216) | Feature: StructLog Support | Enhancement | High |
| [#215](https://github.com/AD-SDL/MADSci/issues/215) | Research: OpenTelemetry and the EventManager | Research | Medium |
| [#80](https://github.com/AD-SDL/MADSci/issues/80) | Enhancement: Event/Log Rotation, Retention, and Backup | Enhancement | Medium |

## Design Decisions

The following decisions were made during planning:

1. **OpenTelemetry Research Output**: Both a research document and proof-of-concept implementation
2. **Event Retention Strategy**: Configurable soft-delete → hard-delete workflow using MongoDB TTL indexes
3. **Structlog API**: Idiomatic structlog API as default (`logger.info()`, `logger.debug()`), with `log_*` aliases for backward compatibility
4. **Structlog Configuration Scope**: Per-instance configuration using `structlog.wrap_logger()` for full isolation
5. **Error Handling**: Configurable behavior via `fail_on_error` setting (default: silent logging)
6. **Bulk Operations**: Batch limits with configurable size to prevent performance impact
7. **Test Coverage Target**: Comprehensive (~80%+ coverage with unit, integration, and edge case tests)
8. **Breaking Changes**: Acceptable where they improve functionality, usability, and feature set

## Architecture Context

### Key Files

| File | Purpose |
|------|---------|
| `src/madsci_client/madsci/client/event_client.py` | EventClient implementation |
| `src/madsci_event_manager/madsci/event_manager/event_server.py` | EventManager server |
| `src/madsci_common/madsci/common/types/event_types.py` | Event, EventType, Settings, Config types |
| `src/madsci_client/tests/test_event_client.py` | EventClient unit tests |
| `src/madsci_event_manager/tests/test_event_server.py` | EventManager unit tests |

### Current Architecture Notes

- **EventClient is dual-purpose**: Both a Python logger AND an HTTP client to the EventManager
- **Asynchronous sending**: Events are sent to server in background threads with retry logic
- **Fallback behavior**: If no event server, events are still logged locally to files
- **MongoDB storage**: Events stored in MongoDB with ULID as `_id`
- **Bespoke context binding**: Current implementation has custom context handling that can be replaced by structlog's native features

---

## Phase 1: Foundation & Quick Wins

**Target Issues:** [#217](https://github.com/AD-SDL/MADSci/issues/217) (Automatic Logging Info)
**Estimated Effort:** Small (1-2 days)
**Breaking Changes:** None

### Goals

- Log MADSci version, configuration, and environment info on EventClient initialization
- Establish patterns for subsequent phases

### Requirements

The EventClient should automatically log useful details the first time it's initialized:

- MADSci version (from package metadata)
- Client name and configuration summary
- Event server URL (if configured)
- Log directory path
- Python version and platform info

### Implementation Tasks

#### 1.1 Write Tests First

Add tests to `src/madsci_client/tests/test_event_client.py`:

```python
class TestEventClientStartupLogging:
    """Test EventClient startup logging behavior."""

    def test_logs_version_on_init(self, config_without_server):
        """Test that MADSci version is logged on initialization."""
        # Verify version info appears in log output
        pass

    def test_logs_config_summary_on_init(self, config_without_server):
        """Test that configuration summary is logged on initialization."""
        # Verify config details appear in log output
        pass

    def test_logs_event_server_url_when_configured(self, config_with_server, temp_log_dir):
        """Test that event server URL is logged when configured."""
        pass

    def test_startup_logging_only_once(self, config_without_server):
        """Test that startup info is only logged once per client instance."""
        pass
```

#### 1.2 Implement Version Detection

Add version detection utility:

```python
# In event_client.py or a new utils module
from importlib.metadata import version, PackageNotFoundError

def get_madsci_version() -> str:
    """Get the installed MADSci version."""
    try:
        return version("madsci_client")
    except PackageNotFoundError:
        return "unknown (development mode)"
```

#### 1.3 Implement Startup Logging

Add `_log_startup_info()` method to EventClient (implemented in `src/madsci_client/madsci/client/event_client.py`):

```python
def _log_startup_info(self) -> None:
    """Log startup information on first initialization.

    Logs MADSci version, client configuration, and environment info
    to help with debugging and auditing.
    """
    startup_info = {
        "madsci_version": get_madsci_version(),
        "client_name": self.name,
        "event_server": str(self.event_server) if self.event_server else "Not configured",
        "log_dir": str(self.log_dir),
        "log_level": self.config.log_level.name if hasattr(self.config.log_level, "name") else str(self.config.log_level),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
    }

    self.logger.info(f"EventClient initialized: {startup_info}")
```

**Note:** The implementation logs at INFO level (not DEBUG as originally planned) so startup info is visible by default.

### Acceptance Criteria

- [x] MADSci version is logged on EventClient initialization
- [x] Configuration summary is logged
- [x] All new tests pass
- [x] Existing tests continue to pass

---

## Phase 2: Python Log Rotation & Retention

**Target Issues:** [#80](https://github.com/AD-SDL/MADSci/issues/80) (Part 1 - Python Logging)
**Estimated Effort:** Medium (2-3 days)
**Breaking Changes:** Minor (new config options)

### Goals

- Add log rotation using Python's `RotatingFileHandler` or `TimedRotatingFileHandler`
- Support configurable retention policies
- Support optional log compression

### Requirements

From issue #80:

> - Add support and default policies for log retention and rotation using python's native logger functionality.
> - For rotation, should use `RotatingFileHandler` or `TimedRotatingFileHandler`
> - Can we support log compression?

### Implementation Tasks

#### 2.1 Extend EventClientConfig

Add rotation configuration to `src/madsci_common/madsci/common/types/event_types.py`:

```python
from typing import Literal

class EventClientConfig(MadsciClientConfig):
    # ... existing fields ...

    # Log rotation settings
    log_rotation_type: Literal["size", "time", "none"] = Field(
        default="size",
        description="Type of log rotation: 'size' (RotatingFileHandler), 'time' (TimedRotatingFileHandler), or 'none'"
    )
    log_max_bytes: int = Field(
        default=10_485_760,  # 10MB
        description="Maximum log file size in bytes before rotation (for size-based rotation)"
    )
    log_backup_count: int = Field(
        default=5,
        description="Number of backup log files to keep"
    )
    log_rotation_when: str = Field(
        default="midnight",
        description="When to rotate logs (for time-based rotation): 'S', 'M', 'H', 'D', 'midnight', 'W0'-'W6'"
    )
    log_rotation_interval: int = Field(
        default=1,
        description="Interval for time-based rotation"
    )
    log_compression_enabled: bool = Field(
        default=True,
        description="Whether to compress rotated log files with gzip"
    )
```

#### 2.2 Write Tests First

Add tests to `src/madsci_client/tests/test_event_client.py`:

```python
class TestEventClientLogRotation:
    """Test EventClient log rotation functionality."""

    def test_size_based_rotation(self, temp_log_dir):
        """Test that logs rotate when max size is reached."""
        pass

    def test_time_based_rotation(self, temp_log_dir):
        """Test that logs rotate based on time interval."""
        pass

    def test_backup_count_limit(self, temp_log_dir):
        """Test that only specified number of backups are kept."""
        pass

    def test_log_compression(self, temp_log_dir):
        """Test that rotated logs are compressed with gzip."""
        pass

    def test_rotation_disabled(self, temp_log_dir):
        """Test that rotation can be disabled."""
        pass

    def test_default_rotation_config(self, temp_log_dir):
        """Test default rotation configuration is applied."""
        pass
```

#### 2.3 Implement Rotation Handler Selection

Update EventClient initialization to select appropriate handler:

```python
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import gzip
import shutil

def _create_file_handler(self) -> logging.Handler:
    """Create the appropriate file handler based on rotation config."""
    if self.config.log_rotation_type == "none":
        return logging.FileHandler(filename=str(self.logfile), mode="a+")

    elif self.config.log_rotation_type == "size":
        handler = RotatingFileHandler(
            filename=str(self.logfile),
            maxBytes=self.config.log_max_bytes,
            backupCount=self.config.log_backup_count,
        )

    elif self.config.log_rotation_type == "time":
        handler = TimedRotatingFileHandler(
            filename=str(self.logfile),
            when=self.config.log_rotation_when,
            interval=self.config.log_rotation_interval,
            backupCount=self.config.log_backup_count,
        )

    if self.config.log_compression_enabled:
        handler.rotator = self._compress_rotated_log
        handler.namer = self._rotated_log_namer

    return handler

def _compress_rotated_log(self, source: str, dest: str) -> None:
    """Compress a rotated log file with gzip."""
    with open(source, 'rb') as f_in:
        with gzip.open(dest, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
    os.remove(source)

def _rotated_log_namer(self, name: str) -> str:
    """Add .gz extension to rotated log file names."""
    return name + ".gz"
```

#### 2.4 Integrate Handler into Logger Setup

Update the logger initialization to use the new handler:

```python
def _setup_file_logging(self) -> None:
    """Set up file logging with rotation support."""
    import os

    # Ensure log directory exists
    self.log_dir.mkdir(parents=True, exist_ok=True)

    # Create the appropriate file handler
    file_handler = self._create_file_handler()

    # Set formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(self.config.log_level.value)

    # Attach to logger
    self.logger.addHandler(file_handler)
```

**Note:** The `os` import is needed for `os.remove()` in `_compress_rotated_log()`.

### Acceptance Criteria

- [x] Size-based log rotation works correctly
- [x] Time-based log rotation works correctly
- [x] Backup count limits are enforced
- [x] Log compression produces valid gzip files
- [x] Rotation can be disabled via config
- [x] All new tests pass
- [x] Existing tests continue to pass

---

## Phase 3: OpenTelemetry Research

**Target Issues:** [#215](https://github.com/AD-SDL/MADSci/issues/215)
**Estimated Effort:** Medium (3-5 days)
**Deliverables:** Research document + proof-of-concept

### Goals

- Understand OTEL integration options for MADSci
- Evaluate structlog's OTEL processors
- Create working PoC demonstrating traces, metrics, logs correlation

### Research Topics

#### 3.1 OpenTelemetry Python SDK

- **Traces API**: How to create spans, propagate context
- **Metrics API**: Counters, gauges, histograms for event statistics
- **Logs API**: Integration with Python logging and structlog
- **Context propagation**: How trace context flows through async operations

#### 3.2 Structlog + OpenTelemetry Integration

- Native OTEL processors available in structlog
- How to inject trace_id/span_id into log records
- Context propagation through bound loggers

#### 3.3 Distributed Tracing in MADSci

How trace context should flow through:

```
Experiment Application
    → Workcell Manager (workflow submission)
        → Node Module (action execution)
            → Resource Manager (resource allocation)
        → Event Manager (event logging)
    → Data Manager (data capture)
```

#### 3.4 OTEL Exporters

Evaluate exporter options:

- **Console**: For development/debugging
- **OTLP**: Standard protocol for production
- **Jaeger**: Popular tracing backend
- **Prometheus**: For metrics

#### 3.5 Integration Patterns

- How to correlate Events with traces
- Should Event.event_id be related to span_id?
- How to add trace context to HTTP requests between components

### Proof-of-Concept Scope

Create a PoC branch demonstrating:

1. **Basic tracing** in EventClient
   - Create span on client initialization
   - Create child spans for event logging operations
   - Propagate trace context to EventManager

2. **Log correlation**
   - Inject trace_id into log records
   - Inject trace_id into Event objects

3. **Basic metrics**
   - Event count by type
   - Event logging latency histogram
   - Buffer size gauge

4. **Console exporter** for easy demonstration

### Deliverables

1. **Research Document**: `docs/dev/opentelemetry_research.md`
   - Summary of OTEL concepts
   - Recommended integration approach
   - Trade-offs and considerations
   - Configuration recommendations

2. **Proof-of-Concept Branch**: `feature/otel-poc`
   - Working OTEL integration in EventClient
   - Example trace output
   - README with instructions to run PoC

### PoC Branch Disposition

The fate of the `feature/otel-poc` branch will be decided after Phase 4 implementation begins:

| Scenario | Action |
|----------|--------|
| PoC code is clean and directly usable | Merge PoC into Phase 4 PR |
| PoC needs significant rework | Keep as reference, implement fresh in Phase 4 |
| OTEL integration deferred | Archive branch for future use |

This decision will be documented in the Phase 4 PR description.

### Acceptance Criteria

- [x] Research document completed
- [x] PoC demonstrates trace propagation
- [x] PoC demonstrates log correlation with traces
- [x] PoC demonstrates basic metrics collection
- [x] Recommendations provided for Phase 4 integration
- [x] PoC includes assessment of code reusability for Phase 4

---

## Phase 4: Structlog Migration

**Target Issues:** [#216](https://github.com/AD-SDL/MADSci/issues/216)
**Estimated Effort:** Large (5-7 days)
**Breaking Changes:** Yes (API changes, new dependency)

### Goals

- Replace Python `logging` with `structlog` as backend
- Use idiomatic structlog API as default
- Provide `log_*` aliases for backward compatibility
- Leverage structlog's built-in features (context binding, processors)
- Integrate OTEL findings from Phase 3

### Requirements

From issue #216:

> Switch to the `structlog` python library as a python logging backend for the EventClient.

### Background: Why Structlog?

1. **Structured logging**: Native JSON output, key-value context
2. **Context binding**: `logger.bind(workflow_id=..., node_id=...)` automatically includes context in all subsequent logs
3. **Processor pipeline**: Composable log processing (timestamps, formatting, filtering)
4. **OTEL integration**: Native processors for trace context injection
5. **Performance**: Lazy evaluation, efficient serialization

### Implementation Tasks

#### 4.1 Add Structlog Dependency

Update `src/madsci_client/pyproject.toml`:

```toml
dependencies = [
    # ... existing deps ...
    "structlog>=24.1.0",
]
```

#### 4.2 Write Tests First

Create new test file or extend existing:

```python
class TestEventClientStructlog:
    """Test EventClient with structlog backend."""

    def test_basic_info_logging(self, config_without_server):
        """Test basic info logging with structlog."""
        pass

    def test_context_binding(self, config_without_server):
        """Test that bound context appears in logs."""
        client = EventClient(config=config_without_server)
        bound_client = client.bind(workflow_id="wf-123", node_id="node-456")
        bound_client.info("Processing step")
        # Verify workflow_id and node_id appear in output
        pass

    def test_nested_context_binding(self, config_without_server):
        """Test nested context binding accumulates context."""
        pass

    def test_json_output_format(self, config_without_server):
        """Test JSON output format."""
        pass

    def test_console_output_format(self, config_without_server):
        """Test console (human-readable) output format."""
        pass

    def test_exception_logging(self, config_without_server):
        """Test exception info is properly captured."""
        pass

    def test_backward_compat_log_info(self, config_without_server):
        """Test log_info() alias works."""
        pass

    def test_backward_compat_log_error(self, config_without_server):
        """Test log_error() alias works."""
        pass

    def test_multiple_clients_isolated_config(self, temp_log_dir):
        """Test that multiple EventClient instances have isolated configurations."""
        json_config = EventClientConfig(name="json_client", log_output_format="json")
        console_config = EventClientConfig(name="console_client", log_output_format="console")

        json_client = EventClient(config=json_config)
        console_client = EventClient(config=console_config)

        # Verify each client uses its own format
        # (implementation verifies output format differs)
        pass
```

#### 4.3 Create Structlog Configuration

Add structlog configuration module with **per-instance configuration** using `structlog.wrap_logger()`:

```python
# src/madsci_client/madsci/client/structlog_config.py

import structlog
from structlog.typing import Processor, WrappedLogger
from typing import Literal
import logging

def build_processors(
    output_format: Literal["json", "console"] = "console",
    add_timestamp: bool = True,
    include_otel_context: bool = False,
) -> list[Processor]:
    """Build structlog processor pipeline.

    Args:
        output_format: Output format - "json" for machine-readable, "console" for human-readable
        add_timestamp: Whether to add ISO timestamps to logs
        include_otel_context: Whether to include OpenTelemetry trace context

    Returns:
        List of processors for structlog configuration
    """
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
    ]

    if add_timestamp:
        processors.append(structlog.processors.TimeStamper(fmt="iso"))

    processors.extend([
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ])

    # Add OTEL context if enabled (from Phase 3 research)
    if include_otel_context:
        # processors.append(otel_trace_context_processor)
        pass

    # Final renderer based on output format
    if output_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(
            colors=True,
            exception_formatter=structlog.dev.plain_traceback,
        ))

    return processors


def create_instance_logger(
    name: str,
    output_format: Literal["json", "console"] = "console",
    log_level: int = logging.INFO,
    include_otel_context: bool = False,
) -> WrappedLogger:
    """Create a per-instance structlog logger.

    Uses structlog.wrap_logger() to avoid global configuration conflicts
    when multiple EventClient instances have different configurations.

    Args:
        name: Logger name (typically the client name)
        output_format: Output format for logs
        log_level: Minimum log level to emit
        include_otel_context: Whether to include OTEL trace context

    Returns:
        A wrapped logger instance with its own processor pipeline
    """
    processors = build_processors(
        output_format=output_format,
        include_otel_context=include_otel_context,
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
```

**Note:** Using `wrap_logger()` instead of `structlog.configure()` ensures each `EventClient` instance has its own isolated configuration. This allows multiple clients with different output formats or log levels to coexist in the same application.

#### 4.4 Refactor EventClient

Major changes to `src/madsci_client/madsci/client/event_client.py`:

```python
import structlog
from structlog.typing import WrappedLogger
from .structlog_config import create_instance_logger

class EventClient:
    """Client for logging events to the MADSci Event Manager.

    Uses structlog for structured logging with context binding support.
    Each EventClient instance has its own isolated logger configuration.

    Example:
        # Basic usage
        client = EventClient(name="my_module")
        client.info("Starting process", step=1, total=10)

        # Context binding
        client = client.bind(workflow_id="wf-123")
        client.info("Processing")  # Automatically includes workflow_id

        # Nested binding
        client = client.bind(node_id="node-456")
        client.info("Action complete")  # Includes both workflow_id and node_id

        # Multiple clients with different configs (fully isolated)
        json_client = EventClient(name="json_logger", config=EventClientConfig(log_output_format="json"))
        console_client = EventClient(name="console_logger", config=EventClientConfig(log_output_format="console"))
    """

    def __init__(self, config: Optional[EventClientConfig] = None, **kwargs):
        # ... initialization ...
        self._logger: WrappedLogger = self._create_structlog_logger()

    def _create_structlog_logger(self) -> WrappedLogger:
        """Create a per-instance structlog logger.

        Uses wrap_logger() for instance isolation - each EventClient
        has its own processor pipeline independent of other instances.
        """
        return create_instance_logger(
            name=self.name,
            output_format=self.config.log_output_format,
            log_level=self.config.log_level.value,
            include_otel_context=self.config.otel_enabled,
        )

    def bind(self, **context) -> "EventClient":
        """Create a new client with additional bound context.

        Args:
            **context: Key-value pairs to bind to all future log messages

        Returns:
            New EventClient instance with bound context
        """
        new_client = copy.copy(self)
        new_client._logger = self._logger.bind(**context)
        return new_client

    # Idiomatic structlog API (primary)
    def debug(self, message: str, **kwargs) -> None:
        """Log a debug message."""
        self._logger.debug(message, **kwargs)
        self._maybe_send_to_server(message, EventLogLevel.DEBUG, **kwargs)

    def info(self, message: str, **kwargs) -> None:
        """Log an info message."""
        self._logger.info(message, **kwargs)
        self._maybe_send_to_server(message, EventLogLevel.INFO, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        """Log a warning message."""
        self._logger.warning(message, **kwargs)
        self._maybe_send_to_server(message, EventLogLevel.WARNING, **kwargs)

    def error(self, message: str, **kwargs) -> None:
        """Log an error message."""
        self._logger.error(message, **kwargs)
        self._maybe_send_to_server(message, EventLogLevel.ERROR, **kwargs)

    def critical(self, message: str, **kwargs) -> None:
        """Log a critical message."""
        self._logger.critical(message, **kwargs)
        self._maybe_send_to_server(message, EventLogLevel.CRITICAL, **kwargs)

    # Backward-compatible aliases
    def log_debug(self, message: str, **kwargs) -> None:
        """Alias for debug(). Provided for backward compatibility."""
        self.debug(message, **kwargs)

    def log_info(self, message: str, **kwargs) -> None:
        """Alias for info(). Provided for backward compatibility."""
        self.info(message, **kwargs)

    def log_warning(self, message: str, **kwargs) -> None:
        """Alias for warning(). Provided for backward compatibility."""
        self.warning(message, **kwargs)

    def log_error(self, message: str, **kwargs) -> None:
        """Alias for error(). Provided for backward compatibility."""
        self.error(message, **kwargs)

    def log_critical(self, message: str, **kwargs) -> None:
        """Alias for critical(). Provided for backward compatibility."""
        self.critical(message, **kwargs)

    def log_alert(self, message: str, **kwargs) -> None:
        """Log an alert (critical with alert flag)."""
        self._logger.critical(message, alert=True, **kwargs)
        self._maybe_send_to_server(message, EventLogLevel.CRITICAL, alert=True, **kwargs)

    # Keep warn as alias for warning
    warn = warning
    alert = log_alert
```

#### 4.5 Update EventClientConfig

Add structlog-related configuration and error handling:

```python
class EventClientConfig(MadsciClientConfig):
    # ... existing fields ...

    log_output_format: Literal["json", "console"] = Field(
        default="console",
        description="Log output format: 'json' for structured, 'console' for human-readable"
    )
    otel_enabled: bool = Field(
        default=False,
        description="Whether to include OpenTelemetry trace context in logs"
    )
    fail_on_error: bool = Field(
        default=False,
        description="If True, raise exceptions on logging/sending failures. If False, log errors silently and continue."
    )
```

#### 4.6 Implement Configurable Error Handling

Add error handling wrapper that respects the `fail_on_error` setting:

```python
def _handle_error(self, error: Exception, context: str) -> None:
    """Handle errors based on fail_on_error configuration.

    Args:
        error: The exception that occurred
        context: Description of what operation failed

    Raises:
        The original exception if fail_on_error is True
    """
    error_msg = f"{context}: {error}"

    if self.config.fail_on_error:
        # Re-raise with context
        raise type(error)(error_msg) from error
    else:
        # Log silently and continue
        # Use stderr to avoid infinite recursion if logging itself fails
        import sys
        print(f"[EventClient Warning] {error_msg}", file=sys.stderr)

def _maybe_send_to_server(
    self,
    message: str,
    level: EventLogLevel,
    alert: bool = False,
    **context
) -> None:
    """Optionally send event to event server with error handling."""
    if not self.event_server:
        return

    try:
        if level.value < self.config.log_level.value:
            return

        event = Event(
            event_type=EventType.LOG,
            event_data={
                "message": message,
                **context,
            },
            log_level=level,
            alert=alert,
            source=self.config.source,
        )

        self._send_event_async(event)
    except Exception as e:
        self._handle_error(e, "Failed to send event to server")
```

#### 4.7 Add Error Handling Tests

Add tests for configurable error handling:

```python
class TestEventClientErrorHandling:
    """Test EventClient error handling behavior."""

    def test_fail_on_error_false_logs_silently(self, config_without_server, capsys):
        """Test that errors are logged silently when fail_on_error=False."""
        config = EventClientConfig(**config_without_server.model_dump(), fail_on_error=False)
        client = EventClient(config=config)
        # Simulate an error condition
        # Verify no exception raised, warning printed to stderr
        pass

    def test_fail_on_error_true_raises_exception(self, config_without_server):
        """Test that errors are raised when fail_on_error=True."""
        config = EventClientConfig(**config_without_server.model_dump(), fail_on_error=True)
        client = EventClient(config=config)
        # Simulate an error condition
        # Verify exception is raised
        pass

    def test_default_fail_on_error_is_false(self):
        """Test that fail_on_error defaults to False."""
        config = EventClientConfig(name="test")
        assert config.fail_on_error is False
```

### Migration Guide

Provide migration guide for existing users:

```markdown
## Migrating to Structlog-based EventClient

### API Changes

| Old API | New API (Preferred) | Notes |
|---------|---------------------|-------|
| `client.log_info("msg")` | `client.info("msg")` | Old method still works |
| `client.log_error("msg")` | `client.error("msg")` | Old method still works |
| `client.log("event_or_msg")` | `client.info("msg", **data)` | Use appropriate level method |

### New Features

#### Context Binding

```python
# Bind context that appears in all subsequent logs
client = EventClient(name="workflow_runner")
client = client.bind(workflow_id="wf-123")
client.info("Starting workflow")  # Includes workflow_id

client = client.bind(step=1)
client.info("Executing step")  # Includes workflow_id and step
```

#### Structured Data

```python
# Pass structured data as keyword arguments
client.info("Resource allocated",
    resource_id="res-456",
    quantity=10,
    location="slot-A1"
)
```

#### JSON Output

```python
# Configure JSON output for log aggregation
config = EventClientConfig(
    name="my_module",
    log_output_format="json"
)
client = EventClient(config=config)
```
```

### Acceptance Criteria

- [ ] Structlog is the default logging backend
- [ ] Per-instance configuration works (multiple clients with different configs are isolated)
- [ ] Idiomatic API (`info()`, `debug()`, etc.) works correctly
- [ ] Backward-compatible aliases (`log_info()`, `log_debug()`, etc.) work correctly
- [ ] Context binding works and accumulates context
- [ ] JSON and console output formats work
- [ ] Events are correctly created and sent to EventManager
- [ ] Configurable error handling (`fail_on_error`) works correctly
- [ ] All tests pass (new and existing, with updates)
- [ ] Migration guide is documented

---

## Phase 5: MongoDB Event Retention & Backup

**Target Issues:** [#80](https://github.com/AD-SDL/MADSci/issues/80) (Part 2 - MongoDB)
**Estimated Effort:** Medium (3-5 days)
**Breaking Changes:** Minor (new config options, new endpoints)

### Goals

- Configurable event retention with soft-delete → hard-delete workflow
- **MongoDB TTL indexes** for automatic hard-deletion (simpler, more reliable)
- Event backup/export functionality with **batch limits** for large operations
- Improved query options

### Requirements

From issue #80:

> - Should support a maximum retention length for events (default to unlimited)
> - Should support one-time or regular event backup/export functionality
> - Improve client query options

### Design: TTL Index vs Manual Deletion

We use a **hybrid approach**:

| Operation | Mechanism | Rationale |
|-----------|-----------|-----------|
| Soft-delete (archiving) | Background task | Requires updating documents, not just deleting |
| Hard-delete | MongoDB TTL index | Automatic, reliable, no application code needed |

This leverages MongoDB's native TTL functionality while still supporting the soft-delete workflow for data recovery.

### Implementation Tasks

#### 5.1 Extend Event Model

Add archive fields to `Event` in `src/madsci_common/madsci/common/types/event_types.py`:

```python
class Event(MongoModel):
    # ... existing fields ...

    archived: bool = Field(
        default=False,
        description="Whether this event has been archived (soft-deleted)"
    )
    archived_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp when this event was archived"
    )
```

#### 5.2 Extend EventManagerSettings

Add retention configuration with batch limits and TTL settings:

```python
class EventManagerSettings(MadsciBaseSettings):
    # ... existing fields ...

    # Retention settings
    retention_enabled: bool = Field(
        default=False,
        description="Whether automatic event retention is enabled"
    )
    soft_delete_after_days: int = Field(
        default=90,
        description="Days after which events are soft-deleted (archived)"
    )
    hard_delete_after_days: int = Field(
        default=365,
        description="Days after archive when events are permanently deleted via TTL index"
    )
    retention_check_interval_hours: int = Field(
        default=24,
        description="How often to run soft-delete retention checks (in hours)"
    )

    # Batch operation limits (to prevent performance impact)
    archive_batch_size: int = Field(
        default=1000,
        description="Maximum number of events to archive in a single batch operation"
    )
    max_batches_per_run: int = Field(
        default=100,
        description="Maximum number of batches to process per retention run (0 = unlimited)"
    )

    # Backup settings
    backup_enabled: bool = Field(
        default=False,
        description="Whether automatic event backups are enabled"
    )
    backup_schedule: Optional[str] = Field(
        default=None,
        description="Cron expression for backup schedule (e.g., '0 2 * * *' for 2am daily)"
    )
    backup_dir: PathLike = Field(
        default="~/.madsci/backups/events",
        description="Directory for event backups"
    )
    backup_max_count: int = Field(
        default=10,
        description="Maximum number of backup files to keep"
    )

    # Error handling
    fail_on_retention_error: bool = Field(
        default=False,
        description="If True, raise exceptions on retention failures. If False, log and continue."
    )
```

#### 5.3 Write Tests First

Add tests to `src/madsci_event_manager/tests/test_event_server.py`:

```python
class TestEventRetention:
    """Test EventManager retention functionality."""

    def test_soft_delete_event(self, mock_event_manager, sample_event):
        """Test that events can be soft-deleted (archived)."""
        pass

    def test_hard_delete_archived_events(self, mock_event_manager):
        """Test that archived events can be permanently deleted."""
        pass

    def test_retention_policy_enforcement(self, mock_event_manager):
        """Test that retention policy is applied correctly."""
        pass

    def test_archived_events_excluded_from_queries(self, mock_event_manager):
        """Test that archived events are excluded by default."""
        pass

    def test_include_archived_events_option(self, mock_event_manager):
        """Test that archived events can be included via option."""
        pass


class TestEventBackup:
    """Test EventManager backup functionality."""

    def test_create_backup(self, mock_event_manager, temp_backup_dir):
        """Test creating a one-time backup."""
        pass

    def test_backup_format_json(self, mock_event_manager, temp_backup_dir):
        """Test backup in JSON format."""
        pass

    def test_backup_rotation(self, mock_event_manager, temp_backup_dir):
        """Test that old backups are rotated out."""
        pass

    def test_restore_from_backup(self, mock_event_manager, temp_backup_dir):
        """Test restoring events from backup."""
        pass


class TestEventQueryImprovements:
    """Test improved event query options."""

    def test_query_with_pagination(self, mock_event_manager):
        """Test paginated event queries."""
        pass

    def test_query_with_date_range(self, mock_event_manager):
        """Test date range filtering."""
        pass

    def test_query_with_cursor(self, mock_event_manager):
        """Test cursor-based pagination for large result sets."""
        pass
```

#### 5.4 Implement Retention Endpoints

Add endpoints to `src/madsci_event_manager/madsci/event_manager/event_server.py`:

```python
@self.app.post("/events/archive")
def archive_events(
    before_date: Optional[datetime] = None,
    event_ids: Optional[list[str]] = None,
) -> dict[str, int]:
    """Archive (soft-delete) events.

    Args:
        before_date: Archive all events before this date
        event_ids: Specific event IDs to archive

    Returns:
        Count of archived events
    """
    pass

@self.app.delete("/events/archived")
def purge_archived_events(
    older_than_days: int = 365,
) -> dict[str, int]:
    """Permanently delete archived events older than threshold.

    Args:
        older_than_days: Delete archived events older than this many days

    Returns:
        Count of deleted events
    """
    pass

@self.app.get("/events/archived")
def get_archived_events(
    number: int = 100,
    offset: int = 0,
) -> dict[str, Event]:
    """Retrieve archived events.

    Args:
        number: Maximum number of events to return
        offset: Offset for pagination

    Returns:
        Dictionary of archived events
    """
    pass
```

#### 5.5 Implement Backup Endpoints

Leverage existing `MongoDBBackupTool` from `madsci_common.backup_tools`:

```python
from madsci.common.backup_tools import MongoDBBackupTool
from madsci.common.types.backup_types import MongoDBBackupSettings

@self.app.post("/backup")
def create_backup(
    description: Optional[str] = None,
) -> dict[str, str]:
    """Create a one-time backup of all events.

    Args:
        description: Optional description for the backup

    Returns:
        Backup file path and metadata
    """
    backup_settings = MongoDBBackupSettings(
        mongo_db_url=self.settings.mongo_db_url,
        database=self.settings.database_name,
        backup_dir=Path(self.settings.backup_dir).expanduser(),
        max_backups=self.settings.backup_max_count,
    )
    backup_tool = MongoDBBackupTool(backup_settings)
    backup_path = backup_tool.create_backup(description or "manual")
    return {"backup_path": str(backup_path), "status": "completed"}

@self.app.get("/backup/status")
def get_backup_status() -> dict[str, Any]:
    """Get status of backups including list of available backups."""
    pass
```

#### 5.6 Create TTL Index for Automatic Hard-Deletion

Add TTL index creation during EventManager initialization:

```python
def _setup_indexes(self) -> None:
    """Set up MongoDB indexes including TTL index for automatic hard-deletion."""
    # Standard indexes for query performance
    self.events.create_index("timestamp")
    self.events.create_index("log_level")
    self.events.create_index("archived")
    self.events.create_index([("archived", 1), ("archived_at", 1)])

    # TTL index for automatic hard-deletion of archived events
    # MongoDB will automatically delete documents where archived_at
    # is older than hard_delete_after_days
    ttl_seconds = self.settings.hard_delete_after_days * 24 * 60 * 60

    # Note: TTL index only applies to documents where archived_at is set
    # Non-archived events (archived_at=None) are not affected
    self.events.create_index(
        "archived_at",
        expireAfterSeconds=ttl_seconds,
        partialFilterExpression={"archived": True}  # Only apply to archived docs
    )

    self.event_client.info(
        "TTL index configured for automatic hard-deletion",
        ttl_days=self.settings.hard_delete_after_days,
    )
```

**Benefits of TTL Index:**
- MongoDB handles deletion automatically in the background
- No application code needed for hard-deletion
- More reliable than custom background tasks
- Scales better with large datasets

#### 5.7 Implement Soft-Delete Background Task with Batch Limits

Add background task for soft-deletion (archiving) with batch processing:

```python
import asyncio
from datetime import datetime, timedelta
from typing import Tuple

async def _run_retention_check(self) -> None:
    """Background task to enforce soft-delete retention policy.

    Note: Hard-deletion is handled automatically by MongoDB TTL index.
    This task only handles soft-deletion (archiving) of old events.
    """
    while True:
        if self.settings.retention_enabled:
            try:
                archived_count = await self._archive_old_events()
                self.event_client.debug(
                    "Retention check completed",
                    archived_count=archived_count,
                )
            except Exception as e:
                error_msg = f"Retention check failed: {e}"
                if self.settings.fail_on_retention_error:
                    self.event_client.error(error_msg)
                    raise
                else:
                    self.event_client.warning(error_msg)

        await asyncio.sleep(self.settings.retention_check_interval_hours * 3600)

async def _archive_old_events(self) -> int:
    """Archive old events in batches to prevent performance impact.

    Returns:
        Total number of events archived
    """
    soft_delete_cutoff = datetime.utcnow() - timedelta(
        days=self.settings.soft_delete_after_days
    )

    total_archived = 0
    batches_processed = 0
    batch_size = self.settings.archive_batch_size
    max_batches = self.settings.max_batches_per_run

    while True:
        # Check batch limit
        if max_batches > 0 and batches_processed >= max_batches:
            self.event_client.info(
                "Reached max batches limit, will continue next run",
                batches_processed=batches_processed,
                total_archived=total_archived,
            )
            break

        # Find batch of events to archive
        events_to_archive = list(self.events.find(
            {
                "timestamp": {"$lt": soft_delete_cutoff},
                "archived": {"$ne": True},
            },
            {"_id": 1}
        ).limit(batch_size))

        if not events_to_archive:
            break  # No more events to archive

        event_ids = [e["_id"] for e in events_to_archive]

        # Archive this batch
        result = self.events.update_many(
            {"_id": {"$in": event_ids}},
            {
                "$set": {
                    "archived": True,
                    "archived_at": datetime.utcnow(),
                }
            }
        )

        total_archived += result.modified_count
        batches_processed += 1

        # Small delay between batches to reduce database load
        await asyncio.sleep(0.1)

    return total_archived
```

**Batch Processing Benefits:**
- Prevents long-running operations from blocking the database
- Configurable batch size adapts to different deployment scales
- Progress logging helps with monitoring and debugging
- Graceful handling of very large backlogs across multiple runs

#### 5.8 Improve Query Options

Add pagination and date range filtering:

```python
@self.app.get("/events")
def get_events(
    number: int = 100,
    offset: int = 0,
    level: int = 10,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    include_archived: bool = False,
) -> dict[str, Event]:
    """Get events with enhanced filtering options.

    Args:
        number: Maximum number of events to return
        offset: Offset for pagination
        level: Minimum log level to include
        start_time: Filter events after this time
        end_time: Filter events before this time
        include_archived: Whether to include archived events
    """
    query = {"log_level": {"$gte": level}}

    if not include_archived:
        query["archived"] = {"$ne": True}

    if start_time:
        query["timestamp"] = {"$gte": start_time}
    if end_time:
        query.setdefault("timestamp", {})["$lte"] = end_time

    cursor = self.events.find(query).sort("timestamp", -1).skip(offset).limit(number)

    return {doc["_id"]: Event.from_mongo(doc) for doc in cursor}
```

#### 5.9 Add Batch Operation and TTL Tests

Add tests for new functionality:

```python
class TestEventRetentionBatching:
    """Test batch processing for retention operations."""

    def test_archive_respects_batch_size(self, mock_event_manager):
        """Test that archiving processes events in batches."""
        pass

    def test_archive_respects_max_batches(self, mock_event_manager):
        """Test that max_batches_per_run limit is enforced."""
        pass

    def test_archive_continues_across_runs(self, mock_event_manager):
        """Test that large backlogs are processed across multiple runs."""
        pass


class TestTTLIndex:
    """Test MongoDB TTL index configuration."""

    def test_ttl_index_created_on_startup(self, mock_event_manager):
        """Test that TTL index is created during initialization."""
        pass

    def test_ttl_only_affects_archived_events(self, mock_event_manager):
        """Test that TTL index has correct partial filter expression."""
        pass


class TestRetentionErrorHandling:
    """Test retention error handling behavior."""

    def test_fail_on_retention_error_false_continues(self, mock_event_manager):
        """Test that retention continues on error when fail_on_retention_error=False."""
        pass

    def test_fail_on_retention_error_true_raises(self, mock_event_manager):
        """Test that retention raises on error when fail_on_retention_error=True."""
        pass
```

### Acceptance Criteria

- [ ] Events can be soft-deleted (archived) in configurable batch sizes
- [ ] TTL index is created for automatic hard-deletion of archived events
- [ ] Soft-delete retention runs automatically on configurable schedule
- [ ] Batch limits prevent performance impact during large retention operations
- [ ] One-time backups can be created via API
- [ ] Backup uses existing `MongoDBBackupTool`
- [ ] Event queries support pagination (offset/limit)
- [ ] Event queries support date range filtering
- [ ] Archived events are excluded by default, can be included
- [ ] Error handling is configurable via `fail_on_retention_error`
- [ ] All tests pass

---

## Dependency Graph

```
Phase 1 (Startup Logging)
    │
    ▼
Phase 2 (Log Rotation) ─────────────┐
    │                               │
    ▼                               │
Phase 3 (OTEL Research) ◄───────────┤
    │                               │
    ▼                               │
Phase 4 (Structlog Migration) ──────┘
    │
    ▼
Phase 5 (MongoDB Retention/Backup)
```

**Notes:**

- Phases 1-2 can proceed immediately and independently
- Phase 3 (research) should complete before Phase 4 to inform structlog processor design
- Phase 5 is largely independent and can run in parallel with Phase 4
- Each phase should be completed in a separate PR for easier review

---

## Test Strategy

Each phase follows test-driven development:

1. **Write failing tests** for new functionality
2. **Implement** until tests pass
3. **Refactor** with tests as safety net

### Test Categories

| Category | Description | Tools |
|----------|-------------|-------|
| Unit | Test components in isolation | pytest, unittest.mock |
| Integration | Test component interactions | mongomock, pytest-httpx |
| Regression | Ensure existing functionality | Existing test suites |

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest src/madsci_client/tests/test_event_client.py

# Run with coverage
just coverage

# Run specific test class
pytest src/madsci_client/tests/test_event_client.py::TestEventClientStructlog
```

---

## Progress Tracking

| Phase | Status | PR | Notes |
|-------|--------|----|-------|
| Phase 1 | Complete | - | Startup logging implemented at INFO level |
| Phase 2 | Complete | - | Log rotation with RotatingFileHandler/TimedRotatingFileHandler, gzip compression |
| Phase 3 | Complete | - | Research doc + PoC branch `feature/otel-poc` |
| Phase 4 | Not Started | - | - |
| Phase 5 | Not Started | - | - |

---

## References

- [Structlog Documentation](https://www.structlog.org/en/stable/)
- [OpenTelemetry Python Documentation](https://opentelemetry.io/docs/languages/python/)
- [Python Logging Handlers](https://docs.python.org/3/library/logging.handlers.html)
- [MongoDB TTL Indexes](https://www.mongodb.com/docs/manual/core/index-ttl/) (alternative to manual retention)
