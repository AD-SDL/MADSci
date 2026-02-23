# Fake Interfaces

This guide explains how to create effective fake (simulated) interfaces for testing without hardware.

## Why Fake Interfaces?

Fake interfaces are essential for:

1. **Development without hardware** - Work on nodes when hardware isn't available
2. **CI/CD testing** - Automated tests that run in any environment
3. **Demo environments** - Show functionality without physical equipment
4. **Debugging** - Isolate node logic from hardware issues
5. **Training** - Let new users explore without risk

## Core Principles

### 1. Same API as Real Interface

The fake interface must have identical method signatures:

```python
# Real interface
class MyInstrumentInterface:
    def connect(self) -> None: ...
    def measure(self, sample_id: str) -> MeasurementResult: ...
    def calibrate(self) -> CalibrationData: ...

# Fake interface - SAME methods
class MyInstrumentFakeInterface:
    def connect(self) -> None: ...
    def measure(self, sample_id: str) -> MeasurementResult: ...
    def calibrate(self) -> CalibrationData: ...
```

### 2. Realistic Timing

Simulate actual operation durations:

```python
class MyInstrumentFakeInterface:
    def __init__(self, latency: float = 0.1):
        self.latency = latency

    def measure(self, sample_id: str) -> MeasurementResult:
        # Real measurement takes ~2 seconds
        time.sleep(2.0 * self.latency)  # Scaled latency
        return MeasurementResult(...)

    def calibrate(self) -> CalibrationData:
        # Real calibration takes ~30 seconds
        time.sleep(30.0 * self.latency)
        return CalibrationData(...)
```

### 3. Realistic Data Generation

Generate plausible values, not just random noise:

```python
def measure(self, sample_id: str) -> MeasurementResult:
    # Base value with realistic drift and noise
    base_value = 22.0  # Room temperature
    drift = (time.time() % 100) * 0.01  # Slow drift
    noise = random.gauss(0, 0.1)  # Measurement noise

    return MeasurementResult(
        value=base_value + drift + noise,
        unit="celsius",
        timestamp=datetime.now().isoformat(),
    )
```

### 4. Internal State for Test Assertions

Track what happened for testing:

```python
class MyInstrumentFakeInterface:
    def __init__(self):
        self._connected = False
        self._measurements: list = []
        self._actions: list = []
        self._state: dict = {}

    def measure(self, sample_id: str) -> MeasurementResult:
        self._actions.append(("measure", sample_id))
        result = MeasurementResult(...)
        self._measurements.append(result)
        return result

    # Testing helpers
    def get_state(self) -> dict:
        """Get internal state for test assertions."""
        return {
            "connected": self._connected,
            "measurement_count": len(self._measurements),
            "actions": self._actions,
            **self._state,
        }

    def reset_state(self) -> None:
        """Reset state between tests."""
        self._connected = False
        self._measurements = []
        self._actions = []
        self._state = {}
```

## Complete Example

