# Testing Strategies

**Audience**: Equipment Integrator
**Prerequisites**: [Wiring the Node](./05-wiring-the-node.md)
**Time**: ~30 minutes

## Overview

Testing laboratory instrument modules requires a layered approach. Most tests should run without hardware, giving you fast feedback during development. Hardware tests are reserved for validation and integration.

This guide covers:

1. The testing pyramid for instrument modules
2. Interface unit tests (using fake interfaces)
3. Node unit tests (testing action logic)
4. Integration tests (node + managers)
5. Hardware-in-the-loop tests

## The Testing Pyramid

```
         ┌──────────────┐
         │  Hardware     │  Few, slow, require physical access
         │  Tests        │
         ├──────────────┤
         │  Integration  │  Some, need Docker/services
         │  Tests        │
         ├──────────────┤
         │  Node Unit    │  Many, test action logic
         │  Tests        │
         ├──────────────┤
         │  Interface    │  Most tests here
         │  Unit Tests   │  Fast, no hardware
         └──────────────┘
```

**Goal**: 80%+ of your tests should use the fake interface and require no hardware or external services.

## 1. Interface Unit Tests

Interface tests validate your hardware communication logic using the fake interface. These are the foundation of your test suite.

### Basic Interface Tests

```python
# tests/test_interface.py
"""Tests for the sensor interface using the fake implementation."""

import pytest

from my_sensor_fake_interface import MySensorFakeInterface


@pytest.fixture
def interface():
    """Create a fresh fake interface for each test."""
    iface = MySensorFakeInterface()
    iface.connect()
    yield iface
    iface.disconnect()


class TestConnection:
    """Test connection lifecycle."""

    def test_connect(self, interface):
        assert interface.is_connected()

    def test_disconnect(self, interface):
        interface.disconnect()
        assert not interface.is_connected()

    def test_double_connect_is_safe(self, interface):
        interface.connect()  # Already connected
        assert interface.is_connected()

    def test_operations_require_connection(self):
        iface = MySensorFakeInterface()
        with pytest.raises(ConnectionError, match="Not connected"):
            iface.read_sensor()


class TestReadSensor:
    """Test sensor reading functionality."""

    def test_single_reading(self, interface):
        reading = interface.read_sensor()
        assert "temperature" in reading
        assert "humidity" in reading
        assert "timestamp" in reading

    def test_reading_types(self, interface):
        reading = interface.read_sensor()
        assert isinstance(reading["temperature"], float)
        assert isinstance(reading["humidity"], float)

    def test_reading_ranges(self, interface):
        reading = interface.read_sensor()
        assert -40 <= reading["temperature"] <= 85  # Sensor spec range
        assert 0 <= reading["humidity"] <= 100

    def test_multiple_samples_averaged(self, interface):
        reading = interface.read_sensor(samples=10)
        assert reading is not None
        # Averaged readings should be within normal range
        assert 15 <= reading["temperature"] <= 35

    def test_readings_vary(self, interface):
        """Verify the fake interface simulates realistic variation."""
        readings = [interface.read_sensor()["temperature"] for _ in range(10)]
        # Not all readings should be identical
        assert len(set(readings)) > 1


class TestCalibration:
    """Test calibration functionality."""

    def test_calibrate_success(self, interface):
        result = interface.calibrate(reference_temp=25.0)
        assert result["success"] is True

    def test_calibrate_updates_state(self, interface):
        interface.calibrate(reference_temp=25.0)
        state = interface.get_state()
        assert state["calibrated"] is True

    def test_readings_after_calibration(self, interface):
        interface.calibrate(reference_temp=25.0)
        reading = interface.read_sensor()
        # After calibration, readings should be closer to reference
        assert reading is not None


class TestState:
    """Test state management."""

    def test_initial_state(self, interface):
        state = interface.get_state()
        assert state["connected"] is True
        assert state["readings_count"] == 0

    def test_state_tracks_readings(self, interface):
        interface.read_sensor()
        interface.read_sensor()
        state = interface.get_state()
        assert state["readings_count"] == 2

    def test_reset_state(self, interface):
        interface.read_sensor()
        interface.reset_state()
        state = interface.get_state()
        assert state["readings_count"] == 0
```

### Testing Error Conditions

