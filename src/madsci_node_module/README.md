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
from madsci.node_module import RestNode, action
from madsci.common.types.node_types import RestNodeConfig
from typing import Any
from pathlib import Path
from pydantic import BaseModel, Field

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
from madsci.node_module import action
from pydantic import BaseModel
from pathlib import Path

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
from madsci.common.types.node_types import RestNodeConfig
from pydantic import Field

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
from madsci.node_module import RestNode
from typing import Any

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
from madsci.node_module import RestNode, action

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
from madsci.node_module import RestNode, action
from typing import Any
from pathlib import Path

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

#### Basic Dockerfile
```dockerfile
FROM ghcr.io/ad-sdl/madsci:latest

# Copy node implementation and configuration
COPY my_instrument_node.py /app/
COPY my_instrument.node.yaml /app/
COPY requirements.txt /app/

WORKDIR /app

# Install additional dependencies if needed
RUN pip install -r requirements.txt

# Create directory for data files
RUN mkdir -p /app/data

# Expose the node port
EXPOSE 2000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:2000/health || exit 1

# Run the node
CMD ["python", "my_instrument_node.py"]
```

#### Multi-stage Docker Build
```dockerfile
# Build stage
FROM python:3.9-slim as builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --user -r requirements.txt

# Runtime stage
FROM ghcr.io/ad-sdl/madsci:latest
COPY --from=builder /root/.local /root/.local
COPY my_instrument_node.py /app/
COPY my_instrument.node.yaml /app/

WORKDIR /app
EXPOSE 2000

ENV PATH=/root/.local/bin:$PATH
CMD ["python", "my_instrument_node.py"]
```

#### Docker Compose for Development
```yaml
version: '3.8'
services:
  my-instrument:
    build: .
    ports:
      - "2000:2000"
    environment:
      # Node configuration via environment variables
      - NODE_NAME=my_instrument_dev
      - DEVICE_PORT=/dev/ttyUSB0
      - LOG_LEVEL=DEBUG
      - NODE_URL=http://localhost:2000

      # MADSci service URLs (for local development)
      - EVENT_MANAGER_URL=http://localhost:8001
      - DATA_MANAGER_URL=http://localhost:8004
      - RESOURCE_MANAGER_URL=http://localhost:8003
    volumes:
      # Mount device (for hardware access)
      - /dev/ttyUSB0:/dev/ttyUSB0
      # Mount data directory
      - ./data:/app/data
      # Mount config for hot-reload during development
      - ./my_instrument.node.yaml:/app/my_instrument.node.yaml
    depends_on:
      - event-manager
      - data-manager
      - resource-manager
    restart: unless-stopped

  # MADSci core services for development
  event-manager:
    image: ghcr.io/ad-sdl/madsci:latest
    command: ["python", "-m", "madsci.event_manager"]
    ports:
      - "8001:8001"
    environment:
      - LOG_LEVEL=DEBUG

  data-manager:
    image: ghcr.io/ad-sdl/madsci:latest
    command: ["python", "-m", "madsci.data_manager"]
    ports:
      - "8004:8004"
    environment:
      - LOG_LEVEL=DEBUG

  resource-manager:
    image: ghcr.io/ad-sdl/madsci:latest
    command: ["python", "-m", "madsci.resource_manager"]
    ports:
      - "8003:8003"
    environment:
      - LOG_LEVEL=DEBUG
```

### Kubernetes Deployment

#### Basic Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-instrument-node
  labels:
    app: my-instrument-node
spec:
  replicas: 1
  selector:
    matchLabels:
      app: my-instrument-node
  template:
    metadata:
      labels:
        app: my-instrument-node
    spec:
      containers:
      - name: my-instrument-node
        image: my-registry/my-instrument-node:latest
        ports:
        - containerPort: 2000
        env:
        - name: NODE_NAME
          value: "my_instrument_prod"
        - name: LOG_LEVEL
          value: "INFO"
        - name: EVENT_MANAGER_URL
          value: "http://event-manager:8001"
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 2000
          initialDelaySeconds: 30
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 2000
          initialDelaySeconds: 5
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: my-instrument-node
spec:
  selector:
    app: my-instrument-node
  ports:
    - protocol: TCP
      port: 80
      targetPort: 2000
  type: ClusterIP
