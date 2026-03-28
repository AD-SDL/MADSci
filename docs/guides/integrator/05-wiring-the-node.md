# Wiring the Node

**Audience**: Equipment Integrator
**Prerequisites**: [Developing Interfaces](./03-developing-interfaces.md), [Fake Interfaces](./04-fake-interfaces.md)
**Time**: ~30 minutes

## Overview

Once you have a working interface (and its fake counterpart), the next step is connecting it to a MADSci node server. The node is the REST API layer that the workcell communicates with to execute actions on your instrument. This guide covers:

1. How nodes and interfaces relate at runtime
2. Configuring the node with your types module
3. Registering actions with the `@action` decorator
4. Handling startup, shutdown, and state
5. Switching between interface variants

## Architecture Recap

```
Workcell Manager
      │
      ▼ (HTTP REST)
┌─────────────────────┐
│   RestNode Server    │  ← MADSci framework
│  (foo_rest_node.py)  │
│                      │
│  ┌────────────────┐  │
│  │  Interface      │  │  ← Your code
│  │  (foo_interface)│  │
│  └────────────────┘  │
└─────────────────────┘
      │
      ▼ (Serial/Socket/HTTP/SDK)
  Physical Instrument
```

The node server handles:
- REST API routing and request/response serialization
- Action lifecycle (queuing, status tracking, result storage)
- Health checks and status reporting
- File upload/download for action inputs and outputs
- Integration with MADSci managers (events, data, resources)

Your interface handles:
- All hardware communication logic
- Device state management
- Error handling and recovery

## Step 1: The Types Module

Every module should have a centralized types file (`foo_types.py`) that defines all configuration and data models. This was introduced in [Creating a Module](./02-creating-a-module.md).

```python
# my_sensor_types.py
from typing import Literal

from pydantic import BaseModel, Field
from madsci.common.types.module_types import NodeModuleSettings


class MySensorNodeConfig(NodeModuleSettings):
    """Node-level configuration for the sensor module."""

    module_name: str = "my_sensor"
    module_description: str = "Temperature and humidity sensor"
    module_version: str = "1.0.0"

    # Interface selection
    interface_type: Literal["real", "fake", "sim"] = "fake"

    # Hardware settings (used by real interface)
    serial_port: str = "/dev/ttyUSB0"
    baud_rate: int = 9600

    # Behavior settings
    default_samples: int = 10
    sample_interval: float = 1.0


class SensorReading(BaseModel):
    """A single sensor reading."""

    temperature: float = Field(description="Temperature in Celsius")
    humidity: float = Field(description="Relative humidity percentage")
    timestamp: str = Field(description="ISO 8601 timestamp")


class CalibrationResult(BaseModel):
    """Result of a calibration procedure."""

    success: bool
    offset: float = 0.0
    message: str = ""
```

Key points:
- `NodeModuleSettings` provides standard fields (`module_name`, `module_version`, etc.)
- All settings are configurable via environment variables (e.g., `MY_SENSOR_INTERFACE_TYPE=real`)
- Data models use Pydantic for automatic validation and serialization

## Step 2: The Node Server

The node server extends `RestNode` and wires your interface to MADSci actions.

```python
# my_sensor_rest_node.py
"""MADSci REST node server for the sensor module."""

from madsci.node_module import RestNode, action
from madsci.common.types.action_types import (
    ActionResult,
    ActionSucceeded,
    ActionFailed,
)

from my_sensor_types import MySensorNodeConfig, SensorReading, CalibrationResult
from my_sensor_interface import MySensorInterface
from my_sensor_fake_interface import MySensorFakeInterface


class MySensorNode(RestNode):
    """MADSci node for the temperature/humidity sensor."""

    config: MySensorNodeConfig = MySensorNodeConfig()
    config_model = MySensorNodeConfig
    interface: MySensorInterface | MySensorFakeInterface

    def startup_handler(self) -> None:
        """Initialize the interface on node startup."""
        if self.config.interface_type == "real":
            self.interface = MySensorInterface(
                port=self.config.serial_port,
                baud_rate=self.config.baud_rate,
            )
        elif self.config.interface_type == "fake":
            self.interface = MySensorFakeInterface()
        else:
            raise ValueError(f"Unknown interface type: {self.config.interface_type}")

        self.interface.connect()

    def shutdown_handler(self) -> None:
        """Clean up the interface on node shutdown."""
        if hasattr(self, "interface"):
            self.interface.disconnect()

    @action
    def measure(self, samples: int = 1) -> ActionResult:
        """Take a measurement from the sensor.

        Args:
            samples: Number of samples to average.

        Returns:
            ActionResult with SensorReading data.
        """
        try:
            reading = self.interface.read_sensor(samples=samples)
            return ActionSucceeded(
                data=SensorReading(
                    temperature=reading["temperature"],
                    humidity=reading["humidity"],
                    timestamp=reading["timestamp"],
                ).model_dump(),
            )
        except Exception as e:
            return ActionFailed(errors=[str(e)])

    @action
    def calibrate(self, reference_temp: float = 25.0) -> ActionResult:
        """Run calibration against a known reference temperature.

        Args:
            reference_temp: Known reference temperature in Celsius.

        Returns:
            ActionResult with CalibrationResult data.
        """
        try:
            result = self.interface.calibrate(reference_temp)
            return ActionSucceeded(
                data=CalibrationResult(
                    success=result["success"],
                    offset=result.get("offset", 0.0),
                    message=result.get("message", "Calibration complete"),
                ).model_dump(),
            )
        except Exception as e:
            return ActionFailed(errors=[str(e)])

    @action
    def get_reading(self) -> ActionResult:
        """Get the most recent sensor reading without taking a new measurement."""
        try:
            reading = self.interface.get_last_reading()
            if reading is None:
                return ActionFailed(errors=["No readings available. Run 'measure' first."])
            return ActionSucceeded(data=reading)
        except Exception as e:
            return ActionFailed(errors=[str(e)])


if __name__ == "__main__":
    node = MySensorNode()
    node.start_node()
```

