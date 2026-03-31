# Creating a Module

This guide walks through creating a new MADSci module using the `madsci new module` command.

## Using the Module Scaffold

The fastest way to create a module is with the CLI:

```bash
madsci new module --name my_instrument
```

### Interactive Mode

By default, the command prompts for configuration:

```
Create New Module

  Module name: my_instrument
  Description: [My laboratory instrument controller]
  Author: [Your Name]

  Interface variants to include:
    [x] Real (hardware communication)
    [x] Fake (simulated, no hardware)
    [ ] Sim (external simulator connection)

  Include:
    [x] Tests
    [x] Dockerfile
    [x] GitHub Actions CI

Create these files? [Y/n]: Y

✓ Module created: my_instrument_module/

Next steps:
  cd my_instrument_module
  pip install -e .
  python src/my_instrument_rest_node.py
```

### Non-Interactive Mode

For scripting or CI:

```bash
madsci new module \
  --name my_instrument \
  --description "My laboratory instrument" \
  --no-interactive
```

## Generated Structure

The command creates:

```
my_instrument_module/
├── src/
│   ├── __init__.py
│   ├── my_instrument_rest_node.py      # MADSci REST node
│   ├── my_instrument_interface.py       # Real hardware interface
│   ├── my_instrument_fake_interface.py  # Fake interface for testing
│   └── my_instrument_types.py           # Type definitions
├── tests/
│   ├── __init__.py
│   └── test_my_instrument_interface.py  # Interface tests
├── Dockerfile
├── pyproject.toml
├── README.md
└── .env.example
```

## Understanding the Generated Files

### `my_instrument_types.py`

Centralized type definitions:

```python
"""Type definitions for my_instrument module."""

from typing import Literal
from pydantic import BaseModel, Field
from madsci.common.types.node_types import RestNodeConfig


class MyInstrumentNodeConfig(RestNodeConfig):
    """Configuration for the my_instrument node."""

    interface_type: Literal["real", "fake"] = Field(
        default="fake",
        description="Which interface implementation to use",
    )
    # Add your configuration fields here
    # port: str = Field(default="/dev/ttyUSB0", description="Serial port")


class MyInstrumentInterfaceConfig(BaseModel):
    """Configuration for the interface."""

    timeout: float = Field(default=5.0, description="Communication timeout")
    retry_count: int = Field(default=3, description="Number of retries")


# Add your data models here
class ActionResult(BaseModel):
    """Result from an action."""

    success: bool
    message: str = ""
    data: dict = Field(default_factory=dict)
```

### `my_instrument_interface.py`

Template for real hardware interface:

```python
"""Real hardware interface for my_instrument.

This class handles communication with the actual hardware.
It is independent of MADSci and can be used directly.
"""

from datetime import datetime, timezone
from my_instrument_types import MyInstrumentInterfaceConfig, ActionResult


class MyInstrumentInterface:
    """Interface for communicating with my_instrument hardware.

    Example usage:
        >>> interface = MyInstrumentInterface(port="/dev/ttyUSB0")
        >>> interface.connect()
        >>> result = interface.example_action(param="value")
        >>> interface.disconnect()
    """

    def __init__(
        self,
        config: MyInstrumentInterfaceConfig | None = None,
        # Add hardware-specific parameters
        # port: str = "/dev/ttyUSB0",
    ):
        self.config = config or MyInstrumentInterfaceConfig()
        # self.port = port
        self._connected = False

    def connect(self) -> None:
        """Establish connection to the hardware.

        Raises:
            ConnectionError: If connection fails.
        """
        # TODO: Implement hardware connection
        # self._connection = serial.Serial(self.port, 9600)
        self._connected = True

    def disconnect(self) -> None:
        """Close the connection."""
        # TODO: Implement disconnection
        # if self._connection:
        #     self._connection.close()
        self._connected = False

    def is_connected(self) -> bool:
        """Check if connected to hardware."""
        return self._connected

    def example_action(self, param: str) -> ActionResult:
        """Perform an example action.

        Args:
            param: Example parameter.

        Returns:
            ActionResult with operation status.

        Raises:
            RuntimeError: If not connected.
        """
        if not self._connected:
            raise RuntimeError("Not connected to hardware")

        # TODO: Implement actual hardware communication
        # self._connection.write(f"ACTION {param}\n".encode())
        # response = self._connection.readline().decode().strip()

        return ActionResult(
            success=True,
            message=f"Executed action with param: {param}",
            data={"timestamp": datetime.now(timezone.utc).isoformat()},
        )
```

### `my_instrument_fake_interface.py`

Simulated interface for testing:

