# Developing Interfaces

This guide covers interface patterns for different types of laboratory instruments.

## Interface Design Principles

### 1. Independence from MADSci

Interfaces should work standalone:

```python
# This should work without MADSci installed
from my_instrument_interface import MyInstrumentInterface

interface = MyInstrumentInterface(port="/dev/ttyUSB0")
interface.connect()
result = interface.measure("sample_001")
print(f"Value: {result.value}")
interface.disconnect()
```

### 2. Clear Lifecycle

Every interface needs:

```python
class MyInterface:
    def connect(self) -> None:
        """Establish connection to hardware."""
        ...

    def disconnect(self) -> None:
        """Close connection cleanly."""
        ...

    def is_connected(self) -> bool:
        """Check connection status."""
        ...
```

### 3. Type Safety

Use Pydantic models for inputs and outputs:

```python
from pydantic import BaseModel

class MeasurementCommand(BaseModel):
    sample_id: str
    duration: float = 1.0

class MeasurementResult(BaseModel):
    value: float
    unit: str
    timestamp: str

def measure(self, command: MeasurementCommand) -> MeasurementResult:
    ...
```

### 4. Error Handling

Define clear exception types:

```python
class InstrumentError(Exception):
    """Base exception for instrument errors."""
    pass

class ConnectionError(InstrumentError):
    """Failed to connect to instrument."""
    pass

class CommunicationError(InstrumentError):
    """Communication with instrument failed."""
    pass

class HardwareError(InstrumentError):
    """Instrument reported a hardware error."""
    pass
```

## Communication Patterns

### Serial (RS-232/RS-485/USB-Serial)

Most common for laboratory instruments:

```python
import serial
from typing import Optional

class SerialInterface:
    """Interface using serial communication."""

    def __init__(
        self,
        port: str = "/dev/ttyUSB0",
        baudrate: int = 9600,
        timeout: float = 5.0,
    ):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self._connection: Optional[serial.Serial] = None

    def connect(self) -> None:
        """Open serial connection."""
        try:
            self._connection = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
            )
        except serial.SerialException as e:
            raise ConnectionError(f"Failed to open {self.port}: {e}")

    def disconnect(self) -> None:
        """Close serial connection."""
        if self._connection and self._connection.is_open:
            self._connection.close()
            self._connection = None

    def _send_command(self, command: str) -> str:
        """Send command and get response."""
        if not self._connection or not self._connection.is_open:
            raise CommunicationError("Not connected")

        # Clear any pending data
        self._connection.reset_input_buffer()

        # Send command with line ending
        self._connection.write(f"{command}\r\n".encode())

        # Read response
        response = self._connection.readline().decode().strip()

        if not response:
            raise CommunicationError(f"No response to command: {command}")

        return response

    def measure(self, sample_id: str) -> MeasurementResult:
        """Take a measurement."""
        response = self._send_command(f"MEASURE {sample_id}")
        # Parse response: "OK,123.45,units"
        parts = response.split(",")
        if parts[0] != "OK":
            raise HardwareError(f"Measurement failed: {response}")

        return MeasurementResult(
            value=float(parts[1]),
            unit=parts[2] if len(parts) > 2 else "units",
            timestamp=datetime.now().isoformat(),
        )
```

### TCP/IP Socket

For networked instruments:

```python
import socket
from typing import Optional

class SocketInterface:
    """Interface using TCP/IP socket."""

    def __init__(
        self,
        host: str = "192.168.1.100",
        port: int = 5000,
        timeout: float = 10.0,
    ):
        self.host = host
        self.port = port
        self.timeout = timeout
        self._socket: Optional[socket.socket] = None

    def connect(self) -> None:
        """Establish TCP connection."""
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.settimeout(self.timeout)
            self._socket.connect((self.host, self.port))
        except socket.error as e:
            raise ConnectionError(f"Failed to connect to {self.host}:{self.port}: {e}")

    def disconnect(self) -> None:
        """Close TCP connection."""
        if self._socket:
            try:
                self._socket.shutdown(socket.SHUT_RDWR)
            except:
                pass
            self._socket.close()
            self._socket = None

    def _send_command(self, command: str) -> str:
        """Send command and receive response."""
        if not self._socket:
            raise CommunicationError("Not connected")

        # Send command
        self._socket.sendall(f"{command}\n".encode())

        # Receive response (with simple framing)
        response = b""
        while True:
            chunk = self._socket.recv(1024)
            if not chunk:
                break
            response += chunk
            if b"\n" in chunk:
                break

        return response.decode().strip()
```

### HTTP/REST API

For instruments with built-in web servers:

