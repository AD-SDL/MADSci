# MADSci Node Module

Framework for creating laboratory instrument nodes that integrate with MADSci workcells via REST APIs.

## Features

- **REST API server**: Automatic FastAPI server generation for your instrument
- **Action system**: Declarative action definitions with automatic validation
- **State management**: Periodic state polling and reporting
- **Event integration**: Built-in logging to MADSci Event Manager
- **Resource integration**: Access to MADSci Resource and Data Managers
- **Lifecycle management**: Startup, shutdown, and error handling
- **Configuration**: YAML-based node configuration and deployment

## Installation

See the main [README](../../README.md#installation) for installation options. This package is available as:
- PyPI: `pip install madsci.node_module`
- Docker: Included in `ghcr.io/ad-sdl/madsci`
- **Example nodes**: See [example_lab/example_modules/](../../example_lab/example_modules/)

## Quick Start

### 1. Create a Node Class

```python
from madsci.node_module.rest_node_module import RestNode
from madsci.node_module.helpers import action
from madsci.common.types.action_types import ActionResult, ActionSucceeded
from madsci.common.types.node_types import RestNodeConfig
from typing import Any
from pathlib import Path

class MyInstrumentConfig(RestNodeConfig):
    """Configuration for your instrument."""
    device_port: str = "/dev/ttyUSB0"
    timeout: int = 30

class MyInstrumentNode(RestNode):
    """Node for controlling my laboratory instrument."""

    config: MyInstrumentConfig = MyInstrumentConfig()
    config_model = MyInstrumentConfig

    def startup_handler(self) -> None:
        """Initialize device connection."""
        # Connect to your instrument
        self.device = MyDeviceInterface(port=self.config.device_port)
        self.logger.log("Instrument initialized!")

    def shutdown_handler(self) -> None:
        """Clean up device connection."""
        if hasattr(self, 'device'):
            self.device.disconnect()

    def state_handler(self) -> dict[str, Any]:
        """Report current instrument state."""
        if hasattr(self, 'device'):
            self.node_state = {
                "temperature": self.device.get_temperature(),
                "status": self.device.get_status()
            }

    @action
    def measure_sample(self, sample_id: str, duration: int = 60) -> ActionResult:
        """Measure a sample for the specified duration."""
        # Your instrument control logic here
        result = self.device.measure(sample_id, duration)

        # Log results to Data Manager (optional)
        if hasattr(self, 'data_client'):
            self.data_client.submit_datapoint(
                ValueDataPoint(
                    label=f"measurement_{sample_id}",
                    value=result
                )
            )

        return ActionSucceeded(data=result)

    @action
    def run_protocol(self, protocol_file: Path) -> ActionResult:
        """Execute a protocol file."""
        self.device.load_protocol(protocol_file)
        self.device.run()
        return ActionSucceeded()

if __name__ == "__main__":
    node = MyInstrumentNode()
    node.start_node()  # Starts REST server
```

### 2. Create Node Definition

Create a YAML file (e.g., `my_instrument.node.yaml`):

```yaml
node_name: my_instrument_1
node_id: 01JYKZDPANTNRYXF5TQKRJS0F2  # Generate with ulid
node_description: My laboratory instrument for sample analysis
node_type: device
module_name: my_instrument
module_version: 1.0.0
```

### 3. Run Your Node

```bash
# Run directly
python my_instrument_node.py

# Or with a pre-defined node
python my_instrument_node.py --node_definition my_instrument.node.yaml

# Node will be available at http://localhost:2000/docs
```

## Core Concepts

### Actions
Actions are the primary interface for interacting with nodes:

```python
@action
def simple_action(self, param: str) -> ActionResult:
    """A simple action with one parameter."""
    return ActionSucceeded(data={"received": param})

@action
def complex_action(
    self,
    sample_id: str,
    temperature: float = 25.0,
    protocol_file: Path = None,
    metadata: dict = None
) -> ActionResult:
    """A more complex action with multiple parameters."""
    # Action implementation
    return ActionSucceeded()
```

**Action features:**
- Automatic parameter validation via type hints
- File uploads supported with `Path` parameters
- Optional parameters with defaults
- Automatic OpenAPI documentation generation
- Result validation and serialization

### Configuration
Node configuration using Pydantic settings:

```python
class MyNodeConfig(RestNodeConfig):
    # Device-specific settings
    device_ip: str = Field(description="Device IP address")
    device_port: int = Field(default=502, description="Device port")

    # Operational settings
    measurement_timeout: int = Field(default=30, description="Timeout in seconds")
    auto_calibrate: bool = Field(default=True, description="Enable auto-calibration")

    # Advanced settings
    retry_attempts: int = Field(default=3, ge=1, description="Number of retry attempts")
```

### Lifecycle Handlers
Manage node startup, shutdown, and state:

```python
class MyNode(RestNode):
    def startup_handler(self) -> None:
        """Called on node initialization."""
        # Initialize connections, load calibration, etc.
        pass

    def shutdown_handler(self) -> None:
        """Called on node shutdown."""
        # Clean up resources, close connections, etc.
        pass

    def state_handler(self) -> dict[str, Any]:
        """Called periodically to update node state."""
        self.node_state = {
            "connected": self.device.is_connected(),
            "ready": self.device.is_ready()
        }
```

### Integration with MADSci Ecosystem

Nodes automatically integrate with other MADSci services:

```python
class IntegratedNode(RestNode):
    @action
    def process_sample(self, sample_id: str) -> ActionResult:
        # Get sample info from Resource Manager
        sample = self.resource_client.get_resource(sample_id)

        # Process sample
        result = self.device.process(sample)

        # Store results in Data Manager
        self.data_client.submit_datapoint(
            ValueDataPoint(label="processing_result", value=result)
        )

        # Log event
        self.logger.log(f"Processed sample {sample_id}")

        return ActionSucceeded(data=result)
```

## Example Nodes

See complete working examples in [example_lab/example_modules/](../../example_lab/example_modules/):

- **[liquidhandler.py](../../example_lab/example_modules/liquidhandler.py)**: Liquid handling robot
- **[platereader.py](../../example_lab/example_modules/platereader.py)**: Microplate reader
- **[robotarm.py](../../example_lab/example_modules/robotarm.py)**: Robotic arm

## Deployment

### Docker Deployment
```dockerfile
FROM ghcr.io/ad-sdl/madsci:latest

COPY my_instrument_node.py /app/
COPY my_instrument.node.yaml /app/

WORKDIR /app
EXPOSE 2000

CMD ["python", "my_instrument_node.py"]
```

### Integration with Workcells
Nodes are automatically discovered by workcells via their REST APIs. Configure in your workcell definition:

```yaml
# workcell.yaml
nodes:
  my_instrument_1: "http://my-instrument:2000"
```

### Testing Your Node

```python
from madsci.client.node.rest_node_client import RestNodeClient

client = RestNodeClient("http://localhost:2000")

# Check node status
status = client.get_status()

# Execute actions
result = client.execute_action("measure_sample", {
    "sample_id": "sample_001",
    "duration": 120
})
```

## Advanced Features

### Custom Error Handling
```python
@action
def risky_action(self, param: str) -> ActionResult:
    try:
        result = self.device.risky_operation(param)
        return ActionSucceeded(data=result)
    except DeviceError as e:
        return ActionFailed(error=f"Device error: {e}")
```

### File Handling
```python
@action
def process_file(self, input_file: Path, output_dir: Path = None) -> ActionResult:
    """Process an uploaded file."""
    # input_file is automatically handled as file upload
    # output_dir is optional with default handling

    processed_data = self.device.process_file(input_file)

    # Return files in response
    return ActionSucceeded(
        data=processed_data,
        files={"result.csv": "/path/to/result.csv"}
    )
```

**Working examples**: See [example_lab/](../../example_lab/) for a complete working laboratory with multiple integrated nodes.