```python
class TestErrorHandling:
    """Test error handling with configurable failure rates."""

    def test_simulated_timeout(self, interface):
        interface.set_failure_mode("timeout", rate=1.0)
        with pytest.raises(TimeoutError):
            interface.read_sensor()

    def test_simulated_connection_loss(self, interface):
        interface.set_failure_mode("disconnect", rate=1.0)
        with pytest.raises(ConnectionError):
            interface.read_sensor()

    def test_intermittent_failures(self, interface):
        """Test that retry logic handles intermittent failures."""
        interface.set_failure_mode("timeout", rate=0.3)
        successes = 0
        failures = 0
        for _ in range(100):
            try:
                interface.read_sensor()
                successes += 1
            except TimeoutError:
                failures += 1

        # With 30% failure rate, we should see both
        assert successes > 50
        assert failures > 10

    def test_recovery_after_error(self, interface):
        interface.set_failure_mode("timeout", rate=1.0)
        with pytest.raises(TimeoutError):
            interface.read_sensor()

        interface.set_failure_mode("timeout", rate=0.0)
        reading = interface.read_sensor()
        assert reading is not None
```

## 2. Node Unit Tests

Node tests validate the action logic, parameter handling, and result formatting. They use the fake interface but test through the node's action methods.

```python
# tests/test_node.py
"""Tests for the sensor node actions."""

import pytest

from my_sensor_rest_node import MySensorNode
from my_sensor_types import MySensorNodeConfig


@pytest.fixture
def node():
    """Create a node with fake interface for testing."""
    config = MySensorNodeConfig(interface_type="fake")
    n = MySensorNode()
    n.config = config
    n.startup_handler()
    yield n
    n.shutdown_handler()


class TestMeasureAction:
    """Test the measure action."""

    def test_measure_succeeds(self, node):
        result = node.measure()
        assert result.action_response == "succeeded"

    def test_measure_returns_reading(self, node):
        result = node.measure()
        assert "temperature" in result.data
        assert "humidity" in result.data

    def test_measure_with_samples(self, node):
        result = node.measure(samples=5)
        assert result.action_response == "succeeded"

    def test_measure_invalid_samples(self, node):
        """Test behavior with edge case parameters."""
        result = node.measure(samples=0)
        # Should handle gracefully
        assert result.action_response in ("succeeded", "failed")


class TestCalibrateAction:
    """Test the calibrate action."""

    def test_calibrate_succeeds(self, node):
        result = node.calibrate(reference_temp=25.0)
        assert result.action_response == "succeeded"
        assert result.data["success"] is True

    def test_calibrate_result_format(self, node):
        result = node.calibrate(reference_temp=25.0)
        assert "offset" in result.data
        assert "message" in result.data


class TestNodeLifecycle:
    """Test node startup and shutdown."""

    def test_startup_creates_interface(self, node):
        assert hasattr(node, "interface")
        assert node.interface.is_connected()

    def test_shutdown_disconnects(self, node):
        node.shutdown_handler()
        assert not node.interface.is_connected()
        # Re-connect for fixture cleanup
        node.startup_handler()

    def test_state_handler(self, node):
        state = node.state_handler()
        assert isinstance(state, dict)
        assert "connected" in state

    def test_invalid_interface_type(self):
        config = MySensorNodeConfig(interface_type="nonexistent")
        n = MySensorNode()
        n.config = config
        with pytest.raises(ValueError, match="Unknown interface type"):
            n.startup_handler()
```

## 3. Integration Tests

Integration tests verify that the node works correctly as a REST server and can communicate with MADSci managers. For testing against real services, Docker is needed. However, MADSci also provides in-memory database handler drop-ins (`InMemoryDocumentStorageHandler`, `InMemoryRedisHandler`, `SQLiteHandler`) that allow integration testing of manager logic without Docker.

```python
# tests/test_integration.py
"""Integration tests for the sensor node.

These tests require running MADSci services.
Start them with: docker compose up -d
Or use madsci start --mode=local for in-memory backends.
"""

import pytest
import httpx

# Skip if services aren't running
pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def node_url():
    """URL of the running node server."""
    return "http://localhost:2000"


@pytest.fixture(scope="module")
def check_services(node_url):
    """Skip tests if the node isn't running."""
    try:
        response = httpx.get(f"{node_url}/health", timeout=5)
        if response.status_code != 200:
            pytest.skip("Node server not running")
    except httpx.ConnectError:
        pytest.skip("Node server not running")


class TestNodeAPI:
    """Test the node's REST API."""

    def test_health_endpoint(self, node_url, check_services):
        response = httpx.get(f"{node_url}/health")
        assert response.status_code == 200

    def test_info_endpoint(self, node_url, check_services):
        response = httpx.get(f"{node_url}/info")
        assert response.status_code == 200
        info = response.json()
        assert "module_name" in str(info) or "name" in info

    def test_state_endpoint(self, node_url, check_services):
        response = httpx.get(f"{node_url}/state")
        assert response.status_code == 200

    def test_measure_action(self, node_url, check_services):
        # Create action
        response = httpx.post(
            f"{node_url}/actions/measure",
            json={"samples": 3},
            timeout=30,
        )
        assert response.status_code == 200

    def test_action_lifecycle(self, node_url, check_services):
        """Test the full action lifecycle: create -> start -> poll -> result."""
        import time

        # Create and start action
        response = httpx.post(
            f"{node_url}/actions/measure",
            json={"samples": 1},
            timeout=30,
        )
        assert response.status_code == 200
        result = response.json()

        # The action should complete (fake interface is fast)
        assert result is not None
```

