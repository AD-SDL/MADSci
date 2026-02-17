# Tutorial 2: Your First Node

**Time to Complete**: ~30 minutes
**Prerequisites**: [Tutorial 1: Exploring MADSci](01-exploration.md), Python 3.10+
**Docker Required**: No

## What You'll Learn

In this tutorial, you'll:

1. Create a complete node module using `madsci new module`
2. Understand the module structure and file organization
3. Explore the interface pattern (real vs. fake)
4. Run and test your node without any services
5. Interact with your node via HTTP

By the end, you'll have a working node that you can test entirely offline.

## The Module Concept

Remember from Tutorial 1:

- **Module**: A complete package containing everything to control an instrument
- **Node**: The runtime server that receives action requests
- **Interface**: The class that handles hardware communication

The key insight is that the **interface is independent of MADSci**. You can use it directly in notebooks or scripts without running a node.

## Step 1: Create Your Module

Let's create a module for a simulated temperature sensor:

```bash
# Make sure you're in your tutorial directory with venv activated
cd madsci-tutorial
source .venv/bin/activate

# Create a new module
madsci new module --name temp_sensor
```

You'll see interactive prompts:

```
Create New Module

  Module name: temp_sensor
  Description: Temperature sensor module
  Author: Your Name
  Include fake interface? [Y/n]: Y
  Include tests? [Y/n]: Y
  Include Dockerfile? [Y/n]: Y

Files to be created:
  temp_sensor_module/
  ├── src/
  │   ├── __init__.py
  │   ├── temp_sensor_rest_node.py
  │   ├── temp_sensor_interface.py
  │   ├── temp_sensor_fake_interface.py
  │   └── temp_sensor_types.py
  ├── tests/
  │   ├── __init__.py
  │   └── test_temp_sensor_interface.py
  ├── Dockerfile
  ├── pyproject.toml
  └── README.md

Create these files? [Y/n]: Y

✓ Module created successfully!

Next steps:
  cd temp_sensor_module
  pip install -e .
  python src/temp_sensor_rest_node.py
```

## Step 2: Explore the Module Structure

Let's look at what was created:

```bash
cd temp_sensor_module
tree
```

```
temp_sensor_module/
├── src/
│   ├── __init__.py
│   ├── temp_sensor_rest_node.py      # The MADSci node server
│   ├── temp_sensor_interface.py      # Real hardware interface
│   ├── temp_sensor_fake_interface.py # Simulated interface for testing
│   └── temp_sensor_types.py          # Type definitions and config
├── tests/
│   ├── __init__.py
│   └── test_temp_sensor_interface.py # Interface tests
├── Dockerfile                         # Container build
├── pyproject.toml                     # Package dependencies
└── README.md                          # Documentation
```

### Understanding Each File

#### `temp_sensor_types.py` - Type Definitions

This file centralizes all type definitions for the module:

```python
"""Type definitions for the temp_sensor module."""

from typing import Literal
from pydantic import BaseModel, Field
from madsci.node_module import RestNodeConfig


class TempSensorNodeConfig(RestNodeConfig):
    """Configuration for the temperature sensor node."""

    interface_type: Literal["real", "fake"] = Field(
        default="fake",
        description="Which interface implementation to use",
    )
    port: str = Field(
        default="/dev/ttyUSB0",
        description="Serial port for real hardware",
    )
    sample_rate: float = Field(
        default=1.0,
        description="Sampling rate in Hz",
    )


class TempSensorInterfaceConfig(BaseModel):
    """Configuration for the interface."""

    timeout: float = Field(default=5.0, description="Communication timeout")
    retry_count: int = Field(default=3, description="Number of retries")


class TemperatureReading(BaseModel):
    """A temperature reading from the sensor."""

    value: float = Field(..., description="Temperature in Celsius")
    timestamp: str = Field(..., description="ISO timestamp of reading")
    unit: str = Field(default="celsius", description="Temperature unit")
```

#### `temp_sensor_interface.py` - Real Hardware Interface

The interface handles actual hardware communication:

```python
"""Real hardware interface for the temperature sensor."""

from datetime import datetime, timezone
import serial
from temp_sensor_types import TempSensorInterfaceConfig, TemperatureReading


class TempSensorInterface:
    """Interface for communicating with real temperature sensor hardware.

    This class is independent of MADSci and can be used directly
    in notebooks or scripts.
    """

    def __init__(self, config: TempSensorInterfaceConfig, port: str = "/dev/ttyUSB0"):
        self.config = config
        self.port = port
        self._connection: serial.Serial | None = None

    def connect(self) -> None:
        """Establish connection to the sensor."""
        self._connection = serial.Serial(
            self.port,
            baudrate=9600,
            timeout=self.config.timeout,
        )

    def disconnect(self) -> None:
        """Close the connection."""
        if self._connection:
            self._connection.close()
            self._connection = None

    def read_temperature(self) -> TemperatureReading:
        """Read current temperature from the sensor."""
        if not self._connection:
            raise RuntimeError("Not connected to sensor")

        # Send read command and get response
        self._connection.write(b"READ\n")
        response = self._connection.readline().decode().strip()
        value = float(response)

        return TemperatureReading(
            value=value,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def set_sample_rate(self, rate: float) -> None:
        """Configure the sensor's sample rate."""
        if not self._connection:
            raise RuntimeError("Not connected to sensor")

        self._connection.write(f"RATE {rate}\n".encode())
        # Wait for acknowledgment
        self._connection.readline()
```