```python
"""Fake interface for a temperature sensor."""

import time
import random
from datetime import datetime, timezone
from typing import Optional

from my_sensor_types import (
    SensorInterfaceConfig,
    TemperatureReading,
    CalibrationData,
    SensorStatus,
)


class MySensorFakeInterface:
    """Simulated temperature sensor interface.

    This interface simulates a temperature sensor for testing.
    It maintains internal state, simulates realistic timing,
    and generates plausible temperature readings.

    Example:
        >>> interface = MySensorFakeInterface(base_temp=25.0)
        >>> interface.connect()
        >>> reading = interface.read_temperature()
        >>> print(f"Temperature: {reading.value}°C")
        >>> interface.disconnect()
    """

    def __init__(
        self,
        config: Optional[SensorInterfaceConfig] = None,
        latency: float = 0.1,
        base_temp: float = 22.0,
        noise_std: float = 0.2,
        failure_rate: float = 0.0,
    ):
        """Initialize fake interface.

        Args:
            config: Interface configuration.
            latency: Time multiplier for simulated operations.
            base_temp: Base temperature for readings.
            noise_std: Standard deviation of measurement noise.
            failure_rate: Probability of random failure (0.0 to 1.0).
        """
        self.config = config or SensorInterfaceConfig()
        self.latency = latency
        self.base_temp = base_temp
        self.noise_std = noise_std
        self.failure_rate = failure_rate

        # Internal state
        self._connected = False
        self._calibrated = False
        self._readings: list[TemperatureReading] = []
        self._calibration: Optional[CalibrationData] = None
        self._start_time: Optional[float] = None

    # =========================================================================
    # Lifecycle Methods
    # =========================================================================

    def connect(self) -> None:
        """Simulate connection to sensor.

        Raises:
            RuntimeError: If connection "fails" (random failure).
        """
        self._maybe_fail("Connection failed")
        time.sleep(0.5 * self.latency)
        self._connected = True
        self._start_time = time.time()

    def disconnect(self) -> None:
        """Simulate disconnection."""
        self._connected = False

    def is_connected(self) -> bool:
        """Check if connected."""
        return self._connected

    # =========================================================================
    # Measurement Methods
    # =========================================================================

    def read_temperature(self) -> TemperatureReading:
        """Read current temperature.

        Returns:
            TemperatureReading with simulated value.

        Raises:
            RuntimeError: If not connected.
        """
        self._check_connected()
        self._maybe_fail("Sensor read error")

        # Simulate read time
        time.sleep(0.1 * self.latency)

        # Generate realistic temperature
        value = self._generate_temperature()

        reading = TemperatureReading(
            value=round(value, 2),
            unit="celsius",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        self._readings.append(reading)
        return reading

    def get_status(self) -> SensorStatus:
        """Get sensor status.

        Returns:
            Current sensor status.
        """
        return SensorStatus(
            connected=self._connected,
            calibrated=self._calibrated,
            reading_count=len(self._readings),
            uptime_seconds=self._get_uptime(),
        )

    # =========================================================================
    # Calibration Methods
    # =========================================================================

    def calibrate(self, reference_temp: float = 20.0) -> CalibrationData:
        """Run calibration procedure.

        Args:
            reference_temp: Known reference temperature.

        Returns:
            Calibration results.
        """
        self._check_connected()

        # Simulate calibration time (longer operation)
        time.sleep(5.0 * self.latency)

        # Calculate simulated calibration offset
        measured = self._generate_temperature()
        offset = reference_temp - measured

        self._calibration = CalibrationData(
            offset=round(offset, 4),
            reference_temp=reference_temp,
            measured_temp=round(measured, 2),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self._calibrated = True

        return self._calibration

    # =========================================================================
    # Testing Helpers
    # =========================================================================

    def get_state(self) -> dict:
        """Get internal state for test assertions.

        Returns:
            Dictionary with all internal state.
        """
        return {
            "connected": self._connected,
            "calibrated": self._calibrated,
            "reading_count": len(self._readings),
            "readings": [r.model_dump() for r in self._readings],
            "calibration": self._calibration.model_dump() if self._calibration else None,
            "uptime_seconds": self._get_uptime(),
        }

    def reset_state(self) -> None:
        """Reset all state for test isolation."""
        self._connected = False
        self._calibrated = False
        self._readings = []
        self._calibration = None
        self._start_time = None

    def set_failure_rate(self, rate: float) -> None:
        """Set failure rate for chaos testing.

        Args:
            rate: Probability of failure (0.0 to 1.0).
        """
        self.failure_rate = max(0.0, min(1.0, rate))

    def inject_readings(self, readings: list[TemperatureReading]) -> None:
        """Inject predetermined readings for testing.

        Args:
            readings: Readings to return from read_temperature().
        """
        self._injected_readings = list(readings)

    # =========================================================================
    # Private Methods
    # =========================================================================

    def _check_connected(self) -> None:
        """Check if connected, raise if not."""
        if not self._connected:
            raise RuntimeError("Not connected to sensor")

    def _maybe_fail(self, message: str) -> None:
        """Randomly fail based on failure rate."""
        if random.random() < self.failure_rate:
            raise RuntimeError(f"Simulated failure: {message}")

    def _generate_temperature(self) -> float:
        """Generate a realistic temperature value."""
        # Check for injected readings
        if hasattr(self, '_injected_readings') and self._injected_readings:
            reading = self._injected_readings.pop(0)
            return reading.value

        # Base temperature with drift and noise
        uptime = self._get_uptime()
        drift = 0.1 * (uptime / 3600)  # 0.1°C/hour drift
        noise = random.gauss(0, self.noise_std)

        # Apply calibration offset if calibrated
        offset = self._calibration.offset if self._calibration else 0.0

        return self.base_temp + drift + noise + offset

    def _get_uptime(self) -> float:
        """Get simulated uptime in seconds."""
        if self._start_time is None:
            return 0.0
        return time.time() - self._start_time
```