```python
"""Fake interface for testing without hardware.

This interface simulates the real hardware behavior.
"""

import time
import random
from datetime import datetime, timezone
from my_instrument_types import MyInstrumentInterfaceConfig, ActionResult


class MyInstrumentFakeInterface:
    """Simulated interface for testing.

    Provides the same API as MyInstrumentInterface but
    generates fake data instead of hardware communication.
    """

    def __init__(
        self,
        config: MyInstrumentInterfaceConfig | None = None,
        latency: float = 0.1,
    ):
        self.config = config or MyInstrumentInterfaceConfig()
        self.latency = latency
        self._connected = False

        # Internal state for testing
        self._action_count = 0
        self._state: dict = {}

    def connect(self) -> None:
        """Simulate connection."""
        time.sleep(self.latency)
        self._connected = True
        self._state["connected_at"] = datetime.now(timezone.utc).isoformat()

    def disconnect(self) -> None:
        """Simulate disconnection."""
        self._connected = False

    def is_connected(self) -> bool:
        """Check connection status."""
        return self._connected

    def example_action(self, param: str) -> ActionResult:
        """Simulate an action.

        Args:
            param: Example parameter.

        Returns:
            Simulated ActionResult.
        """
        if not self._connected:
            raise RuntimeError("Not connected")

        time.sleep(self.latency)
        self._action_count += 1
        self._state["last_param"] = param

        return ActionResult(
            success=True,
            message=f"Fake executed with param: {param}",
            data={
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "fake": True,
                "action_count": self._action_count,
            },
        )

    # Testing helpers
    def get_state(self) -> dict:
        """Get internal state for assertions."""
        return {
            "connected": self._connected,
            "action_count": self._action_count,
            **self._state,
        }

    def reset_state(self) -> None:
        """Reset state between tests."""
        self._connected = False
        self._action_count = 0
        self._state = {}
```

### `my_instrument_rest_node.py`

The MADSci node server:

```python
"""MADSci REST node for my_instrument."""

from madsci.node_module import RestNode, action
from my_instrument_types import (
    MyInstrumentNodeConfig,
    MyInstrumentInterfaceConfig,
    ActionResult,
)


class MyInstrumentNode(RestNode):
    """MADSci node for controlling my_instrument."""

    config: MyInstrumentNodeConfig = MyInstrumentNodeConfig()
    config_model = MyInstrumentNodeConfig

    def startup_handler(self) -> None:
        """Initialize the interface on node startup."""
        interface_config = MyInstrumentInterfaceConfig()

        if self.config.interface_type == "real":
            from my_instrument_interface import MyInstrumentInterface
            self.interface = MyInstrumentInterface(config=interface_config)
        else:
            from my_instrument_fake_interface import MyInstrumentFakeInterface
            self.interface = MyInstrumentFakeInterface(config=interface_config)

        self.interface.connect()
        self.logger.info(
            f"my_instrument initialized (interface: {self.config.interface_type})"
        )

    def shutdown_handler(self) -> None:
        """Clean up on node shutdown."""
        if hasattr(self, "interface") and self.interface:
            self.interface.disconnect()
            self.logger.info("my_instrument disconnected")

    @action
    def example_action(self, param: str) -> ActionResult:
        """Execute an example action.

        Args:
            param: Example parameter to pass to the action.

        Returns:
            ActionResult with the operation status.
        """
        result = self.interface.example_action(param)
        self.logger.info(f"Action completed: {result.message}")
        return result


if __name__ == "__main__":
    node = MyInstrumentNode()
    node.start_server()
```

## Customizing Your Module

### Step 1: Define Your Data Models

Edit `my_instrument_types.py` to add your instrument-specific models:

```python
class MeasurementResult(BaseModel):
    """Result from a measurement."""
    value: float
    unit: str = "units"
    timestamp: str
    sample_id: str

class CalibrationData(BaseModel):
    """Calibration parameters."""
    offset: float = 0.0
    scale: float = 1.0
    calibrated_at: str | None = None
```

### Step 2: Implement the Real Interface

Edit `my_instrument_interface.py` with actual hardware communication:

```python
import serial

class MyInstrumentInterface:
    def __init__(self, port: str = "/dev/ttyUSB0"):
        self.port = port
        self._connection: serial.Serial | None = None

    def connect(self) -> None:
        self._connection = serial.Serial(
            self.port,
            baudrate=9600,
            timeout=5.0,
        )

    def measure(self, sample_id: str) -> MeasurementResult:
        self._connection.write(f"MEASURE {sample_id}\n".encode())
        response = self._connection.readline().decode().strip()
        value = float(response.split(",")[0])
        return MeasurementResult(
            value=value,
            sample_id=sample_id,
            timestamp=datetime.now().isoformat(),
        )
```

### Step 3: Update the Fake Interface

Mirror the real interface API in `my_instrument_fake_interface.py`:

```python
class MyInstrumentFakeInterface:
    def measure(self, sample_id: str) -> MeasurementResult:
        time.sleep(self.latency)
        return MeasurementResult(
            value=random.uniform(10.0, 20.0),
            sample_id=sample_id,
            timestamp=datetime.now().isoformat(),
        )
```

### Step 4: Add Node Actions

Expose interface methods as node actions in `my_instrument_rest_node.py`:

```python
@action
def measure(self, sample_id: str) -> MeasurementResult:
    """Take a measurement.

    Args:
        sample_id: Identifier for the sample.

    Returns:
        MeasurementResult with the value and metadata.
    """
    result = self.interface.measure(sample_id)
    self.logger.info(f"Measured {sample_id}: {result.value}")
    return result

@action
def calibrate(self) -> CalibrationData:
    """Run calibration procedure."""
    return self.interface.calibrate()
```

## Running Your Module

```bash
# Install in development mode
pip install -e .

# Run with fake interface (default)
python src/my_instrument_rest_node.py

# Run with real interface
INTERFACE_TYPE=real python src/my_instrument_rest_node.py

# Specify port
INTERFACE_TYPE=real PORT=/dev/ttyUSB0 python src/my_instrument_rest_node.py
```

## Testing Your Module

```bash
# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

## Next Steps

- [Developing Interfaces](03-developing-interfaces.md) - Interface patterns for different hardware types
- [Fake Interfaces](04-fake-interfaces.md) - Creating effective simulated interfaces
- [Testing Strategies](06-testing-strategies.md) - Comprehensive testing approaches
