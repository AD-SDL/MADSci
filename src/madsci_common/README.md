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
from madsci.common.utils import (
    utcnow, new_ulid_str, is_valid_ulid, extract_datapoint_ids,
    threaded_task, threaded_daemon, prompt_from_pydantic_model
)
from madsci.common.validators import ulid_validator
from madsci.common.serializers import serialize_to_yaml

# Generate unique IDs (ULID format)
experiment_id = new_ulid_str()

# UTC timestamps
timestamp = utcnow()

# YAML serialization
yaml_content = serialize_to_yaml(my_pydantic_model)

# ULID validation
is_valid = ulid_validator(experiment_id)
# Alternative validation
is_valid_alt = is_valid_ulid(experiment_id)

# Extract datapoint IDs from complex data structures
data_with_ids = {"result": ["01ARZ3NDEKTSV4RRFFQ69G5FAV", "01BX5ZZKBKACTAV9WEVGEMMVRZ"]}
datapoint_ids = extract_datapoint_ids(data_with_ids)

# Threading decorators for background tasks
@threaded_task
def background_job(data):
    # Long-running task
    pass

@threaded_daemon
def daemon_process():
    # Background daemon that stops when main thread exits
    pass

# Interactive model creation
from madsci.common.types.base_types import MadsciBaseModel

class MyModel(MadsciBaseModel):
    name: str
    value: int

# Prompt user to fill model fields interactively
user_data = prompt_from_pydantic_model(MyModel, "Enter model data")
my_instance = MyModel(**user_data)
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

### ULID Best Practices

MADSci uses **ULID (Universally Unique Lexicographically Sortable Identifier)** for all ID generation throughout the system:

```python
from madsci.common.utils import new_ulid_str, is_valid_ulid

# Generate new IDs
resource_id = new_ulid_str()
experiment_id = new_ulid_str()

# Validate ULID format
if is_valid_ulid(some_id):
    # Process valid ULID
    pass
```

**When to use ULIDs:**
- All resource identifiers (experiments, workflows, datapoints, etc.)
- Database primary keys
- Event tracking and correlation
- Any case requiring unique, sortable identifiers

**Benefits over UUIDs:**
- **Performance**: More efficient generation and comparison
- **Lexicographical sorting**: Natural time-based ordering
- **Timestamp preservation**: First 48 bits encode creation time
- **URL-safe**: Uses Crockford's Base32 encoding
- **Collision resistance**: 80 bits of randomness per millisecond

**Validation patterns:**
```python
from madsci.common.validators import ulid_validator
from pydantic import Field

class MyModel(MadsciBaseModel):
    id: str = Field(default_factory=new_ulid_str, title="Resource ID")
    parent_id: Optional[str] = Field(None, title="Parent Resource ID")

    @field_validator("parent_id")
    @classmethod
    def validate_parent_id(cls, v):
        if v is not None:
            return ulid_validator(v)
        return v
```

### Error Handling

MADSci provides standardized error handling patterns using the `Error` class and specific exceptions:

```python
from madsci.common.types.base_types import Error
from madsci.common.exceptions import (
    ActionNotImplementedError, WorkflowFailedError,
    ExperimentCancelledError, LocationNotFoundError
)

# Create errors from exceptions
try:
    # Some operation that might fail
    pass
except ValueError as e:
    error = Error.from_exception(e)
    # Error has: message, error_type, logged_at

# Create errors manually
error = Error(
    message="Custom error occurred",
    error_type="ValidationError"
)

# MADSci-specific exceptions
raise ActionNotImplementedError("Action 'analyze_sample' not implemented")
raise WorkflowFailedError("Sample preparation workflow failed at step 3")
raise ExperimentCancelledError("User cancelled experiment 'batch_synthesis'")
raise LocationNotFoundError("Location 'sample_rack_1' not found in lab")
```

**Error handling in actions:**
```python
def my_action(self, sample_id: str) -> ActionResult:
    try:
        # Action implementation
        result = process_sample(sample_id)
        return self.request.succeeded(json_result=result)
    except Exception as e:
        # Convert exception to MADSci Error
        error = Error.from_exception(e)
        return self.request.failed(errors=[error])
```

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

### Middleware

MADSci provides middleware components for enhancing server resilience and monitoring:

#### Rate Limiting

The `RateLimitMiddleware` protects services from overload by enforcing request rate limits per client IP with support for dual window limiting (burst + sustained):

```python
from madsci.common.middleware import RateLimitMiddleware
from fastapi import FastAPI

app = FastAPI()

# Add rate limiting with dual windows
app.add_middleware(
    RateLimitMiddleware,
    requests_limit=100,              # Long window: 100 requests per 60 seconds
    time_window=60,
    short_requests_limit=50,         # Short window: 50 requests per 1 second (burst protection)
    short_time_window=1,
    cleanup_interval=300             # Clean up inactive clients every 5 minutes
)
```

