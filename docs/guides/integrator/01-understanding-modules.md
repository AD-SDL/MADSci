# Understanding Modules

This guide explains the fundamental concepts of MADSci module development: the distinction between modules, nodes, and interfaces.

## The Module Hierarchy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              MODULE                                          │
│  (Complete package - often its own git repository)                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌───────────────────────────────────────────────────────────────────┐     │
│   │                          NODE                                      │     │
│   │   (Runtime REST server - what the workcell talks to)              │     │
│   │                                                                    │     │
│   │   ┌─────────────────────────────────────────────────────────────┐ │     │
│   │   │                     INTERFACE                                │ │     │
│   │   │   (Hardware communication - independent of MADSci)          │ │     │
│   │   │                                                              │ │     │
│   │   │   ┌─────────────────────────────────────────────────────┐   │ │     │
│   │   │   │                    DRIVER                            │   │ │     │
│   │   │   │   (Low-level protocol: serial, socket, SDK)         │   │ │     │
│   │   │   └─────────────────────────────────────────────────────┘   │ │     │
│   │   └─────────────────────────────────────────────────────────────┘ │     │
│   └───────────────────────────────────────────────────────────────────┘     │
│                                                                              │
│   + Types, Tests, Dockerfile, Documentation, Configuration                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Definitions

### Module

A **module** is a complete package containing everything needed to control a laboratory instrument. It typically lives in its own git repository and includes:

| Component | File(s) | Purpose |
|-----------|---------|--------|
| Node Server | `*_rest_node.py` | MADSci REST endpoint |
| Real Interface | `*_interface.py` | Hardware communication |
| Fake Interface | `*_fake_interface.py` | Testing without hardware |
| Type Definitions | `*_types.py` | Pydantic models, configs |
| Tests | `tests/` | Unit and integration tests |
| Dockerfile | `Dockerfile` | Container build |
| Package Config | `pyproject.toml` | Dependencies |
| Documentation | `README.md` | Usage instructions |

**Example**: `pf400_module`, `ot2_module`, `inheco_incubator_module`

### Node

A **node** is the runtime server that the workcell communicates with. It:

- Receives action requests via REST API
- Executes actions using the interface
- Reports status and results
- Manages lifecycle (startup, shutdown)

```python
class MyInstrumentNode(RestNode):
    """The MADSci node server."""

    @action
    def measure(self, sample_id: str) -> MeasurementResult:
        """Execute measurement action."""
        return self.interface.measure(sample_id)
```

### Interface

An **interface** is a class that handles all communication with the hardware. The key insight:

> **The interface is independent of MADSci!**

You can use an interface directly in:
- Jupyter notebooks
- Python scripts
- Test files
- Other applications

```python
# Using interface directly (no MADSci needed)
from my_instrument_interface import MyInstrumentInterface

interface = MyInstrumentInterface(port="/dev/ttyUSB0")
interface.connect()
result = interface.measure("sample_001")
interface.disconnect()
```

### Driver

A **driver** handles the low-level protocol communication:

- Serial port commands
- TCP/IP socket messages
- REST API calls to vendor systems
- Vendor SDK wrappers

The driver is often embedded in the interface or separated for complex instruments.

## Why This Separation?

### 1. Testability

```python
# Test interface without MADSci infrastructure
def test_interface_measure():
    interface = MyFakeInterface()
    interface.connect()
    result = interface.measure("sample_001")
    assert result.value > 0
```

### 2. Reusability

```python
# Use interface in Jupyter notebook
from my_instrument_interface import MyInstrumentInterface

interface = MyInstrumentInterface(port="/dev/ttyUSB0")
interface.connect()

# Interactive exploration
for i in range(10):
    result = interface.measure(f"sample_{i}")
    print(f"Sample {i}: {result.value}")
```

### 3. Debuggability

- Interface issues → Hardware/communication problem
- Node issues → MADSci configuration/wiring problem
- Clear separation makes debugging easier

### 4. Development Speed