## Testing with Fake Interfaces

### Basic Tests

```python
import pytest
from my_sensor_fake_interface import MySensorFakeInterface

def test_connect_disconnect():
    interface = MySensorFakeInterface()

    assert not interface.is_connected()
    interface.connect()
    assert interface.is_connected()
    interface.disconnect()
    assert not interface.is_connected()

def test_read_temperature():
    interface = MySensorFakeInterface(base_temp=25.0)
    interface.connect()

    reading = interface.read_temperature()

    assert reading.value is not None
    assert 24.0 < reading.value < 26.0  # Within noise range
    assert reading.unit == "celsius"

def test_state_tracking():
    interface = MySensorFakeInterface()
    interface.connect()
    interface.read_temperature()
    interface.read_temperature()

    state = interface.get_state()

    assert state["reading_count"] == 2
    assert state["connected"] is True
```

### Test Isolation

```python
@pytest.fixture
def interface():
    """Provide fresh interface for each test."""
    iface = MySensorFakeInterface(latency=0.01)  # Fast for tests
    yield iface
    iface.reset_state()

def test_one(interface):
    interface.connect()
    interface.read_temperature()
    assert interface.get_state()["reading_count"] == 1

def test_two(interface):
    # State is fresh, not affected by test_one
    assert interface.get_state()["reading_count"] == 0
```

### Chaos Testing

```python
def test_handles_failures_gracefully():
    interface = MySensorFakeInterface()
    interface.connect()
    interface.set_failure_rate(0.5)  # 50% failure rate

    successes = 0
    failures = 0

    for _ in range(100):
        try:
            interface.read_temperature()
            successes += 1
        except RuntimeError:
            failures += 1

    # Should see both successes and failures
    assert successes > 30
    assert failures > 30
```

### Predetermined Values

```python
def test_with_predetermined_values():
    interface = MySensorFakeInterface()
    interface.connect()

    # Inject specific values
    interface.inject_readings([
        TemperatureReading(value=20.0, unit="celsius", timestamp="..."),
        TemperatureReading(value=25.0, unit="celsius", timestamp="..."),
        TemperatureReading(value=30.0, unit="celsius", timestamp="..."),
    ])

    assert interface.read_temperature().value == 20.0
    assert interface.read_temperature().value == 25.0
    assert interface.read_temperature().value == 30.0
```

## Advanced Patterns

### State Machine Simulation

```python
from enum import Enum

class InstrumentState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    ERROR = "error"
    CALIBRATING = "calibrating"

class StatefulFakeInterface:
    def __init__(self):
        self._state = InstrumentState.IDLE

    def start(self):
        if self._state != InstrumentState.IDLE:
            raise RuntimeError(f"Cannot start from state {self._state}")
        self._state = InstrumentState.RUNNING

    def stop(self):
        if self._state != InstrumentState.RUNNING:
            raise RuntimeError(f"Cannot stop from state {self._state}")
        self._state = InstrumentState.IDLE

    def measure(self):
        if self._state != InstrumentState.RUNNING:
            raise RuntimeError("Must be running to measure")
        return {"value": 42}
```

### Data Recording for Playback

```python
class RecordingInterface:
    """Records real interface calls for playback in tests."""

    def __init__(self, real_interface):
        self._real = real_interface
        self._recordings = []

    def record_calls(self, method_name: str, *args, **kwargs):
        result = getattr(self._real, method_name)(*args, **kwargs)
        self._recordings.append({
            "method": method_name,
            "args": args,
            "kwargs": kwargs,
            "result": result,
        })
        return result

    def save_recordings(self, path: str):
        import json
        with open(path, "w") as f:
            json.dump(self._recordings, f)

class PlaybackInterface:
    """Replays recorded interface calls."""

    def __init__(self, recording_path: str):
        import json
        with open(recording_path) as f:
            self._recordings = json.load(f)
        self._index = 0

    def __getattr__(self, name):
        def playback(*args, **kwargs):
            if self._index >= len(self._recordings):
                raise RuntimeError("No more recorded calls")
            recording = self._recordings[self._index]
            self._index += 1
            return recording["result"]
        return playback
```

## Next Steps

- [Wiring the Node](05-wiring-the-node.md) - Connect interfaces to MADSci nodes
- [Testing Strategies](06-testing-strategies.md) - Comprehensive testing approaches