```

#### ConfigMap for Node Configuration
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: my-instrument-config
data:
  my_instrument.node.yaml: |
    node_name: my_instrument_prod
    node_id: 01JYKZDPANTNRYXF5TQKRJS0F2
    node_description: Production instrument for sample analysis
    node_type: device
    module_name: my_instrument
    module_version: 1.0.0
    actions:
      - name: measure_sample
        description: Measure a sample
        parameters:
          sample_id: str
          duration: int
        returns: dict
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-instrument-node
spec:
  template:
    spec:
      containers:
      - name: my-instrument-node
        image: my-registry/my-instrument-node:latest
        volumeMounts:
        - name: config-volume
          mountPath: /app/my_instrument.node.yaml
          subPath: my_instrument.node.yaml
      volumes:
      - name: config-volume
        configMap:
          name: my-instrument-config
```

### Environment Configuration

#### Environment Variables
All node configuration can be controlled via environment variables:

```bash
# Core node settings
export NODE_NAME="my_instrument_1"
export NODE_ID="01JYKZDPANTNRYXF5TQKRJS0F2"
export NODE_URL="http://localhost:2000"
export NODE_PORT="2000"

# Device-specific settings (custom configuration)
export DEVICE_PORT="/dev/ttyUSB0"
export DEVICE_TIMEOUT="30"
export DEVICE_BAUDRATE="9600"

# MADSci service endpoints
export EVENT_MANAGER_URL="http://localhost:8001"
export DATA_MANAGER_URL="http://localhost:8004"
export RESOURCE_MANAGER_URL="http://localhost:8003"
export LOCATION_MANAGER_URL="http://localhost:8006"

# Logging configuration
export LOG_LEVEL="INFO"
export LOG_FORMAT="json"

# Security settings (if applicable)
export API_KEY="your-api-key"
export TLS_CERT_PATH="/etc/ssl/certs/node.crt"
export TLS_KEY_PATH="/etc/ssl/private/node.key"

# Start the node
python my_instrument_node.py
```

#### Configuration Files
Create environment-specific configuration files:

```python
# config/development.py
from madsci.common.types.node_types import RestNodeConfig

class DevelopmentConfig(RestNodeConfig):
    device_port: str = "/dev/mock"
    log_level: str = "DEBUG"
    event_manager_url: str = "http://localhost:8001"
    enable_debug_endpoints: bool = True

# config/production.py
class ProductionConfig(RestNodeConfig):
    device_port: str = "/dev/ttyUSB0"
    log_level: str = "INFO"
    event_manager_url: str = "http://event-manager:8001"
    enable_debug_endpoints: bool = False
    tls_enabled: bool = True

# my_instrument_node.py
import os
from config.development import DevelopmentConfig
from config.production import ProductionConfig

# Select configuration based on environment
if os.getenv("ENVIRONMENT", "development") == "production":
    config_class = ProductionConfig
else:
    config_class = DevelopmentConfig

class MyInstrumentNode(RestNode):
    config_model = config_class
```

### Integration with Workcells

#### Static Configuration
```yaml
# workcell.yaml
nodes:
  my_instrument_1: "http://my-instrument:2000"
  backup_instrument: "http://backup-instrument:2000"

workflows:
  - name: sample_analysis
    steps:
      - node: my_instrument_1
        action: measure_sample
        parameters:
          sample_id: "${sample_id}"
          duration: 60
```

#### Dynamic Discovery
```python
# workcell_manager.py
from madsci.workcell_manager import WorkcellManager

class MyWorkcell(WorkcellManager):
    def discover_nodes(self):
        """Automatically discover available nodes."""
        nodes = {}

        # Check for nodes on network
        for ip in self.get_network_ips():
            try:
                client = RestNodeClient(f"http://{ip}:2000")
                definition = client.get_definition()
                nodes[definition.node_name] = f"http://{ip}:2000"
            except:
                continue

        return nodes
```

