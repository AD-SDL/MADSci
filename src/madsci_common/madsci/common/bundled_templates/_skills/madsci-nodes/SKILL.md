---
name: madsci-nodes
description: Working with MADSci node modules for laboratory instrument integration. Use when creating, modifying, debugging, or testing node modules that interface with scientific instruments.
---

# MADSci Node Modules

Node modules are the instrument integration layer of MADSci. Each node wraps a laboratory instrument (robot arm, plate reader, liquid handler, etc.) behind a standard API. The architecture is: **AbstractNode** (protocol-agnostic base) -> **RestNode** (FastAPI HTTP server). Both use **MadsciClientMixin** for lazy access to Event, Resource, and Data clients.

## Key Files

| File | Purpose |
|------|---------|
| `src/madsci_node_module/madsci/node_module/abstract_node_module.py` | Base class with lifecycle, action dispatch, type analysis |
| `src/madsci_node_module/madsci/node_module/rest_node_module.py` | FastAPI server, file upload/download, rate limiting |
| `src/madsci_node_module/madsci/node_module/helpers.py` | `@action` decorator |
| `src/madsci_node_module/madsci/node_module/type_analyzer.py` | Recursive type hint analysis (`TypeInfo`) |
| `src/madsci_common/madsci/common/types/node_types.py` | NodeConfig, RestNodeConfig, NodeStatus, NodeInfo, NodeCapabilities, NodeIntrinsicLocationDefinition |
| `src/madsci_client/madsci/client/node/rest_node_client.py` | HTTP client for node communication |
| `src/madsci_common/madsci/common/bundled_templates/node/basic/` | `madsci new node` template |

## Creating a Node

### 1. Scaffold with template
```bash
madsci new node
# or: madsci new module  (full module with interface, types, tests, Dockerfile)
```

### 2. Minimal RestNode
```python
from madsci.node_module.rest_node_module import RestNode
from madsci.node_module.helpers import action

class MyInstrumentNode(RestNode):
    """Node for controlling MyInstrument."""

    def startup_handler(self):
        """Initialize instrument connections."""
        self.instrument = MyInstrumentDriver()

    def shutdown_handler(self):
        """Clean up instrument connections."""
        self.instrument.disconnect()

    @action(name="measure", description="Take a measurement")
    def measure(self, sample_id: str, temperature: float = 25.0) -> dict:
        result = self.instrument.measure(sample_id, temp=temperature)
        return {"sample_id": sample_id, "value": result}

if __name__ == "__main__":
    node = MyInstrumentNode()
    node.start_node()
```

### 3. Configuration
Nodes use `NodeConfig` (AbstractNode) or `RestNodeConfig` (RestNode), both inheriting from `MadsciBaseSettings`:

```python
# RestNodeConfig key fields:
node_name: Optional[str]       # Human name (defaults to class name)
node_id: Optional[str]         # ULID (auto-generated)
node_type: Optional[NodeType]  # DEVICE, COMPUTE, etc.
node_url: AnyUrl               # Default: http://127.0.0.1:2000
status_update_interval: float  # Default: 2.0s
state_update_interval: float   # Default: 2.0s
enable_registry_resolution: bool  # Default: True
enable_rate_limiting: bool     # Default: True
```

Config is discovered via walk-up file search (see CLAUDE.md). Override with environment variables using `NODE_` prefix or pass directly:
```python
node = MyNode(node_config=RestNodeConfig(node_url="http://0.0.0.0:3000"))
```

### Deprecated: NodeDefinition

`NodeDefinition` is **deprecated as of v0.7.0**. Node identity now comes from `NodeConfig`/`RestNodeConfig` plus the ID Registry.

- Do not use `NodeDefinition` or `*.node.yaml` definition files in new code
- Use `NodeConfig` or `RestNodeConfig` (both are `MadsciBaseSettings` subclasses)
- Run `madsci migrate` to convert legacy `*.node.yaml` files

## The @action Decorator

Register methods as node actions. Discovered automatically at init.

```python
from madsci.node_module.helpers import action

# With explicit parameters
@action(name="dispense", description="Dispense liquid", blocking=True)
def dispense(self, volume_ul: float, well: str) -> dict:
    ...

# Minimal (name from function, description from docstring, blocking=True)
@action
def home(self):
    """Home all axes to reference position."""
    self.instrument.home()
```

