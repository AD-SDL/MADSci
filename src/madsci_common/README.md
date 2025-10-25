# MADSci Common

Shared types, utilities, validators, base classes and other common code used across the MADSci toolkit.

## Installation

See the main [README](../../README.md#installation) for installation options. This package is available as:
- PyPI: `pip install madsci.common`
- Docker: Included in `ghcr.io/ad-sdl/madsci`
- **Dependency**: Required by all other MADSci packages

## Core Components

### Types System
Pydantic-based data models for the entire MADSci ecosystem:

```python
# Import types organized by subsystem
from madsci.common.types.workflow_types import WorkflowDefinition
from madsci.common.types.node_types import NodeDefinition
from madsci.common.types.experiment_types import ExperimentDesign
from madsci.common.types.datapoint_types import ValueDataPoint
```

**Available type modules:**
- `action_types`: Action definitions, parameters, and flexible return types
- `experiment_types`: Experiment campaigns, designs, runs
- `workflow_types`: Workflow and step definitions with enhanced datapoint handling
- `node_types`: Node configurations and status
- `datapoint_types`: Data storage and retrieval
- `event_types`: Event logging and querying
- `resource_types`: Resource management and tracking
- `location_types`: Location management and resource attachments
- `parameter_types`: Enhanced parameter validation and serialization
- `auth_types`: Ownership and authentication
- `base_types`: Foundation classes and utilities

### Utilities
Common helper functions and validators:

```python
from madsci.common.utils import utcnow, new_ulid_str
from madsci.common.types.action_types import create_dynamic_model
from madsci.common.validators import ulid_validator
from madsci.common.serializers import serialize_to_yaml

# Generate unique IDs (ULID format)
experiment_id = new_ulid_str()

# UTC timestamps
timestamp = utcnow()

# YAML serialization
yaml_content = serialize_to_yaml(my_pydantic_model)

# Dynamic model creation for complex types
DynamicModel = create_dynamic_model("MyModel", {"value": int})
```

### Settings Framework
Hierarchical configuration system using [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/):

```python
from madsci.common.types.base_types import MadsciBaseSettings

class MyManagerSettings(MadsciBaseSettings):
    server_url: str = "http://localhost:8000"
    database_url: str = "mongodb://localhost:27017"
    # Supports env vars, CLI args, config files

settings = MyManagerSettings()
```

**Configuration sources (in precedence order):**
1. Command line arguments
2. Environment variables
3. Subsystem-specific files (`workcell.env`, `event.yaml`)
4. Generic files (`.env`, `settings.yaml`)
5. Default values

![Settings Precedence](./assets/drawio/config_precedence.drawio.svg)

**Configuration options**: See [Configuration.md](../../Configuration.md) and [example_lab/managers/](../../example_lab/managers/) for examples.

## Usage Patterns

### Creating Custom Types
```python
from madsci.common.types.base_types import MadsciBaseModel
from pydantic import Field
from typing import Optional

class MyCustomType(MadsciBaseModel):
    name: str = Field(description="Object name")
    value: float = Field(gt=0, description="Positive value")
    metadata: dict = Field(default_factory=dict)
    optional_field: Optional[str] = Field(None, description="Optional parameter")

# Automatic validation, serialization to JSON/YAML
obj = MyCustomType(name="test", value=42.0)
json_str = obj.model_dump_json()
yaml_str = obj.model_dump_yaml()  # YAML serialization supported
```

### Action Parameter Types
```python
from madsci.common.types.action_types import ActionFiles
from pathlib import Path
from typing import Union

class ProcessingFiles(ActionFiles):
    """Custom file collection for action returns."""
    log_file: Path
    results_file: Path
    optional_config: Optional[Path] = None

# Complex parameter handling
def my_action(
    sample_id: str,
    parameters: dict[str, Union[str, int, float]],
    file_input: Path,
    optional_metadata: Optional[dict] = None
) -> ProcessingFiles:
    """Action with complex parameter types and file return."""
    # MADSci automatically handles serialization/deserialization
    pass
```

### Extending Base Settings
```python
from madsci.common.types.base_types import MadsciBaseSettings
from pydantic import Field
from typing import Optional

class CustomSettings(MadsciBaseSettings, env_prefix="CUSTOM_"):
    api_key: str = Field(description="API authentication key")
    timeout: int = Field(default=30, description="Request timeout")
    advanced_config: Optional[dict[str, str]] = Field(
        default=None,
        description="Advanced configuration options"
    )

# Reads from CUSTOM_API_KEY, CUSTOM_TIMEOUT environment variables
settings = CustomSettings()
```

### Working with Complex Types
```python
from madsci.common.types.parameter_types import ParameterDefinition
from typing import Union, Optional, get_origin

# Handle complex nested types
complex_type = dict[str, list[Union[int, float]]]
origin = get_origin(complex_type)  # Returns dict

# Parameter validation for action arguments
param_def = ParameterDefinition(
    name="complex_param",
    type_hint=complex_type,
    required=True,
    description="Complex nested parameter"
)
```

### Manager Base Class
Create standardized manager services with `AbstractManagerBase`:

```python
from madsci.common.manager_base import AbstractManagerBase
from madsci.common.types.base_types import MadsciBaseSettings, MadsciBaseModel
from madsci.common.types.manager_types import ManagerHealth

class MyManagerSettings(MadsciBaseSettings):
    model_config = {"env_prefix": "MY_MANAGER_"}
    database_url: str = "mongodb://localhost:27017"

class MyManagerDefinition(MadsciBaseModel):
    name: str = "My Manager"
    description: str = "Custom manager service"

class MyManager(AbstractManagerBase[MyManagerSettings, MyManagerDefinition]):
    SETTINGS_CLASS = MyManagerSettings
    DEFINITION_CLASS = MyManagerDefinition
    # ENABLE_ROOT_DEFINITION_ENDPOINT = True  # Default: enabled

    def get_health(self) -> ManagerHealth:
        """Override to implement custom health checks."""
        return ManagerHealth(healthy=True, description="Manager is healthy")

# Create and run the manager
manager = MyManager()
manager.run_server()  # Starts FastAPI server with auto-generated endpoints
```

**Built-in endpoints:**
- `GET /` - Manager definition (configurable with `ENABLE_ROOT_DEFINITION_ENDPOINT`)
- `GET /definition` - Manager definition (always available)
- `GET /health` - Health status

**Configurable root endpoint:**
```python
class CustomManager(AbstractManagerBase[Settings, Definition]):
    ENABLE_ROOT_DEFINITION_ENDPOINT = False  # Disable root endpoint
    # Allows custom root endpoint implementation or static file serving for UIs
```