#### `temp_sensor_fake_interface.py` - Simulated Interface

The fake interface mimics the real one for testing:

```python
"""Fake interface for testing without hardware."""

import random
import time
from datetime import datetime, timezone
from temp_sensor_types import TempSensorInterfaceConfig, TemperatureReading


class TempSensorFakeInterface:
    """Simulated interface for testing without hardware.

    This interface has the same API as TempSensorInterface but
    generates fake data instead of communicating with hardware.
    """

    def __init__(
        self,
        config: TempSensorInterfaceConfig,
        latency: float = 0.1,
        base_temp: float = 22.0,
    ):
        self.config = config
        self.latency = latency
        self.base_temp = base_temp
        self.sample_rate = 1.0

        # Internal state for testing assertions
        self._connected = False
        self._reading_count = 0
        self._state: dict = {}

    def connect(self) -> None:
        """Simulate connection."""
        time.sleep(self.latency)  # Simulate connection time
        self._connected = True
        self._state["connected_at"] = datetime.now(timezone.utc).isoformat()

    def disconnect(self) -> None:
        """Simulate disconnection."""
        self._connected = False

    def read_temperature(self) -> TemperatureReading:
        """Return a simulated temperature reading."""
        if not self._connected:
            raise RuntimeError("Not connected to sensor")

        time.sleep(self.latency)  # Simulate read time
        self._reading_count += 1

        # Generate realistic-looking temperature with small variations
        value = self.base_temp + random.uniform(-0.5, 0.5)

        return TemperatureReading(
            value=round(value, 2),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def set_sample_rate(self, rate: float) -> None:
        """Simulate setting sample rate."""
        time.sleep(self.latency)
        self.sample_rate = rate
        self._state["sample_rate"] = rate

    # Methods for testing assertions
    def get_state(self) -> dict:
        """Get internal state for test assertions."""
        return {
            "connected": self._connected,
            "reading_count": self._reading_count,
            "sample_rate": self.sample_rate,
            **self._state,
        }

    def reset_state(self) -> None:
        """Reset internal state for test isolation."""
        self._connected = False
        self._reading_count = 0
        self.sample_rate = 1.0
        self._state = {}
```

#### `temp_sensor_rest_node.py` - The Node Server

The node wires the interface to MADSci:

```python
"""MADSci REST node for the temperature sensor."""

from madsci.node_module import RestNode, action
from temp_sensor_types import (
    TempSensorNodeConfig,
    TempSensorInterfaceConfig,
    TemperatureReading,
)
from temp_sensor_interface import TempSensorInterface
from temp_sensor_fake_interface import TempSensorFakeInterface


class TempSensorNode(RestNode):
    """MADSci node for controlling a temperature sensor.

    This node wraps the temperature sensor interface and exposes
    its functionality via REST API actions.
    """

    config: TempSensorNodeConfig = TempSensorNodeConfig()
    config_model = TempSensorNodeConfig

    # Interface will be set during startup
    interface: TempSensorInterface | TempSensorFakeInterface

    def startup_handler(self) -> None:
        """Initialize the interface on node startup."""
        interface_config = TempSensorInterfaceConfig()

        if self.config.interface_type == "real":
            self.interface = TempSensorInterface(
                config=interface_config,
                port=self.config.port,
            )
        else:
            self.interface = TempSensorFakeInterface(
                config=interface_config,
            )

        self.interface.connect()
        self.logger.info(
            f"Temperature sensor initialized (interface: {self.config.interface_type})"
        )

    def shutdown_handler(self) -> None:
        """Clean up on node shutdown."""
        if hasattr(self, "interface"):
            self.interface.disconnect()
            self.logger.info("Temperature sensor disconnected")

    @action
    def read_temperature(self) -> TemperatureReading:
        """Read the current temperature.

        Returns:
            TemperatureReading with value, timestamp, and unit.
        """
        reading = self.interface.read_temperature()
        self.logger.info(f"Temperature reading: {reading.value}°C")
        return reading

    @action
    def set_sample_rate(self, rate: float) -> dict:
        """Configure the sampling rate.

        Args:
            rate: Sample rate in Hz.

        Returns:
            Confirmation of the new rate.
        """
        self.interface.set_sample_rate(rate)
        return {"sample_rate": rate, "status": "configured"}


if __name__ == "__main__":
    node = TempSensorNode()
    node.start_server()
```