**Parameters:**
- `name` (str, optional): Action name (defaults to function name)
- `description` (str, optional): Description (defaults to docstring)
- `blocking` (bool, default `True`): Whether the action blocks concurrent actions via `_action_lock`

**Behind the scenes:** Sets `__is_madsci_action__ = True` on the function. `AbstractNode.__init__()` scans `__class__.__dict__` for this flag and auto-registers via `_add_action()`.

## Action Parameters and Return Types

### Regular parameters
Standard Python types become JSON-serializable action arguments:
```python
@action
def process(self, sample_id: str, count: int = 1, options: Optional[dict] = None) -> dict:
    ...
```

### File parameters (use `Path`, not `UploadFile`)
```python
from pathlib import Path

@action
def analyze_image(self, image: Path) -> dict:
    """Single file upload."""
    data = image.read_bytes()
    return {"size": len(data)}

@action
def batch_process(self, files: list[Path]) -> dict:
    """Multiple file upload."""
    return {"count": len(files)}
```

### Location parameters
```python
from madsci.common.types.location_types import LocationArgument

@action
def transfer(self, source: LocationArgument, destination: LocationArgument) -> dict:
    ...
```

### Annotated parameters (extra metadata)
```python
from typing import Annotated

@action
def calibrate(self, offset: Annotated[float, "Offset in mm, range -10 to 10"]) -> dict:
    ...
```

### Return types
```python
from madsci.common.types.action_types import ActionFiles, ActionDatapoints
from madsci.common.types.data_types import DataPoint

# Plain dict/Pydantic model -> json_result
@action
def measure(self) -> dict:
    return {"value": 42}

# Path -> single file result
@action
def capture(self) -> Path:
    return Path("/tmp/image.png")

# ActionFiles -> multiple named files
@action
def generate_report(self) -> ActionFiles:
    return ActionFiles(report=Path("report.pdf"), data=Path("data.csv"))

# Tuple -> (json_result, files, datapoints)
@action
def full_result(self) -> tuple[dict, ActionFiles, ActionDatapoints]:
    return (
        {"status": "ok"},
        ActionFiles(output=Path("out.csv")),
        ActionDatapoints(dp=DataPoint(label="measurement", value=42)),
    )
```

## Node Lifecycle

```
__init__()
  ├── Load NodeConfig (walk-up discovery)
  ├── Synthesize NodeInfo
  ├── Resolve registry identity (if enabled)
  ├── Configure clients (EventClient, ResourceClient, DataClient)
  └── Discover @action methods

start_node()
  ├── Establish event_client_context
  ├── Log startup
  └── _startup() thread:
      ├── startup_handler()       ← Override this
      ├── template_handler()      ← Override for resource/location templates
      └── Status/state update loops (every N seconds)
          ├── status_handler()    ← Override to populate node_status
          └── state_handler()     ← Override to populate node_state

Per-action execution:
  ├── Parse args (TypeAnalyzer)
  ├── Validate required args
  ├── Check node ready (not busy/locked/errored)
  ├── Execute in daemon thread (with _action_lock if blocking)
  ├── Process result -> ActionResult
  └── Update action_history & log status

shutdown:
  ├── shutdown_handler()          ← Override for cleanup
  ├── Release registry identity
  └── Teardown clients
```

## REST API Endpoints (RestNode)

### Standard endpoints
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/status` | Node operational status |
| `GET` | `/info` | Node metadata, actions, capabilities |
| `GET` | `/state` | Custom state dict |
| `POST` | `/config` | Update config fields |
| `GET` | `/log` | EventClient logs |
| `POST` | `/admin/{command}` | Admin commands (lock, unlock, shutdown) |
| `GET` | `/action` | Action history |

### Per-action endpoints (3-phase file upload)
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/action/{name}` | Create action, get `action_id` |
| `POST` | `/action/{name}/{id}/upload/{param}` | Upload file(s) for a parameter |
| `POST` | `/action/{name}/{id}/start` | Start execution |
| `GET` | `/action/{name}/{id}/status` | Poll action status |
| `GET` | `/action/{name}/{id}/result` | Get result (files as key list) |
| `GET` | `/action/{id}/download` | Download all files as ZIP |