**Key features:**
- **Dual rate limiting**: Separate limits for burst (short window) and sustained (long window) traffic
- **Async-safe**: Uses asyncio locks to prevent race conditions in concurrent coroutine handling
- **Sliding window**: Rate limiting based on moving time window algorithm
- **Memory efficient**: Automatic cleanup of inactive client tracking data
- **Standard headers**: Returns `X-RateLimit-*` headers and `Retry-After` on limit exceeded
- **429 responses**: Returns HTTP 429 Too Many Requests when limit is exceeded

**Configuration parameters:**
- `requests_limit`: Maximum requests allowed per long time window (default: 100)
- `time_window`: Long time window in seconds (default: 60)
- `short_requests_limit`: Maximum requests per short window for burst protection (default: 50, optional)
- `short_time_window`: Short time window in seconds (default: 1, optional)
- `cleanup_interval`: Interval between cleanup operations in seconds (default: 300)

**Response headers:**
- `X-RateLimit-Limit`: Maximum requests allowed in the long time window
- `X-RateLimit-Remaining`: Number of requests remaining in current long window
- `X-RateLimit-Reset`: Unix timestamp when the long window rate limit resets
- `X-RateLimit-Burst-Limit`: Maximum requests allowed in the short time window (if configured)
- `X-RateLimit-Burst-Remaining`: Number of requests remaining in current short window (if configured)
- `Retry-After`: Seconds to wait before retrying (included in 429 responses)

**Example 429 responses:**
```json
// Burst limit exceeded
{
  "detail": "Rate limit exceeded: 50 requests per 1 seconds (burst limit)"
}

// Long window limit exceeded
{
  "detail": "Rate limit exceeded: 100 requests per 60 seconds"
}
```

**Integration with managers:**
```python
from madsci.common.manager_base import AbstractManagerBase
from madsci.common.middleware import RateLimitMiddleware

class MyManager(AbstractManagerBase[MySettings, MyDefinition]):
    def __init__(self, settings: MySettings):
        super().__init__(settings)
        # Rate limiting is automatically configured from ManagerSettings
        # To customize, modify settings before initialization:
        # settings.rate_limit_requests = 200
        # settings.rate_limit_short_requests = 20
```

**How dual rate limiting works:**

Dual rate limiting protects against both burst traffic and sustained high load:

1. **Burst protection (short window)**: Prevents rapid request bursts that could overwhelm the service
   - Example: 50 requests per second limit prevents a client from sending 100 requests instantly

2. **Sustained load protection (long window)**: Prevents continuous high request rates over time
   - Example: 100 requests per minute limit prevents sustained abuse

Both limits must be satisfied for a request to succeed. If either limit is exceeded, a 429 response is returned with appropriate `Retry-After` guidance.

**Single window mode:**

To use only long window limiting (no burst protection), set `short_requests_limit` and `short_time_window` to `None`:

```python
app.add_middleware(
    RateLimitMiddleware,
    requests_limit=100,
    time_window=60,
    short_requests_limit=None,  # Disable burst protection
    short_time_window=None,
)
```
### Database Backup Tools

MADSci provides standalone backup tools for MongoDB databases that can be used independently or integrated with migration workflows:

```python
from pathlib import Path
from pydantic import AnyUrl
from madsci.common.backup_tools import (
    MongoDBBackupTool,
    MongoDBBackupSettings
)

# Configure backup settings
settings = MongoDBBackupSettings(
    mongo_db_url=AnyUrl("mongodb://localhost:27017"),
    database="events",
    backup_dir=Path("./backups"),
    max_backups=10,  # Keep last 10 backups
    validate_integrity=True
)

# Create backup tool
backup_tool = MongoDBBackupTool(settings)

# Create a backup
backup_path = backup_tool.create_backup("before_migration")
print(f"Backup created: {backup_path}")

# List available backups
backups = backup_tool.list_available_backups()

# Restore from backup
backup_tool.restore_from_backup(backup_path)

# Validate backup integrity
is_valid = backup_tool.validate_backup_integrity(backup_path)
```

**Using the unified CLI:**
```bash
# Create MongoDB backup (auto-detects database type)
madsci-backup create --db-url mongodb://localhost:27017/events

# Restore from backup
madsci-backup restore --backup /path/to/backup --db-url mongodb://localhost:27017/events

# Validate backup integrity
madsci-backup validate --backup /path/to/backup --db-url mongodb://localhost:27017/events
```

**Features:**
- Standalone backup/restore operations
- Automatic backup rotation and retention
- SHA256 integrity validation
- Support for specific collection filtering
- Integration with MADSci migration tools
- Unified CLI for both PostgreSQL and MongoDB

For comprehensive documentation including examples, best practices, and advanced usage, see [backup_tools/README.md](./madsci/common/backup_tools/README.md).
