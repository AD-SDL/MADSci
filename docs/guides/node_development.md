# Node Development Quick Reference

> For comprehensive, interactive node development tutorials, see **[node_notebook.ipynb](../../examples/notebooks/node_notebook.ipynb)**

This guide provides quick reference information for node development patterns not covered in the interactive tutorial.

## Quick Start Checklist

1. **Start with the interactive tutorial**: Run `jupyter lab examples/notebooks/node_notebook.ipynb` for hands-on learning
2. **Choose a template**: Copy from `example_modules/` that matches your instrument type
3. **Define configuration**: Create your config class inheriting from `RestNodeConfig`
4. **Implement hardware interface**: Separate device communication logic
5. **Add action methods**: Use `@action` decorator on your methods
6. **Create resource templates**: Define lab materials your instrument handles
7. **Test thoroughly**: Use both unit tests and integration tests
8. **Deploy**: Add to `compose.yaml` and configure YAML files

## Production Deployment Patterns

### Docker Configuration Template
```yaml
# Add to compose.yaml
my_instrument:
  <<: *madsci-service
  container_name: my_instrument_1
  environment:
    - NODE_NAME=my_instrument_1
    - NODE_MODULE_NAME=my_instrument
    - NODE_URL=http://localhost:2010
  command: python example_modules/my_instrument.py
```

### Node Settings File
**`settings.yaml`** (or set via environment variables):
```yaml
node_name: my_instrument_1
node_module_name: my_instrument
node_url: http://localhost:2010
```

## Testing Patterns

### Unit Testing Template
```python
import pytest
from unittest.mock import Mock, patch
from my_instrument import MyInstrumentNode

class TestMyInstrumentNode:
    @pytest.fixture
    def node(self):
        node = MyInstrumentNode()
        node.logger = Mock()
        node.resource_client = Mock()
        return node

    def test_startup_handler(self, node):
        with patch.object(MyInstrumentInterface, 'connect'):
            node.startup_handler()
            assert node.hardware is not None
```

### Integration Testing
```python
def test_node_integration():
    base_url = "http://localhost:2010"
    response = requests.get(f"{base_url}/health")
    assert response.status_code == 200
```

## Advanced Patterns

### Concurrent Operations
```python
from concurrent.futures import ThreadPoolExecutor

class MyInstrumentNode(RestNode):
    def __init__(self):
        super().__init__()
        self.executor = ThreadPoolExecutor(max_workers=4)

    @action
    async def parallel_measurements(self, samples: list[str]) -> list[dict]:
        futures = [self.executor.submit(self._measure_single, s) for s in samples]
        return [f.result() for f in futures]
```

### State Machine Implementation
```python
from enum import Enum

class InstrumentState(Enum):
    IDLE = "idle"
    MEASURING = "measuring"
    ERROR = "error"

class MyInstrumentNode(RestNode):
    def _transition_state(self, new_state: InstrumentState):
        # Validation logic here
        self.state = new_state
```

## Security Best Practices

1. **Input Validation**: Always validate action parameters
2. **Command Sanitization**: Sanitize hardware command strings
3. **Authentication**: Implement authentication for sensitive operations
4. **Audit Logging**: Log all security-relevant operations
5. **Secure Communication**: Use TLS for production deployments

## Performance Optimization

1. **Connection Pooling**: Reuse network connections where possible
2. **Caching**: Cache expensive operations and calibration data
3. **Async Operations**: Use async/await for I/O bound operations
4. **Memory Management**: Clean up resources in shutdown handlers
5. **Profiling**: Profile critical code paths for bottlenecks

## Common Hardware Integration Patterns

### Serial Communication
```python
import serial

class MyInterface:
    def __init__(self, port: str, baudrate: int):
        self.connection = serial.Serial(port, baudrate, timeout=5.0)

    def send_command(self, cmd: str) -> str:
        self.connection.write(f"{cmd}\n".encode())
        return self.connection.readline().decode().strip()
```

### Network Devices
```python
import requests

class NetworkInterface:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()

    def send_command(self, endpoint: str, data: dict) -> dict:
        response = self.session.post(f"{self.base_url}/{endpoint}", json=data)
        return response.json()
```

### Vendor SDK Integration
```python
# Example for vendor-specific SDK
import vendor_sdk

class VendorInterface:
    def __init__(self, device_id: str):
        self.device = vendor_sdk.Device(device_id)
        self.device.connect()

    def __del__(self):
        if hasattr(self, 'device'):
            self.device.disconnect()
```

## Error Handling Patterns

### Custom Exceptions
```python
class InstrumentError(Exception):
    """Base class for instrument errors."""
    pass

class HardwareError(InstrumentError):
    """Hardware communication error."""
    pass

class CalibrationError(InstrumentError):
    """Calibration-related error."""
    pass
```

### Retry Logic
```python
import time
from functools import wraps

def retry(times=3, delay=1.0):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for i in range(times):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if i == times - 1:
                        raise
                    time.sleep(delay)
            return None
        return wrapper
    return decorator
```

## Location Templates

Nodes that interact with physical locations (deck slots, sample positions, waypoints) can declare **location representation templates** to describe the data they need for each location. The framework registers templates with the Location Manager at startup.

```python
from typing import ClassVar
from madsci.common.types.node_types import NodeRepresentationTemplateDefinition

class MyNode(RestNode):
    location_representation_templates: ClassVar[
        list[NodeRepresentationTemplateDefinition]
    ] = [
        NodeRepresentationTemplateDefinition(
            template_name="my_node_access",
            default_values={"speed": 50.0},
            schema_def={
                "type": "object",
                "properties": {
                    "position": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Coordinates for this location",
                    },
                    "speed": {
                        "type": "number",
                        "description": "Approach speed",
                    },
                },
                "required": ["position"],
            },
            required_overrides=["position"],
            version="1.0.0",
        ),
    ]
```

- `schema_def` provides a JSON Schema for validation and dashboard form rendering
- `default_values` are merged with per-location overrides at instantiation
- `required_overrides` lists fields that must be supplied for each location

For the full guide on representation templates, location templates, seed files, and programmatic usage, see [Location Templates](integrator/10-location-templates.md).

## Next Steps

1. **Complete the interactive tutorial**: Work through `examples/notebooks/node_notebook.ipynb` thoroughly
2. **Study example implementations**: Review all modules in `example_modules/`
3. **Start simple**: Begin with a basic node and add complexity gradually
4. **Test extensively**: Use both unit and integration testing
5. **Monitor in production**: Set up logging and health checks

## Reference Links

- **Interactive Tutorial**: [node_notebook.ipynb](../../examples/notebooks/node_notebook.ipynb)
- **Example Implementations**: [example_modules/](../../examples/example_lab/example_modules/)
- **Troubleshooting**: [Troubleshooting](troubleshooting.md)
- **Workflow Development**: [Workflow Development](workflow_development.md)