## Step 3: Understanding the `@action` Decorator

The `@action` decorator registers a method as a callable action on the node's REST API. When the node starts, it introspects all decorated methods to:

1. **Generate API endpoints**: Each action gets `POST /actions/{action_name}` endpoints
2. **Parse parameters**: Method arguments become action parameters (with type validation)
3. **Track execution**: Actions are queued, executed, and their status/results are stored
4. **Generate documentation**: OpenAPI docs are auto-generated from type hints and docstrings

### Parameter Types

Action methods support several parameter types:

```python
from pathlib import Path
from typing import Annotated

from madsci.common.types.action_types import (
    ActionResult,
    ActionSucceeded,
    ActionFiles,
    ActionJSON,
    ActionDatapoints,
)
from madsci.common.types.location_types import LocationArgument


@action
def simple_action(self, count: int = 5, name: str = "default") -> ActionResult:
    """Basic typed parameters are sent as JSON."""
    return ActionSucceeded()


@action
def file_action(self, protocol_file: Path) -> ActionResult:
    """Path parameters accept file uploads."""
    with open(protocol_file) as f:
        data = f.read()
    return ActionSucceeded(data={"lines": len(data.splitlines())})


@action
def location_action(
    self,
    source: LocationArgument,
    destination: LocationArgument,
) -> ActionResult:
    """LocationArgument parameters are resolved by the workcell."""
    # source.node_value contains the node-specific representation
    # source.resource contains the attached resource (if any)
    return ActionSucceeded()
```

### Return Values

Actions must return an `ActionResult`. Use the convenience subclasses:

```python
# Success with data
return ActionSucceeded(data={"temperature": 25.3})

# Success with files
return ActionSucceeded(files={"report": Path("/tmp/report.csv")})

# Failure with error messages
return ActionFailed(errors=["Sensor not responding", "Check connection"])
```

## Step 4: Startup and Shutdown Handlers

The `startup_handler` and `shutdown_handler` methods manage your interface's lifecycle:

```python
def startup_handler(self) -> None:
    """Called once when the node starts.

    Use this to:
    - Initialize the interface
    - Connect to hardware
    - Load calibration data
    - Register resources with the Resource Manager
    """
    self.interface = self._create_interface()
    self.interface.connect()

    # Optionally register resources
    if self.resource_client:
        self.resource_client.add_resource(
            Resource(resource_name="sensor_1", base_type="asset")
        )

def shutdown_handler(self) -> None:
    """Called when the node shuts down.

    Use this to:
    - Disconnect from hardware
    - Save state
    - Release resources
    """
    if hasattr(self, "interface"):
        self.interface.disconnect()
```

### State Handler

Override `state_handler` to expose custom state information:

```python
def state_handler(self) -> dict:
    """Return current node state.

    This is called by GET /state and included in status checks.
    """
    state = {}
    if hasattr(self, "interface"):
        state["connected"] = self.interface.is_connected()
        state["last_reading"] = self.interface.get_last_reading()
        state["calibration_valid"] = self.interface.is_calibrated()
    return state
```

### Status Handler

Override `status_handler` to customize the node's status reporting:

```python
from madsci.common.types.node_types import NodeStatus

def status_handler(self) -> NodeStatus:
    """Return current node status."""
    if not hasattr(self, "interface") or not self.interface.is_connected():
        return NodeStatus.ERROR
    return NodeStatus.IDLE
```

## Step 5: Interface Selection Pattern

The recommended pattern for switching between interface variants uses the config:

