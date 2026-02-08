# MADSci Common Package

## Overview
The `madsci_common` package contains shared types, utilities, and base classes used across all MADSci components. This is the foundation package that establishes common patterns and interfaces.

## Key Components

### Types System (`madsci/common/types/`)
- **base_types.py**: Core Pydantic models and enums
- **manager_types.py**: Manager service definitions and health checks
- **node_types.py**: Laboratory instrument node interfaces
- **resource_types/**: Resource management models and enums
- **workflow_types.py**: Workflow and step definitions
- **experiment_types.py**: Experiment and campaign management
- **event_types.py**: Event logging and monitoring
- **location_types.py**: Laboratory location and spatial management
- **auth_types.py**: Ownership metadata and authentication

### Context Management (`madsci/common/context.py`)
- **MadsciContext**: Global context for server URLs and configuration
- **EventClient context**: Hierarchical logging context system
- **Context decorators**: `@with_madsci_context`, `@with_event_client`, `@event_client_class`

### Ownership (`madsci/common/ownership.py`)
- **OwnershipInfo**: Metadata tracking (user, experiment, workflow, etc.)
- **ownership_context**: Context manager for ownership propagation
- **Decorators**: `@with_ownership`, `@ownership_class`

### OpenTelemetry (`madsci/common/otel/`)
- **bootstrap.py**: OTEL initialization and configuration
- **tracing.py**: Span context managers and decorators (`span_context`, `@with_span`, `@traced_class`)
- **propagation.py**: W3C trace context propagation
- **fastapi_instrumentation.py**: FastAPI auto-instrumentation
- **requests_instrumentation.py**: HTTP requests auto-instrumentation

### Base Classes
- **AbstractManagerBase**: Base class for all manager services with FastAPI integration
- **MadsciBaseSettings**: Configuration management with environment variable support
- **AbstractNodeModule**: Base class for laboratory instrument implementations

### Utilities
- **utils.py**: ULID generation, serialization helpers, and common functions
- **validators.py**: Custom Pydantic validators for MADSci-specific data types
- **workflows.py**: Workflow execution and management utilities
- **object_storage_helpers.py**: File and data storage abstractions

## Development Patterns

### ID Generation
Always use `new_ulid_str()` for generating unique identifiers:
```python
from madsci.common.utils import new_ulid_str
resource_id = new_ulid_str()
```

### Manager Implementation
Inherit from `AbstractManagerBase` for consistent manager patterns:
```python
from madsci.common.manager_base import AbstractManagerBase

class MyManagerServer(AbstractManagerBase[MySettings, MyDefinition]):
    def __init__(self, settings: MySettings):
        super().__init__(settings)
```

### Context-Aware Logging
Use the context system for hierarchical logging:
```python
from madsci.common.context import event_client_context, get_event_client

# At entry points, establish context
with event_client_context(name="operation", operation_id="op-123") as logger:
    logger.info("Starting operation")

# In library code, inherit context
def utility_function():
    logger = get_event_client()
    logger.info("Utility running")
```

### OpenTelemetry Tracing
Use the tracing decorators and context managers:
```python
from madsci.common.otel import span_context, with_span

@with_span(name="process_data")
def process(data):
    return transform(data)

with span_context("custom_operation") as span:
    span.set_attribute("key", "value")
    do_work()
```

### Type Definitions
- All models use Pydantic v2 with proper validation
- Enums are used for status and state management
- SQLModel integration for database ORM
- AnyUrl type for all URL fields (ensures trailing slash)

## Important Notes
- This package must remain dependency-light as it's imported by all other packages
- Breaking changes here affect the entire MADSci ecosystem
- Type definitions should be backward-compatible when possible
- All new types should include comprehensive docstrings and examples
- Context management uses `contextvars.ContextVar` for thread-safe, async-compatible propagation