### Production Deployment Best Practices

#### Security
```python
# Secure node configuration
class SecureNodeConfig(RestNodeConfig):
    # Enable TLS
    tls_enabled: bool = True
    tls_cert_path: str = "/etc/ssl/certs/node.crt"
    tls_key_path: str = "/etc/ssl/private/node.key"

    # API authentication
    api_key_required: bool = True
    api_key_header: str = "X-API-Key"

    # Rate limiting
    rate_limit_enabled: bool = True
    rate_limit_requests_per_minute: int = 60

class SecureNode(RestNode):
    config_model = SecureNodeConfig

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.config.tls_enabled:
            # Configure TLS
            import ssl
            ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ssl_context.load_cert_chain(
                self.config.tls_cert_path,
                self.config.tls_key_path
            )

        if self.config.api_key_required:
            # Add API key middleware
            from fastapi import Depends, HTTPException, status

            def verify_api_key(api_key: str = Header(alias=self.config.api_key_header)):
                if api_key != os.getenv("API_KEY"):
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid API key"
                    )

            # Apply to all action endpoints
            for route in self.app.routes:
                if hasattr(route, 'dependencies'):
                    route.dependencies.append(Depends(verify_api_key))
```

#### Monitoring and Observability
```python
from madsci.node_module import RestNode
import time
from prometheus_client import Counter, Histogram, generate_latest

# Metrics collection
action_counter = Counter('node_actions_total', 'Total actions executed', ['action_name', 'status'])
action_duration = Histogram('node_action_duration_seconds', 'Action execution time', ['action_name'])

class MonitoredNode(RestNode):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Add metrics endpoint
        @self.app.get("/metrics")
        async def metrics():
            return generate_latest()

    def execute_action_with_monitoring(self, action_name: str, func, *args, **kwargs):
        """Wrap action execution with monitoring."""
        start_time = time.time()
        status = "success"

        try:
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            status = "error"
            raise
        finally:
            # Record metrics
            duration = time.time() - start_time
            action_counter.labels(action_name=action_name, status=status).inc()
            action_duration.labels(action_name=action_name).observe(duration)
```

### Testing Your Node

#### Manual Testing with REST Client

```python
from madsci.client.node.rest_node_client import RestNodeClient

client = RestNodeClient("http://localhost:2000")

# Check node status
status = client.get_status()
print(f"Node status: {status}")

# Execute actions
result = client.execute_action("measure_sample", {
    "sample_id": "sample_001",
    "duration": 120
})
print(f"Measurement result: {result}")

# Test file operations
with open("test_protocol.json", "w") as f:
    f.write('{"steps": ["prepare", "measure", "analyze"]}')

file_result = client.execute_action("run_protocol", {
    "protocol_file": "test_protocol.json"
})
print(f"Protocol result datapoint ID: {file_result}")
```

#### Unit Testing with pytest

Create a test file `test_my_instrument_node.py`:

