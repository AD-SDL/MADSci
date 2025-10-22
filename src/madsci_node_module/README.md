# MADSci Node Module

Framework for creating laboratory instrument nodes that integrate with MADSci workcells via REST APIs.

## Features

- **REST API server**: Automatic FastAPI server generation with comprehensive OpenAPI documentation
- **Action system**: Declarative action definitions with flexible return types and automatic validation
- **Advanced return types**: Support for Pydantic models, files, JSON data, and datapoint IDs
- **File handling**: Seamless file upload/download with automatic path management
- **State management**: Periodic state polling and reporting
- **Event integration**: Built-in logging to MADSci Event Manager
- **Resource integration**: Access to MADSci Resource and Data Managers
- **Lifecycle management**: Startup, shutdown, and error handling
- **Configuration**: YAML-based node configuration and deployment

## Installation

See the main [README](../../README.md#installation) for installation options. This package is available as:
- PyPI: `pip install madsci.node_module`
- Docker: Included in `ghcr.io/ad-sdl/madsci`
- **Example nodes**: See [example_lab/example_modules/](../../example_lab/example_modules/) including the comprehensive [advanced_example_module.py](../../example_lab/example_modules/advanced_example_module.py)

## Quick Start

### 1. Create a Node Class

```python
from madsci.node_module.rest_node_module import RestNode
from madsci.node_module.helpers import action
from madsci.common.types.node_types import RestNodeConfig
from typing import Any
from pathlib import Path
from pydantic import BaseModel

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
    def measure_sample(self, sample_id: str, duration: int = 60) -> dict[str, float]:
        """Measure a sample and return results directly as JSON."""
        # Your instrument control logic here
        result = self.device.measure(sample_id, duration)
        return {"temperature": result.temp, "absorbance": result.abs}

    @action
    def run_protocol(self, protocol_file: Path) -> str:
        """Execute a protocol file and return datapoint ID."""
        self.device.load_protocol(protocol_file)
        results = self.device.run()

        # Upload results and return datapoint ID
        return self.create_and_upload_value_datapoint(
            value=results,
            label=f"protocol_results"
        )

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
Actions are the primary interface for interacting with nodes. They support flexible return types:

```python
# Return simple JSON data
@action
def get_temperature(self) -> float:
    """Get current temperature."""
    return self.device.get_temperature()

# Return custom Pydantic models
class AnalysisResult(BaseModel):
    sample_id: str
    concentration: float
    ph_level: float

@action
def analyze_sample(self, sample_id: str) -> AnalysisResult:
    """Analyze sample and return structured results."""
    result = self.device.analyze(sample_id)
    return AnalysisResult(
        sample_id=sample_id,
        concentration=result.conc,
        ph_level=result.ph
    )

# Return datapoint IDs for workflow integration
@action
def capture_data(self, location: str) -> str:
    """Capture data and return datapoint ID."""
    data = self.device.capture(location)
    return self.create_and_upload_value_datapoint(
        value=data,
        label=f"capture_{location}"
    )

# Handle file operations
@action
def process_file(self, input_file: Path) -> Path:
    """Process file and return output file path."""
    output_path = self.device.process_file(input_file)
    return output_path
```

**Action features:**
- **Flexible return types**: JSON data, Pydantic models, file paths, datapoint IDs
- **Automatic validation**: Parameter and return value validation via type hints
- **File handling**: Seamless file uploads/downloads with `Path` parameters
- **OpenAPI documentation**: Comprehensive auto-generated API documentation
- **Type safety**: Full type checking for complex nested data structures

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
    def process_sample(self, sample_id: str) -> str:
        # Get sample info from Resource Manager
        sample = self.resource_client.get_resource(sample_id)

        # Process sample
        result = self.device.process(sample)

        # Store results and return datapoint ID
        datapoint_id = self.create_and_upload_value_datapoint(
            value=result,
            label=f"processing_result_{sample_id}"
        )

        # Log event
        self.logger.log(f"Processed sample {sample_id}")

        return datapoint_id
```

### Return Type Options

Actions support multiple return patterns depending on your needs:

```python
class MyNode(RestNode):
    @action
    def get_status(self) -> dict[str, Any]:
        """Return status directly as JSON for immediate use."""
        return {"temperature": 25.0, "ready": True}

    @action
    def analyze_sample(self, sample_id: str) -> str:
        """Analyze sample and return datapoint ID for workflow storage."""
        analysis_data = {"purity": 95.2, "concentration": 1.25}
        return self.create_and_upload_value_datapoint(
            value=analysis_data,
            label=f"analysis_{sample_id}"
        )

    @action
    def generate_report(self, data: dict) -> Path:
        """Generate report file and return file path."""
        report_path = self.create_report(data)
        return report_path  # File automatically served via REST API

    @action
    def perform_measurement(self) -> None:
        """Perform action without returning data."""
        self.device.calibrate()
        # No return value needed
```

Choose the appropriate return type based on how the data will be used in workflows.

## Example Nodes

See complete working examples in [example_lab/example_modules/](../../example_lab/example_modules/):

- **[liquidhandler.py](../../example_lab/example_modules/liquidhandler.py)**: Liquid handling robot
- **[platereader.py](../../example_lab/example_modules/platereader.py)**: Microplate reader
- **[robotarm.py](../../example_lab/example_modules/robotarm.py)**: Robotic arm
- **[advanced_example_module.py](../../example_lab/example_modules/advanced_example_module.py)**: Comprehensive example showcasing advanced features

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

### Error Handling
```python
@action
def risky_action(self, param: str) -> dict[str, float]:
    """Actions can raise exceptions for error handling."""
    try:
        result = self.device.risky_operation(param)
        return {"result": result}
    except DeviceError as e:
        # Exceptions are automatically converted to HTTP error responses
        raise RuntimeError(f"Device error: {e}")
```

### File Handling
```python
@action
def process_file(self, file_input: Path, output_dir: Path = None) -> Path:
    """Process uploaded file and return output file."""
    # file_input is automatically handled as file upload
    # Process the file
    processed_data = self.device.process_file(file_input)

    # Save processed file
    output_path = output_dir / "result.csv" if output_dir else Path("result.csv")
    processed_data.to_csv(output_path)

    # Return file path - file is automatically served
    return output_path

@action
def get_multiple_files(self) -> list[Path]:
    """Return multiple files."""
    files = self.device.generate_reports()
    return files  # All files automatically served
```

**Working examples**: See [example_lab/](../../example_lab/) for a complete working laboratory with multiple integrated nodes.