### Running Integration Tests

```bash
# Run only unit tests (default, no markers)
pytest tests/ -m "not integration"

# Run integration tests (requires services)
pytest tests/ -m integration

# Run all tests
pytest tests/
```

Configure markers in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
markers = [
    "integration: tests requiring running MADSci services",
    "hardware: tests requiring physical hardware",
]
```

## 4. Hardware-in-the-Loop Tests

Hardware tests validate against the actual instrument. They are slow, require physical access, and should be run manually or in a dedicated CI environment.

```python
# tests/test_hardware.py
"""Hardware-in-the-loop tests.

These tests require the physical sensor to be connected.
Run with: pytest tests/test_hardware.py -m hardware
"""

import pytest

from my_sensor_interface import MySensorInterface

pytestmark = pytest.mark.hardware


@pytest.fixture(scope="module")
def real_interface():
    """Create a real interface connected to hardware."""
    iface = MySensorInterface(port="/dev/ttyUSB0", baud_rate=9600)
    try:
        iface.connect()
    except Exception as e:
        pytest.skip(f"Hardware not available: {e}")
    yield iface
    iface.disconnect()


class TestRealHardware:
    """Tests that validate against real hardware."""

    def test_connection(self, real_interface):
        assert real_interface.is_connected()

    def test_read_sensor(self, real_interface):
        reading = real_interface.read_sensor()
        assert "temperature" in reading
        # Real readings should be room temperature-ish
        assert 10 <= reading["temperature"] <= 40

    def test_multiple_readings_consistent(self, real_interface):
        """Real readings should be consistent within a short period."""
        import time

        readings = []
        for _ in range(5):
            readings.append(real_interface.read_sensor()["temperature"])
            time.sleep(0.5)

        # Temperature shouldn't change more than 1 degree in 2.5 seconds
        assert max(readings) - min(readings) < 1.0

    def test_calibration(self, real_interface):
        result = real_interface.calibrate(reference_temp=25.0)
        assert result["success"] is True
```

### CI Configuration for Hardware Tests

```yaml
# .github/workflows/hardware-tests.yml
name: Hardware Tests
on:
  workflow_dispatch:  # Manual trigger only
    inputs:
      device_port:
        description: 'Serial port for the sensor'
        default: '/dev/ttyUSB0'

jobs:
  hardware-test:
    runs-on: [self-hosted, lab-runner]  # Requires lab-specific runner
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.10'
      - run: pip install -e ".[dev]"
      - run: pytest tests/test_hardware.py -m hardware
        env:
          SENSOR_PORT: ${{ inputs.device_port }}
```

## 5. Test Organization

Recommended test structure for a module:

```
my_sensor_module/
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Shared fixtures
│   ├── test_interface.py        # Interface unit tests (fake)
│   ├── test_node.py             # Node action tests (fake)
│   ├── test_types.py            # Data model validation
│   ├── test_integration.py      # REST API tests (services)
│   └── test_hardware.py         # Hardware-in-the-loop
├── pyproject.toml
└── ...
```

### Shared Fixtures (`conftest.py`)

```python
# tests/conftest.py
"""Shared test fixtures for the sensor module."""

import pytest

from my_sensor_fake_interface import MySensorFakeInterface
from my_sensor_rest_node import MySensorNode
from my_sensor_types import MySensorNodeConfig


@pytest.fixture
def fake_interface():
    """A connected fake interface."""
    iface = MySensorFakeInterface()
    iface.connect()
    yield iface
    iface.disconnect()


@pytest.fixture
def node():
    """A node configured with fake interface."""
    config = MySensorNodeConfig(interface_type="fake")
    n = MySensorNode()
    n.config = config
    n.startup_handler()
    yield n
    n.shutdown_handler()
```

## Running Tests

```bash
# Run all non-hardware tests
pytest tests/ -m "not hardware"

# Run with coverage
pytest tests/ --cov=src/ --cov-report=html -m "not hardware"

# Run specific test file
pytest tests/test_interface.py -v

# Run specific test class
pytest tests/test_interface.py::TestReadSensor -v

# Run with verbose output for debugging
pytest tests/test_interface.py -v -s
```

## What's Next?

- [Debugging](./07-debugging.md) - Common issues and troubleshooting techniques
- [Packaging & Deployment](./08-packaging-deployment.md) - Docker, dependencies, CI/CD