```python
import pytest
from unittest.mock import Mock, patch
from pathlib import Path
from my_instrument_node import MyInstrumentNode, MyInstrumentConfig

@pytest.fixture
def node_config():
    """Create test configuration."""
    return MyInstrumentConfig(
        device_port="/dev/ttyUSB0",
        timeout=10
    )

@pytest.fixture
def mock_device():
    """Create mock device interface."""
    device = Mock()
    device.get_temperature.return_value = 25.0
    device.get_status.return_value = "ready"
    device.measure.return_value = Mock(temp=24.5, abs=0.85)
    return device

@pytest.fixture
def node(node_config, mock_device):
    """Create test node instance."""
    with patch('my_instrument_node.MyDeviceInterface', return_value=mock_device):
        node = MyInstrumentNode()
        node.config = node_config
        node.startup_handler()
        yield node

def test_startup_handler(node, mock_device):
    """Test node initialization."""
    assert hasattr(node, 'device')
    assert node.device is mock_device

def test_state_handler(node, mock_device):
    """Test state reporting."""
    node.state_handler()
    assert "temperature" in node.node_state
    assert "status" in node.node_state
    assert node.node_state["temperature"] == 25.0
    assert node.node_state["status"] == "ready"

def test_measure_sample_action(node, mock_device):
    """Test sample measurement action."""
    result = node.measure_sample("sample_001", 60)

    # Verify device was called correctly
    mock_device.measure.assert_called_once_with("sample_001", 60)

    # Verify return values
    assert "temperature" in result
    assert "absorbance" in result
    assert result["temperature"] == 24.5
    assert result["absorbance"] == 0.85

def test_run_protocol_action(node, mock_device, tmp_path):
    """Test protocol execution action."""
    # Create test protocol file
    protocol_file = tmp_path / "test_protocol.json"
    protocol_file.write_text('{"steps": ["prepare", "measure"]}')

    # Mock device protocol execution
    mock_device.load_protocol.return_value = None
    mock_device.run.return_value = {"result": "success"}

    # Mock datapoint creation
    with patch.object(node, 'create_and_upload_value_datapoint', return_value="01ABCD1234"):
        result = node.run_protocol(protocol_file)

        # Verify device calls
        mock_device.load_protocol.assert_called_once_with(protocol_file)
        mock_device.run.assert_called_once()

        # Verify datapoint creation
        node.create_and_upload_value_datapoint.assert_called_once_with(
            value={"result": "success"},
            label="protocol_results"
        )

        # Verify return value
        assert result == "01ABCD1234"

def test_shutdown_handler(node, mock_device):
    """Test cleanup on shutdown."""
    mock_device.disconnect = Mock()
    node.shutdown_handler()
    mock_device.disconnect.assert_called_once()

@pytest.mark.asyncio
async def test_rest_api_integration(node):
    """Test REST API endpoints."""
    from fastapi.testclient import TestClient

    # Create test client
    client = TestClient(node.app)

    # Test health endpoint
    response = client.get("/health")
    assert response.status_code == 200

    # Test node definition
    response = client.get("/definition")
    assert response.status_code == 200

    # Test action execution
    response = client.post("/actions/measure_sample", json={
        "sample_id": "test_sample",
        "duration": 30
    })
    assert response.status_code == 200
    assert "temperature" in response.json()
    assert "absorbance" in response.json()
```

#### Integration Testing with Docker

Create a `docker-compose.test.yml` for integration testing:

```yaml
version: '3.8'
services:
  my-instrument-node:
    build: .
    ports:
      - "2000:2000"
    environment:
      - DEVICE_PORT=/dev/mock
      - LOG_LEVEL=DEBUG
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:2000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  integration-test:
    image: python:3.9
    depends_on:
      - my-instrument-node
    volumes:
      - ./tests:/tests
    command: |
      bash -c "
        pip install pytest requests
        python -m pytest /tests/test_integration.py -v
      "
```

Run integration tests:

```bash
# Start services and run tests
docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit

# Run specific test
docker-compose -f docker-compose.test.yml run integration-test pytest /tests/test_integration.py::test_node_communication -v
```

#### Performance Testing

```python
import time
import concurrent.futures
from madsci.client.node.rest_node_client import RestNodeClient

def test_concurrent_actions():
    """Test node performance under concurrent load."""
    client = RestNodeClient("http://localhost:2000")

    def execute_action(sample_id):
        start_time = time.time()
        result = client.execute_action("measure_sample", {
            "sample_id": f"sample_{sample_id}",
            "duration": 5
        })
        end_time = time.time()
        return end_time - start_time, result

    # Execute 10 concurrent actions
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(execute_action, i) for i in range(10)]
        results = [future.result() for future in futures]

    # Analyze performance
    execution_times = [result[0] for result in results]
    avg_time = sum(execution_times) / len(execution_times)
    max_time = max(execution_times)

    print(f"Average execution time: {avg_time:.2f}s")
    print(f"Maximum execution time: {max_time:.2f}s")

    # Assert performance requirements
    assert avg_time < 2.0, f"Average execution time too high: {avg_time}s"
    assert max_time < 5.0, f"Maximum execution time too high: {max_time}s"
```

#### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_my_instrument_node.py -v

# Run with coverage
pytest tests/ --cov=my_instrument_node --cov-report=html

# Run integration tests only
pytest tests/ -m integration

# Run performance tests
pytest tests/ -m performance --timeout=60
```

## Advanced Features

### Error Handling

#### Basic Exception Handling

```python
from madsci.node_module import RestNode, action
from typing import Dict, Any
import logging

class MyNode(RestNode):
    @action
    def risky_action(self, param: str) -> Dict[str, float]:
        """Actions can raise exceptions for error handling."""
        try:
            result = self.device.risky_operation(param)
            return {"result": result}
        except DeviceError as e:
            # Log the error for debugging
            self.logger.error(f"Device error in risky_action: {e}")
            # Exceptions are automatically converted to HTTP error responses
            raise RuntimeError(f"Device operation failed: {e}")
        except ValueError as e:
            # Handle parameter validation errors
            raise ValueError(f"Invalid parameter '{param}': {e}")
        except Exception as e:
            # Catch-all for unexpected errors
            self.logger.error(f"Unexpected error in risky_action: {e}")
            raise RuntimeError("An unexpected error occurred during operation")
```

#### Custom Exception Classes

```python
from madsci.node_module import RestNode, action

class InstrumentError(Exception):
    """Base exception for instrument-related errors."""
    pass

class CalibrationError(InstrumentError):
    """Raised when calibration fails."""
    pass

class CommunicationError(InstrumentError):
    """Raised when device communication fails."""
    pass

class MyNode(RestNode):
    @action
    def calibrate_instrument(self) -> Dict[str, Any]:
        """Calibrate instrument with specific error handling."""
        try:
            # Attempt calibration
            if not self.device.is_connected():
                raise CommunicationError("Device not connected")

            calibration_result = self.device.calibrate()

            if not calibration_result.success:
                raise CalibrationError(f"Calibration failed: {calibration_result.error}")

            return {
                "status": "success",
                "calibration_value": calibration_result.value,
                "timestamp": calibration_result.timestamp
            }

        except CommunicationError as e:
            self.logger.error(f"Communication error during calibration: {e}")
            raise RuntimeError(f"Device communication error: {e}")
        except CalibrationError as e:
            self.logger.warning(f"Calibration failed: {e}")
            raise RuntimeError(f"Calibration error: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected calibration error: {e}")
            raise RuntimeError("Calibration failed due to unexpected error")
```

#### Validation and Input Checking

```python
from madsci.node_module import RestNode, action
from pydantic import validator, Field
from typing import Dict, Any

class MyNode(RestNode):
    @action
    def set_temperature(self, temperature: float, unit: str = "celsius") -> Dict[str, Any]:
        """Set instrument temperature with validation."""
        # Input validation
        if unit not in ["celsius", "fahrenheit", "kelvin"]:
            raise ValueError(f"Invalid temperature unit: {unit}. Must be celsius, fahrenheit, or kelvin")

        # Convert to celsius for internal use
        if unit == "fahrenheit":
            celsius_temp = (temperature - 32) * 5/9
        elif unit == "kelvin":
            celsius_temp = temperature - 273.15
        else:
            celsius_temp = temperature

        # Range validation
        if celsius_temp < -50 or celsius_temp > 200:
            raise ValueError(f"Temperature {celsius_temp}°C out of range (-50°C to 200°C)")

        try:
            # Attempt to set temperature
            self.device.set_temperature(celsius_temp)

            # Verify setting was applied
            actual_temp = self.device.get_temperature()
            if abs(actual_temp - celsius_temp) > 0.5:
                raise RuntimeError(f"Temperature setting failed. Set: {celsius_temp}°C, Got: {actual_temp}°C")

            return {
                "status": "success",
                "set_temperature": celsius_temp,
                "actual_temperature": actual_temp,
                "unit": "celsius"
            }

        except Exception as e:
            self.logger.error(f"Failed to set temperature: {e}")
            raise RuntimeError(f"Temperature setting failed: {e}")