## Step 3: Install Your Module

Install the module in development mode:

```bash
pip install -e .
```

## Step 4: Run the Node

Start your node with the fake interface (no hardware needed):

```bash
python src/temp_sensor_rest_node.py
```

You should see:

```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Temperature sensor initialized (interface: fake)
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:2000 (Press CTRL+C to quit)
```

## Step 5: Interact with Your Node

In a new terminal, test your node:

```bash
# Check node health
curl http://localhost:2000/health
```

Response:
```json
{"status": "healthy"}
```

```bash
# Get node information
curl http://localhost:2000/info
```

Response:
```json
{
  "node_name": "temp_sensor",
  "module_name": "temp_sensor_module",
  "actions": ["read_temperature", "set_sample_rate"],
  "status": "ready"
}
```

```bash
# Read temperature
curl -X POST http://localhost:2000/actions/read_temperature \
  -H "Content-Type: application/json" \
  -d '{}'
```

Response:
```json
{
  "action_response": "succeeded",
  "action_result": {
    "value": 22.34,
    "timestamp": "2026-02-09T14:30:00.000000Z",
    "unit": "celsius"
  }
}
```

```bash
# Set sample rate
curl -X POST http://localhost:2000/actions/set_sample_rate \
  -H "Content-Type: application/json" \
  -d '{"rate": 2.0}'
```

Response:
```json
{
  "action_response": "succeeded",
  "action_result": {
    "sample_rate": 2.0,
    "status": "configured"
  }
}
```

## Step 6: Run the Tests

The generated module includes tests that use the fake interface:

```bash
pip install pytest
pytest tests/ -v
```

Output:
```
========================= test session starts ==========================
collected 4 items

tests/test_temp_sensor_interface.py::test_connect_disconnect PASSED
tests/test_temp_sensor_interface.py::test_read_temperature PASSED
tests/test_temp_sensor_interface.py::test_set_sample_rate PASSED
tests/test_temp_sensor_interface.py::test_read_without_connect PASSED

========================= 4 passed in 0.15s ============================
```

All tests pass without any hardware!

## Step 7: Use the Interface Directly

Remember, the interface is independent of MADSci. You can use it in a notebook or script:

```python
# In a Python script or Jupyter notebook
from temp_sensor_fake_interface import TempSensorFakeInterface
from temp_sensor_types import TempSensorInterfaceConfig

# Create interface directly (no node needed)
config = TempSensorInterfaceConfig()
interface = TempSensorFakeInterface(config, base_temp=25.0)

# Connect and read
interface.connect()

for i in range(5):
    reading = interface.read_temperature()
    print(f"Reading {i+1}: {reading.value}°C at {reading.timestamp}")

interface.disconnect()
```

Output:
```
Reading 1: 25.23°C at 2026-02-09T14:35:00.123456Z
Reading 2: 24.87°C at 2026-02-09T14:35:00.234567Z
Reading 3: 25.41°C at 2026-02-09T14:35:00.345678Z
Reading 4: 24.92°C at 2026-02-09T14:35:00.456789Z
Reading 5: 25.15°C at 2026-02-09T14:35:00.567890Z
```

## Switching Between Real and Fake

Switch to the real interface when hardware is available:

```bash
# Using environment variable
export INTERFACE_TYPE=real
export PORT=/dev/ttyUSB0
python src/temp_sensor_rest_node.py

# Or using command line (if supported)
python src/temp_sensor_rest_node.py --interface-type real --port /dev/ttyUSB0
```

## Key Takeaways

1. **Modules are complete packages**: Everything you need to control an instrument
2. **Interfaces are independent**: Use them directly without MADSci infrastructure
3. **Fake interfaces enable testing**: Develop and test without hardware
4. **Nodes are thin wrappers**: They wire interfaces to the MADSci ecosystem
5. **Configuration is centralized**: The `*_types.py` file contains all types

## What's Next?

You've created a working node module! Next steps:

### Next Tutorial

**[Tutorial 3: Your First Experiment](03-first-experiment.md)** - Write an experiment script that uses your node.

### Try These Exercises

1. **Add a new action**: Add a `get_statistics` action that returns min/max/average of recent readings
2. **Enhance the fake interface**: Add configurable failure scenarios for testing error handling
3. **Add more types**: Create a `SensorStatus` model and a `get_status` action

### Reference

- [Module Templates](../../docs/designs/template_system_design.md)
- [Node Development Guide](../guides/node_development.md)
- [Interface Patterns](../guides/integrator/03-developing-interfaces.md)
