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
- `action_types`: Action definitions and results
- `experiment_types`: Experiment campaigns, designs, runs
- `workflow_types`: Workflow and step definitions
- `node_types`: Node configurations and status
- `datapoint_types`: Data storage and retrieval
- `event_types`: Event logging and querying
- `resource_types`: Resource management and tracking
- `auth_types`: Ownership and authentication
- `base_types`: Foundation classes and utilities

### Utilities
Common helper functions and validators:

```python
from madsci.common.utils import utcnow, new_ulid_str
from madsci.common.validators import ulid_validator
from madsci.common.serializers import serialize_to_yaml

# Generate unique IDs
experiment_id = new_ulid_str()

# UTC timestamps
timestamp = utcnow()

# YAML serialization
yaml_content = serialize_to_yaml(my_pydantic_model)
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

class MyCustomType(MadsciBaseModel):
    name: str = Field(description="Object name")
    value: float = Field(gt=0, description="Positive value")
    metadata: dict = Field(default_factory=dict)

# Automatic validation, serialization to JSON/YAML
obj = MyCustomType(name="test", value=42.0)
json_str = obj.model_dump_json()
```

### Extending Base Settings
```python
from madsci.common.types.base_types import MadsciBaseSettings

class CustomSettings(MadsciBaseSettings, env_prefix="CUSTOM_"):
    api_key: str = Field(description="API authentication key")
    timeout: int = Field(default=30, description="Request timeout")

# Reads from CUSTOM_API_KEY, CUSTOM_TIMEOUT environment variables
settings = CustomSettings()
```
