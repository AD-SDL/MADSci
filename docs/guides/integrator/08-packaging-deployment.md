# Packaging and Deployment

**Audience**: Equipment Integrator
**Prerequisites**: [Testing Strategies](./06-testing-strategies.md)
**Time**: ~25 minutes

## Overview

Once your module is tested and working, you need to package it for deployment. This guide covers:

1. Python package configuration
2. Docker containerization
3. Docker Compose integration with a lab
4. CI/CD with GitHub Actions
5. Environment-based configuration

## 1. Python Package Configuration

Your module's `pyproject.toml` defines its dependencies and metadata:

```toml
[project]
name = "my_sensor_module"
version = "1.0.0"
description = "MADSci module for temperature/humidity sensor"
requires-python = ">=3.10"
dependencies = [
    "madsci_node_module>=0.6.0",
    "pyserial>=3.5",  # Hardware-specific dependency
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "ruff>=0.1.0",
    "httpx>=0.25.0",  # For integration tests
]

[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.backends._legacy:_Backend"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "integration: tests requiring running MADSci services",
    "hardware: tests requiring physical hardware",
]

[tool.ruff]
line-length = 120
target-version = "py310"
```

### Installing for Development

```bash
# Install in development mode
pip install -e ".[dev]"

# Or with PDM (if using the MADSci monorepo)
pdm install
```

## 2. Dockerfile

The generated Dockerfile from `madsci new module` provides a working starting point:

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (if needed for hardware libraries)
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Uncomment as needed:
    # libusb-1.0-0 \        # For USB devices
    # libserialport-dev \    # For serial devices
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy source code
COPY src/ src/

# Install the module
RUN pip install --no-cache-dir -e .

# Default environment variables
ENV MY_SENSOR_INTERFACE_TYPE=fake
ENV MY_SENSOR_NODE_PORT=2000

# Expose the node port
EXPOSE 2000

# Run the node
CMD ["python", "src/my_sensor_rest_node.py"]
```

### Building and Running

```bash
# Build the image
docker build -t my-sensor-module .

# Run with fake interface
docker run -p 2000:2000 my-sensor-module

# Run with real hardware (pass through USB device)
docker run -p 2000:2000 \
  --device=/dev/ttyUSB0 \
  -e MY_SENSOR_INTERFACE_TYPE=real \
  -e MY_SENSOR_SERIAL_PORT=/dev/ttyUSB0 \
  my-sensor-module
```

### Hardware Access in Docker

For modules that communicate with physical hardware, you need to pass devices through to the container:

```bash
# Serial devices
docker run --device=/dev/ttyUSB0 my-sensor-module

# USB devices (more permissive)
docker run --privileged my-sensor-module

# Network devices (host networking)
docker run --network=host my-sensor-module

# Multiple devices
docker run \
  --device=/dev/ttyUSB0 \
  --device=/dev/ttyUSB1 \
  my-sensor-module
```

## 3. Docker Compose Integration

To add your module to a MADSci lab, add it to the lab's `compose.yaml`:

```yaml
services:
  # ... existing services ...

  my_sensor:
    build:
      context: ./my_sensor_module
      dockerfile: Dockerfile
    ports:
      - "2000:2000"
    environment:
      - MY_SENSOR_INTERFACE_TYPE=fake
      - MY_SENSOR_NODE_PORT=2000
      - EVENT_SERVER_URL=http://event_manager:8001
      - DATA_SERVER_URL=http://data_manager:8004
    depends_on:
      - event_manager
    restart: unless-stopped
    # For real hardware:
    # devices:
    #   - /dev/ttyUSB0:/dev/ttyUSB0
```

### Using with the Example Lab

```bash
# Start the full lab (includes your module)
docker compose up -d

# Start only your module (for development)
docker compose up my_sensor

# Rebuild after code changes
docker compose build my_sensor
docker compose up -d my_sensor

# View logs
docker compose logs my_sensor -f
```

## 4. CI/CD with GitHub Actions

Set up automated testing for your module:

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install ruff
      - run: ruff check src/ tests/
      - run: ruff format --check src/ tests/

  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.10', '3.11', '3.12']
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: pip install -e ".[dev]"
      - run: pytest tests/ -m "not hardware and not integration" --cov=src/ --cov-report=xml
      - uses: codecov/codecov-action@v3
        if: matrix.python-version == '3.11'

  integration:
    runs-on: ubuntu-latest
    needs: test
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -e ".[dev]"
      # Start the node with fake interface
      - run: |
          MY_SENSOR_INTERFACE_TYPE=fake python src/my_sensor_rest_node.py &
          sleep 5
          curl --retry 10 --retry-delay 2 http://localhost:2000/health
      - run: pytest tests/ -m integration

  docker:
    runs-on: ubuntu-latest
    needs: test
    steps:
      - uses: actions/checkout@v4
      - run: docker build -t my-sensor-module .
      - run: |
          docker run -d -p 2000:2000 --name sensor my-sensor-module
          sleep 5
          curl --retry 10 --retry-delay 2 http://localhost:2000/health
          docker stop sensor
```

## 5. Environment-Based Configuration

MADSci modules use Pydantic Settings for configuration, which supports multiple sources with this precedence (highest to lowest):

1. **Environment variables** - `MY_SENSOR_SERIAL_PORT=/dev/ttyACM0`
2. **`.env` file** - Loaded automatically if present
3. **Config file** - TOML or YAML
4. **Defaults** - Defined in the Settings class

### `.env` File for Development

```bash
# .env
MY_SENSOR_INTERFACE_TYPE=fake
MY_SENSOR_NODE_PORT=2000
MY_SENSOR_DEFAULT_SAMPLES=10
EVENT_SERVER_URL=http://localhost:8001/
DATA_SERVER_URL=http://localhost:8004/
```

### `.env` File for Production

```bash
# .env.production
MY_SENSOR_INTERFACE_TYPE=real
MY_SENSOR_SERIAL_PORT=/dev/ttyUSB0
MY_SENSOR_BAUD_RATE=115200
MY_SENSOR_NODE_PORT=2000
EVENT_SERVER_URL=http://event_manager:8001/
DATA_SERVER_URL=http://data_manager:8004/
```

### Docker Compose with `.env`

```yaml
services:
  my_sensor:
    build: ./my_sensor_module
    env_file:
      - .env.production
    ports:
      - "2000:2000"
    devices:
      - /dev/ttyUSB0:/dev/ttyUSB0
```

## 6. Multi-Architecture Builds

For labs with mixed hardware (x86 workstations, ARM-based edge devices):

```bash
# Build for multiple architectures
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t my-sensor-module:latest \
  --push .
```

## Deployment Checklist

Before deploying a module to production:

- [ ] All unit tests pass (`pytest tests/ -m "not hardware"`)
- [ ] Code passes linting (`ruff check src/ tests/`)
- [ ] Docker image builds successfully
- [ ] Node starts and responds to health checks
- [ ] Actions work with fake interface in Docker
- [ ] Actions work with real hardware (manual verification)
- [ ] Environment variables documented in `.env.example`
- [ ] Docker Compose entry added to lab configuration
- [ ] Node registered in workcell configuration

## What's Next?

- [Publishing](./09-publishing.md) - Sharing modules with the community
- [Tutorial: Full Lab](../../tutorials/05-full-lab.md) - Deploy a complete lab