```python
def _create_interface(self):
    """Factory method for creating the appropriate interface."""
    interface_type = self.config.interface_type

    if interface_type == "real":
        from my_sensor_interface import MySensorInterface
        return MySensorInterface(
            port=self.config.serial_port,
            baud_rate=self.config.baud_rate,
        )
    elif interface_type == "fake":
        from my_sensor_fake_interface import MySensorFakeInterface
        return MySensorFakeInterface()
    elif interface_type == "sim":
        from my_sensor_sim_interface import MySensorSimInterface
        return MySensorSimInterface(
            sim_host=self.config.sim_host,
            sim_port=self.config.sim_port,
        )
    else:
        raise ValueError(f"Unknown interface type: {interface_type}")

def startup_handler(self) -> None:
    self.interface = self._create_interface()
    self.interface.connect()
```

Switch at runtime via environment variable:

```bash
# Development (default)
python my_sensor_rest_node.py

# With real hardware
MY_SENSOR_INTERFACE_TYPE=real python my_sensor_rest_node.py

# With simulator
MY_SENSOR_INTERFACE_TYPE=sim python my_sensor_rest_node.py
```

## Step 6: Data Upload Integration

Nodes can upload data to the Data Manager during action execution:

```python
@action
def measure_and_store(self, experiment_id: str = "") -> ActionResult:
    """Take a measurement and store it in the Data Manager."""
    reading = self.interface.read_sensor()

    # Upload a value datapoint
    self.create_and_upload_value_datapoint(
        label="temperature_reading",
        value=reading["temperature"],
        description="Temperature measurement from sensor",
    )

    # Upload a file datapoint
    import json
    from pathlib import Path

    data_file = Path("/tmp/sensor_data.json")
    data_file.write_text(json.dumps(reading))

    self.create_and_upload_file_datapoint(
        label="raw_sensor_data",
        file_path=data_file,
        description="Raw sensor data in JSON format",
    )

    return ActionSucceeded(data=reading)
```

## Step 7: Running the Node

Start your node server:

```bash
# Run with default config (fake interface)
python my_sensor_rest_node.py

# Override settings via environment variables
MY_SENSOR_SERIAL_PORT=/dev/ttyACM0 MY_SENSOR_INTERFACE_TYPE=real python my_sensor_rest_node.py
```

The node starts a FastAPI server (default port 2000). Test it:

```bash
# Check health
curl http://localhost:2000/health

# Get node info
curl http://localhost:2000/info

# Get current state
curl http://localhost:2000/state

# Execute an action
curl -X POST http://localhost:2000/actions/measure \
  -H "Content-Type: application/json" \
  -d '{"samples": 5}'

# Check action status
curl http://localhost:2000/actions/measure/{action_id}/status

# Get action result
curl http://localhost:2000/actions/measure/{action_id}/result
```

## Common Patterns

### Long-Running Actions

For actions that take significant time, the node framework handles asynchronous execution automatically. The caller gets an action ID immediately and polls for completion:

```python
@action
def long_measurement(self, duration_minutes: int = 60) -> ActionResult:
    """Run a long measurement campaign.

    The workcell will poll for completion automatically.
    """
    import time

    readings = []
    for i in range(duration_minutes * 6):  # Every 10 seconds
        reading = self.interface.read_sensor()
        readings.append(reading)
        time.sleep(10)

    return ActionSucceeded(data={"readings": readings, "count": len(readings)})
```

### Error Recovery

Handle errors gracefully in your actions:

```python
@action
def robust_measure(self, retries: int = 3) -> ActionResult:
    """Measure with automatic retry on failure."""
    last_error = None
    for attempt in range(retries):
        try:
            reading = self.interface.read_sensor()
            return ActionSucceeded(data=reading)
        except ConnectionError as e:
            last_error = e
            self.interface.reconnect()
        except TimeoutError as e:
            last_error = e
            self.interface.reset()

    return ActionFailed(
        errors=[f"Failed after {retries} attempts: {last_error}"]
    )
```

### Admin Commands

Nodes support admin commands for operational control:

```python
def run_admin_command(self, command: str, **kwargs) -> dict:
    """Handle admin commands."""
    if command == "reset":
        self.interface.reset()
        return {"status": "reset complete"}
    elif command == "reconnect":
        self.interface.disconnect()
        self.interface.connect()
        return {"status": "reconnected"}
    return super().run_admin_command(command, **kwargs)
```

## Location Templates

If your instrument interacts with specific locations (e.g., deck slots, sample positions), you can define location representation templates to describe the data your node needs for each location. See [Location Templates](./10-location-templates.md) for details.

## What's Next?

- [Location Templates](./10-location-templates.md) - Define location representation templates for your node
- [Testing Strategies](./06-testing-strategies.md) - Unit, integration, and hardware-in-the-loop testing
- [Debugging](./07-debugging.md) - Common issues and troubleshooting techniques
- [Tutorial: First Workcell](../../tutorials/04-first-workcell.md) - Connect your node to a workcell
