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