- Develop interface first (fast iteration in notebooks)
- Test thoroughly with fake interface
- Then wire up to MADSci node

## Module Structure

```
my_instrument_module/
├── src/
│   ├── __init__.py
│   ├── my_instrument_rest_node.py      # MADSci node server
│   ├── my_instrument_interface.py       # Real hardware interface
│   ├── my_instrument_fake_interface.py  # Simulated interface
│   ├── my_instrument_types.py           # Types and configuration
│   └── my_instrument_driver.py          # Low-level communication (optional)
├── tests/
│   ├── __init__.py
│   ├── test_interface.py               # Interface tests
│   └── test_node.py                     # Node tests
├── Dockerfile
├── pyproject.toml
├── README.md
└── .env.example
```

## The Types Module Pattern

Centralize all type definitions in `*_types.py`:

```python
"""Type definitions for my_instrument module."""

from typing import Literal
from pydantic import BaseModel, Field
from madsci.common.types.node_types import RestNodeConfig


# Node configuration (how to start the node)
class MyInstrumentNodeConfig(RestNodeConfig):
    """Configuration for the node server."""
    interface_type: Literal["real", "fake"] = "fake"
    port: str = "/dev/ttyUSB0"
    timeout: float = 30.0


# Interface configuration (how to connect to hardware)
class MyInstrumentInterfaceConfig(BaseModel):
    """Configuration for the interface."""
    baud_rate: int = 9600
    retry_count: int = 3


# Data models (what the instrument produces)
class MeasurementResult(BaseModel):
    """Result from a measurement action."""
    value: float
    unit: str = "units"
    timestamp: str
    status: Literal["success", "error"] = "success"


# Command models (what you send to the instrument)
class MeasurementCommand(BaseModel):
    """Command to start a measurement."""
    sample_id: str
    duration: float = 1.0
```

## Real vs Fake Interfaces

Every module should have at least two interfaces:

### Real Interface

Communicates with actual hardware:

```python
class MyInstrumentInterface:
    """Real hardware communication."""

    def __init__(self, port: str = "/dev/ttyUSB0"):
        self.port = port
        self._connection = None

    def connect(self) -> None:
        self._connection = serial.Serial(self.port, 9600)

    def measure(self, sample_id: str) -> MeasurementResult:
        self._connection.write(f"MEASURE {sample_id}\n".encode())
        response = self._connection.readline().decode().strip()
        return MeasurementResult.model_validate_json(response)
```

### Fake Interface

Simulates hardware for testing:

```python
class MyInstrumentFakeInterface:
    """Simulated interface for testing."""

    def __init__(self, latency: float = 0.1):
        self.latency = latency
        self._connected = False
        self._measurements: list[MeasurementResult] = []

    def connect(self) -> None:
        time.sleep(self.latency)
        self._connected = True

    def measure(self, sample_id: str) -> MeasurementResult:
        time.sleep(self.latency)
        result = MeasurementResult(
            value=random.uniform(10.0, 20.0),
            timestamp=datetime.now().isoformat(),
        )
        self._measurements.append(result)
        return result

    # Testing helpers
    def get_measurement_count(self) -> int:
        return len(self._measurements)
```

## Choosing Interface Type at Runtime

The node selects which interface to use:

```python
class MyInstrumentNode(RestNode):
    config: MyInstrumentNodeConfig = MyInstrumentNodeConfig()

    def startup_handler(self) -> None:
        if self.config.interface_type == "real":
            from my_instrument_interface import MyInstrumentInterface
            self.interface = MyInstrumentInterface(self.config.port)
        else:
            from my_instrument_fake_interface import MyInstrumentFakeInterface
            self.interface = MyInstrumentFakeInterface()

        self.interface.connect()
```

## Next Steps

- [Creating a Module](02-creating-a-module.md) - Use `madsci new module` to scaffold a complete module
- [Developing Interfaces](03-developing-interfaces.md) - Deep dive into interface patterns