```python
import httpx
from typing import Any

class HTTPInterface:
    """Interface using HTTP/REST API."""

    def __init__(
        self,
        base_url: str = "http://192.168.1.100:8080",
        timeout: float = 30.0,
        api_key: str | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.api_key = api_key
        self._client: httpx.Client | None = None

    def connect(self) -> None:
        """Initialize HTTP client."""
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout,
            headers=headers,
        )

        # Verify connection with health check
        try:
            response = self._client.get("/health")
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise ConnectionError(f"Failed to connect to {self.base_url}: {e}")

    def disconnect(self) -> None:
        """Close HTTP client."""
        if self._client:
            self._client.close()
            self._client = None

    def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> dict:
        """Make HTTP request."""
        if not self._client:
            raise CommunicationError("Not connected")

        try:
            response = self._client.request(method, endpoint, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HardwareError(f"Request failed: {e.response.text}")
        except httpx.HTTPError as e:
            raise CommunicationError(f"HTTP error: {e}")

    def measure(self, sample_id: str) -> MeasurementResult:
        """Take a measurement via API."""
        data = self._request(
            "POST",
            "/api/v1/measure",
            json={"sample_id": sample_id},
        )
        return MeasurementResult.model_validate(data)
```

### Vendor SDK Wrapper

For instruments with proprietary SDKs:

```python
import vendor_sdk  # Hypothetical vendor SDK

class SDKInterface:
    """Interface wrapping vendor SDK."""

    def __init__(self, device_id: str = "DEVICE001"):
        self.device_id = device_id
        self._device: vendor_sdk.Device | None = None

    def connect(self) -> None:
        """Initialize and connect via SDK."""
        try:
            vendor_sdk.initialize()
            devices = vendor_sdk.discover_devices()

            for dev in devices:
                if dev.id == self.device_id:
                    self._device = dev
                    self._device.connect()
                    return

            raise ConnectionError(f"Device {self.device_id} not found")
        except vendor_sdk.SDKError as e:
            raise ConnectionError(f"SDK error: {e}")

    def disconnect(self) -> None:
        """Disconnect and cleanup SDK."""
        if self._device:
            try:
                self._device.disconnect()
            except:
                pass
            self._device = None
        vendor_sdk.shutdown()

    def measure(self, sample_id: str) -> MeasurementResult:
        """Take measurement using SDK."""
        if not self._device:
            raise CommunicationError("Not connected")

        try:
            result = self._device.measure(sample_id=sample_id)
            return MeasurementResult(
                value=result.value,
                unit=result.unit,
                timestamp=result.timestamp.isoformat(),
            )
        except vendor_sdk.SDKError as e:
            raise HardwareError(f"Measurement failed: {e}")
```

## Advanced Patterns

### Connection Pooling

```python
from contextlib import contextmanager
from threading import Lock

class ConnectionPool:
    """Pool of connections for high-throughput operations."""

    def __init__(self, interface_class, max_connections: int = 5, **kwargs):
        self._interface_class = interface_class
        self._kwargs = kwargs
        self._max = max_connections
        self._pool: list = []
        self._lock = Lock()

    @contextmanager
    def get_connection(self):
        """Get a connection from the pool."""
        with self._lock:
            if self._pool:
                conn = self._pool.pop()
            else:
                conn = self._interface_class(**self._kwargs)
                conn.connect()

        try:
            yield conn
        finally:
            with self._lock:
                if len(self._pool) < self._max:
                    self._pool.append(conn)
                else:
                    conn.disconnect()
```

### Retry Logic

```python
import time
from functools import wraps

def with_retry(max_attempts: int = 3, delay: float = 1.0):
    """Decorator for retrying operations."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except CommunicationError as e:
                    last_error = e
                    if attempt < max_attempts - 1:
                        time.sleep(delay * (attempt + 1))
            raise last_error
        return wrapper
    return decorator

class RobustInterface(SerialInterface):
    @with_retry(max_attempts=3, delay=0.5)
    def measure(self, sample_id: str) -> MeasurementResult:
        return super().measure(sample_id)
```

### Async Support

```python
import asyncio
import aioserial

class AsyncSerialInterface:
    """Async interface for concurrent operations."""

    async def connect(self) -> None:
        self._connection = aioserial.AioSerial(
            port=self.port,
            baudrate=self.baudrate,
        )

    async def measure(self, sample_id: str) -> MeasurementResult:
        await self._connection.write_async(f"MEASURE {sample_id}\n".encode())
        response = await self._connection.readline_async()
        # Parse and return...
```

## Testing Your Interface

Always test interfaces independently of the node:

```python
# tests/test_interface.py
import pytest
from my_instrument_interface import MyInstrumentInterface
from my_instrument_fake_interface import MyInstrumentFakeInterface

class TestInterface:
    """Tests that apply to both real and fake interfaces."""

    @pytest.fixture
    def interface(self):
        # Use fake interface for automated tests
        return MyInstrumentFakeInterface()

    def test_connect_disconnect(self, interface):
        assert not interface.is_connected()
        interface.connect()
        assert interface.is_connected()
        interface.disconnect()
        assert not interface.is_connected()

    def test_measure(self, interface):
        interface.connect()
        result = interface.measure("sample_001")
        assert result.value is not None
        assert result.sample_id == "sample_001"

    def test_measure_without_connect(self, interface):
        with pytest.raises(RuntimeError, match="Not connected"):
            interface.measure("sample_001")
```

## Next Steps

- [Fake Interfaces](04-fake-interfaces.md) - Creating effective simulated interfaces
- [Testing Strategies](06-testing-strategies.md) - Comprehensive testing approaches