```

#### Timeout and Retry Patterns

```python
import time
import asyncio
from functools import wraps
from madsci.node_module import RestNode, action

def with_timeout(timeout_seconds: int):
    """Decorator to add timeout to actions."""
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            start_time = time.time()
            try:
                result = func(self, *args, **kwargs)
                elapsed = time.time() - start_time
                if elapsed > timeout_seconds:
                    raise TimeoutError(f"Action '{func.__name__}' exceeded timeout of {timeout_seconds}s")
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                self.logger.error(f"Action '{func.__name__}' failed after {elapsed:.2f}s: {e}")
                raise
        return wrapper
    return decorator

def with_retry(max_attempts: int, delay_seconds: float = 1.0):
    """Decorator to add retry logic to actions."""
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(self, *args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        self.logger.warning(f"Action '{func.__name__}' attempt {attempt + 1} failed: {e}. Retrying in {delay_seconds}s...")
                        time.sleep(delay_seconds)
                    else:
                        self.logger.error(f"Action '{func.__name__}' failed after {max_attempts} attempts")
            raise last_exception
        return wrapper
    return decorator

class MyNode(RestNode):
    @action
    @with_timeout(30)
    @with_retry(3, delay_seconds=2.0)
    def measure_with_retry(self, sample_id: str) -> Dict[str, Any]:
        """Measure sample with timeout and retry logic."""
        try:
            # Simulate potentially failing measurement
            result = self.device.measure(sample_id)

            if result is None:
                raise RuntimeError("Measurement returned no data")

            return {
                "sample_id": sample_id,
                "measurement": result,
                "timestamp": time.time()
            }

        except Exception as e:
            # Log the specific attempt failure
            self.logger.debug(f"Measurement attempt failed for {sample_id}: {e}")
            raise  # Re-raise for retry logic
```

#### Error Response Customization

```python
from madsci.node_module import RestNode
from fastapi import HTTPException
from fastapi.responses import JSONResponse

class MyNode(RestNode):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Add custom exception handler
        @self.app.exception_handler(InstrumentError)
        async def instrument_error_handler(request, exc):
            return JSONResponse(
                status_code=500,
                content={
                    "error": "InstrumentError",
                    "message": str(exc),
                    "node_id": self.node_id,
                    "timestamp": time.time()
                }
            )

        @self.app.exception_handler(ValueError)
        async def validation_error_handler(request, exc):
            return JSONResponse(
                status_code=400,
                content={
                    "error": "ValidationError",
                    "message": str(exc),
                    "node_id": self.node_id
                }
            )
```

#### Health Check with Error Reporting

```python
from madsci.node_module import RestNode
from typing import Dict, Any

class MyNode(RestNode):
    def get_health_status(self) -> Dict[str, Any]:
        """Override health status to include error information."""
        base_health = super().get_health_status()

        # Add custom health checks
        errors = []
        warnings = []

        try:
            # Check device connection
            if not self.device.is_connected():
                errors.append("Device not connected")
        except Exception as e:
            errors.append(f"Device check failed: {e}")

        try:
            # Check temperature within range
            temp = self.device.get_temperature()
            if temp > 100:
                warnings.append(f"High temperature detected: {temp}°C")
        except Exception as e:
            warnings.append(f"Temperature check failed: {e}")

        # Add error information to health status
        base_health.update({
            "errors": errors,
            "warnings": warnings,
            "error_count": len(errors),
            "warning_count": len(warnings),
            "status": "error" if errors else "warning" if warnings else "healthy"
        })

        return base_health
```

### File Handling
```python
from madsci.node_module import action
from pathlib import Path

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