## NodeStatus

```python
# Operational flags:
busy: bool          # Currently executing an action
paused: bool        # Manually paused
locked: bool        # Locked via admin command
stopped: bool       # Node stopped
errored: bool       # Node in error state
disconnected: bool  # Lost connection
initializing: bool  # Still starting up

# Computed:
ready: bool         # True only if no flags set and no waiting_for_config
description: str    # Human-readable reason if not ready
```

## Resource/Location Template Registration

Declare templates as ClassVar lists for automatic registration at startup:

```python
class MyNode(RestNode):
    resource_templates: ClassVar[list[NodeResourceTemplateDefinition]] = [
        NodeResourceTemplateDefinition(
            template_name="sample_plate",
            description="96-well sample plate",
            version="1.0",
        ),
    ]

    # Representation templates define how this node "sees" a location
    location_representation_templates: ClassVar[
        list[NodeRepresentationTemplateDefinition]
    ] = [
        NodeRepresentationTemplateDefinition(
            template_name="mynode_slot_repr",
            default_values={"slot_index": 0},
            required_overrides=["slot_index"],
            version="1.0.0",
        ),
    ]

    # Intrinsic locations are auto-created on startup with '{node_name}.' prefix
    intrinsic_locations: ClassVar[list[NodeIntrinsicLocationDefinition]] = [
        NodeIntrinsicLocationDefinition(
            location_name="slot_1",  # becomes "{node_name}.slot_1"
            representation_template_name="mynode_slot_repr",
            representation_overrides={"slot_index": 1},
            resource_template_name="sample_plate",
        ),
    ]

    def template_handler(self):
        """Called at startup to register templates. Override for custom logic."""
        super().template_handler()
```

## Datapoint Helpers

Upload data to the Data Manager from within actions:

```python
@action
def measure(self) -> dict:
    value = self.instrument.read()

    # Single value datapoint
    dp_id = self.create_and_upload_value_datapoint(value=value, label="measurement")

    # File datapoint
    file_id = self.create_and_upload_file_datapoint(
        file_path=Path("output.csv"), label="raw_data"
    )

    # Custom datapoint
    from madsci.common.types.data_types import DataPoint
    dp = DataPoint(label="custom", value={"nested": "data"})
    self.upload_datapoint(dp)

    return {"measurement": value, "datapoint_id": dp_id}
```

## Testing Nodes

```python
from fastapi.testclient import TestClient

def test_node_action():
    node = MyInstrumentNode(
        node_config=RestNodeConfig(
            enable_registry_resolution=False,  # Critical for tests
            node_url="http://127.0.0.1:2000",
        )
    )
    node.start_node(testing=True)  # Configures routes without starting uvicorn

    client = TestClient(node.rest_api)

    # Check info
    response = client.get("/info")
    assert response.status_code == 200
    assert "measure" in response.json()["actions"]

    # Run action (no file params)
    response = client.post("/action/measure", json={"sample_id": "ABC123"})
    assert response.status_code == 200
    action_id = response.json()["action_id"]

    # Start and get result
    client.post(f"/action/measure/{action_id}/start")
    import time; time.sleep(0.5)
    result = client.get(f"/action/measure/{action_id}/result")
    assert result.json()["json_result"]["sample_id"] == "ABC123"
```

## Common Pitfalls

- **ULID not UUID**: Always use `new_ulid_str()` from `madsci.common.utils` for IDs
- **Path not UploadFile**: File parameters use `pathlib.Path`, not FastAPI's `UploadFile`
- **blocking=True by default**: Actions serialize unless you set `blocking=False`
- **Registry in tests**: Always set `enable_registry_resolution=False` in test configs
- **Config discovery**: `NodeConfig` walks up directories looking for `settings.yaml`, `node.settings.yaml`, etc. Set `_settings_dir` to control where it looks
- **Client lazy init**: `self.resource_client`, `self.data_client`, `self.event_client` are created on first access. If the corresponding service is unavailable, the first access will fail
- **AnyUrl trailing slash**: Pydantic's `AnyUrl` always adds a trailing slash to URLs
