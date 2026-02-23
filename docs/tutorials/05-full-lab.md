# Tutorial 5: Full Lab Setup

**Time to Complete**: ~60 minutes
**Prerequisites**: [Tutorial 4: Your First Workcell](04-first-workcell.md)
**Docker Required**: Yes

## What You'll Learn

In this tutorial, you'll:

1. Deploy a complete MADSci lab with all manager services
2. Configure the Lab Manager dashboard
3. Set up resource and location tracking
4. Configure data capture and storage
5. Enable observability with logging and monitoring
6. Run production-ready experiments

This is the full MADSci experience - a complete self-driving laboratory!

## Lab Architecture Overview

A full MADSci lab includes:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              MADSci Lab                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                         Infrastructure                               │   │
│   │   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐        │   │
│   │   │ MongoDB  │   │PostgreSQL│   │  Redis   │   │  MinIO   │        │   │
│   │   │  :27017  │   │  :5432   │   │  :6379   │   │  :9000   │        │   │
│   │   └──────────┘   └──────────┘   └──────────┘   └──────────┘        │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                          Managers                                    │   │
│   │   ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐       │   │
│   │   │  Lab   │  │ Event  │  │Experim.│  │Resource│  │  Data  │       │   │
│   │   │ :8000  │  │ :8001  │  │ :8002  │  │ :8003  │  │ :8004  │       │   │
│   │   └────────┘  └────────┘  └────────┘  └────────┘  └────────┘       │   │
│   │   ┌────────┐  ┌────────┐                                            │   │
│   │   │Workcell│  │Location│                                            │   │
│   │   │ :8005  │  │ :8006  │                                            │   │
│   │   └────────┘  └────────┘                                            │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                           Nodes                                      │   │
│   │   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐             │   │
│   │   │ Sensor  │   │  Robot  │   │ Reader  │   │ Handler │             │   │
│   │   │ :2000   │   │ :2001   │   │ :2002   │   │ :2003   │             │   │
│   │   └─────────┘   └─────────┘   └─────────┘   └─────────┘             │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Step 1: Create Lab Configuration

Create a new directory for your lab:

```bash
mkdir my_lab
cd my_lab

# Create lab configuration
madsci new lab --name my_lab --template standard
```

Or create the files manually:

### `.env` - Environment Configuration

```bash
# .env

# Lab identification
LAB_NAME=my_lab

# Database URLs
MONGO_DB_URL=mongodb://mongodb:27017
POSTGRES_URL=postgresql://postgres:postgres@postgres:5432/madsci
REDIS_URL=redis://redis:6379

# MinIO (S3-compatible storage)
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=madsci
MINIO_SECRET_KEY=madsci123

# Manager URLs (internal Docker network)
LAB_SERVER_URL=http://lab_manager:8000
EVENT_SERVER_URL=http://event_manager:8001
EXPERIMENT_SERVER_URL=http://experiment_manager:8002
RESOURCE_SERVER_URL=http://resource_manager:8003
DATA_SERVER_URL=http://data_manager:8004
WORKCELL_SERVER_URL=http://workcell_manager:8005
LOCATION_SERVER_URL=http://location_manager:8006
```

### `compose.yaml` - Docker Compose Configuration

```yaml
# compose.yaml
version: "3.8"

# Common service configuration
x-madsci-service: &madsci-service
  restart: unless-stopped
  networks:
    - madsci
  env_file:
    - .env

services:
  # ==========================================================================
  # Infrastructure
  # ==========================================================================

  mongodb:
    image: mongo:7
    <<: *madsci-service
    ports:
      - "27017:27017"
    volumes:
      - mongo_data:/data/db
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"]
      interval: 10s
      timeout: 5s
      retries: 5

  postgres:
    image: postgres:16-alpine
    <<: *madsci-service
    ports:
      - "5432:5432"
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: madsci
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    <<: *madsci-service
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  minio:
    image: minio/minio:latest
    <<: *madsci-service
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      MINIO_ROOT_USER: madsci
      MINIO_ROOT_PASSWORD: madsci123
    command: server /data --console-address ":9001"
    volumes:
      - minio_data:/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ==========================================================================
  # Managers
  # ==========================================================================

  lab_manager:
    image: ghcr.io/ad-sdl/madsci_squid:latest
    <<: *madsci-service
    ports:
      - "8000:8000"
    depends_on:
      mongodb:
        condition: service_healthy

  event_manager:
    image: ghcr.io/ad-sdl/madsci_event_manager:latest
    <<: *madsci-service
    ports:
      - "8001:8001"
    depends_on:
      mongodb:
        condition: service_healthy

  experiment_manager:
    image: ghcr.io/ad-sdl/madsci_experiment_manager:latest
    <<: *madsci-service
    ports:
      - "8002:8002"
    depends_on:
      mongodb:
        condition: service_healthy

  resource_manager:
    image: ghcr.io/ad-sdl/madsci_resource_manager:latest
    <<: *madsci-service
    ports:
      - "8003:8003"
    depends_on:
      postgres:
        condition: service_healthy

  data_manager:
    image: ghcr.io/ad-sdl/madsci_data_manager:latest
    <<: *madsci-service
    ports:
      - "8004:8004"
    environment:
      DATA_MINIO_ENDPOINT: ${MINIO_ENDPOINT}
      DATA_MINIO_ACCESS_KEY: ${MINIO_ACCESS_KEY}
      DATA_MINIO_SECRET_KEY: ${MINIO_SECRET_KEY}
    depends_on:
      mongodb:
        condition: service_healthy
      minio:
        condition: service_healthy

  workcell_manager:
    image: ghcr.io/ad-sdl/madsci_workcell_manager:latest
    <<: *madsci-service
    ports:
      - "8005:8005"
    depends_on:
      mongodb:
        condition: service_healthy
      redis:
        condition: service_healthy

  location_manager:
    image: ghcr.io/ad-sdl/madsci_location_manager:latest
    <<: *madsci-service
    ports:
      - "8006:8006"
    depends_on:
      mongodb:
        condition: service_healthy

  # ==========================================================================
  # Nodes (Example - customize for your lab)
  # ==========================================================================

  temp_sensor:
    image: ghcr.io/ad-sdl/madsci_node_module:latest
    <<: *madsci-service
    ports:
      - "2000:2000"
    volumes:
      - ./modules/temp_sensor:/app
    command: python /app/temp_sensor_rest_node.py

  robot_arm:
    image: ghcr.io/ad-sdl/madsci_node_module:latest
    <<: *madsci-service
    ports:
      - "2001:2001"
    volumes:
      - ./modules/robot_arm:/app
    command: python /app/robot_arm_rest_node.py --port 2001

networks:
  madsci:
    driver: bridge

volumes:
  mongo_data:
  postgres_data:
  minio_data:
```

## Step 2: Start the Lab

```bash
# Pull the latest images
docker compose pull

# Start all services
docker compose up -d

# Watch the logs
docker compose logs -f
```

Wait for all services to be healthy:

```bash
docker compose ps
```

All services should show "healthy" or "running".

## Step 3: Verify the Lab

```bash
# Check all services
madsci status
```

Output:
```
MADSci Service Status

  Service               URL                       Status    Version
  ─────────────────────────────────────────────────────────────────────
  Lab Manager           http://localhost:8000     ● Online  0.6.2
  Event Manager         http://localhost:8001     ● Online  0.6.2
  Experiment Manager    http://localhost:8002     ● Online  0.6.2
  Resource Manager      http://localhost:8003     ● Online  0.6.2
  Data Manager          http://localhost:8004     ● Online  0.6.2
  Workcell Manager      http://localhost:8005     ● Online  0.6.2
  Location Manager      http://localhost:8006     ● Online  0.6.2

  Nodes:
  temp_sensor           http://localhost:2000     ● Online
  robot_arm             http://localhost:2001     ● Online
```

## Step 4: Access the Dashboard

Open your browser to [http://localhost:8000](http://localhost:8000)

The Lab Manager dashboard provides:

- **Lab Overview**: All services and their status
- **Node Management**: View and control nodes
- **Workflow Monitor**: Track running workflows
- **Resource Browser**: View lab inventory
- **Event Log**: Real-time event stream

## Step 5: Configure Resources

Define the resources (labware, samples, etc.) in your lab:

```python
from madsci.client.resource_client import ResourceClient
from madsci.common.types.resource_types import ResourceTemplate, ResourceInstance

client = ResourceClient(base_url="http://localhost:8003")

# Create a resource template for sample tubes
template = ResourceTemplate(
    name="sample_tube",
    description="Standard 2mL sample tube",
    category="container",
    attributes={
        "volume_ml": 2.0,
        "material": "polypropylene",
    }
)
client.create_template(template)

# Create resource instances
for i in range(10):
    tube = ResourceInstance(
        template_id=template.template_id,
        name=f"tube_{i+1:03d}",
        barcode=f"TUBE{i+1:03d}",
    )
    client.create_resource(tube)

print("Created 10 sample tubes")
```

## Step 6: Configure Locations

Define physical locations in your lab:

```python
from madsci.client.location_client import LocationClient

client = LocationClient(base_url="http://localhost:8006")

# Create storage rack
rack = client.create_location(
    name="sample_rack_a",
    location_type="rack",
    capacity=24,  # 24 tube slots
    parent_location=None,
)

# Create individual slots
for row in "ABCD":
    for col in range(1, 7):
        slot = client.create_location(
            name=f"slot_{row}{col}",
            location_type="slot",
            parent_location=rack.location_id,
        )

print("Created rack with 24 slots")
```

## Step 7: Configure Data Capture

Set up data capture for experiments:

```python
from madsci.client.data_client import DataClient

client = DataClient(base_url="http://localhost:8004")

# Create a data collection for temperature readings
collection = client.create_collection(
    name="temperature_readings",
    description="Temperature sensor data",
    schema={
        "type": "object",
        "properties": {
            "value": {"type": "number"},
            "unit": {"type": "string"},
            "timestamp": {"type": "string", "format": "date-time"},
            "sensor_id": {"type": "string"},
        }
    }
)

print(f"Created data collection: {collection.collection_id}")
```

## Step 8: Run a Full Experiment

Now run an experiment that uses all the services:

```python
"""Complete lab experiment with resource tracking and data capture."""

from madsci.experiment_application import ExperimentScript, ExperimentDesign
from madsci.client import (
    WorkcellClient,
    ResourceClient,
    LocationClient,
    DataClient,
    EventClient,
)


class FullLabExperiment(ExperimentScript):
    """Experiment demonstrating full MADSci lab capabilities."""

    experiment_design = ExperimentDesign(
        name="Full Lab Demo",
        description="Demonstrates resource tracking, data capture, and workflow execution",
        version="1.0.0",
    )

    def __init__(self):
        super().__init__()
        self.workcell = WorkcellClient(base_url="http://localhost:8005")
        self.resources = ResourceClient(base_url="http://localhost:8003")
        self.locations = LocationClient(base_url="http://localhost:8006")
        self.data = DataClient(base_url="http://localhost:8004")
        self.events = EventClient(base_url="http://localhost:8001")

    def run(self) -> dict:
        """Execute the full experiment."""
        results = {
            "samples_processed": [],
            "readings": [],
        }

        # Log experiment start
        self.events.info(
            "Starting full lab experiment",
            experiment_name=self.experiment_design.name,
        )

        # Find available samples
        samples = self.resources.query_resources(
            template_name="sample_tube",
            status="available",
            limit=3,
        )

        self.events.info(f"Found {len(samples)} available samples")

        for sample in samples:
            # Mark sample as in-use
            self.resources.update_status(sample.resource_id, "in_use")

            # Get sample location
            location = self.locations.get_resource_location(sample.resource_id)
            self.events.info(
                f"Processing sample {sample.name} from {location.name}"
            )

            # Run workflow
            run = self.workcell.start_workflow(
                workflow_path="sample_collection.workflow.yaml",
                parameters={"sample_location": location.name},
            )

            result = self.workcell.wait_for_workflow(run.workflow_run_id)

            if result.status == "completed":
                # Capture data
                reading = {
                    "sample_id": sample.resource_id,
                    "temperature": result.outputs.get("temperature"),
                    "timestamp": result.completed_at,
                }
                self.data.store_data(
                    collection="temperature_readings",
                    data=reading,
                )
                results["readings"].append(reading)
                results["samples_processed"].append(sample.name)

                # Move sample to processed location
                self.locations.move_resource(
                    sample.resource_id,
                    destination="processed_rack",
                )
                self.resources.update_status(sample.resource_id, "processed")

            else:
                self.events.error(
                    f"Workflow failed for sample {sample.name}",
                    error=str(result.error),
                )

        # Log experiment complete
        self.events.info(
            "Experiment complete",
            samples_processed=len(results["samples_processed"]),
            readings_captured=len(results["readings"]),
        )

        return results


if __name__ == "__main__":
    experiment = FullLabExperiment()
    experiment.main()
```

## Step 9: Enable Observability (Optional)

Add full observability with OpenTelemetry:

### `compose.otel.yaml` - Observability Stack

```yaml
# compose.otel.yaml
version: "3.8"

services:
  # Distributed tracing
  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - "16686:16686"  # UI
      - "4317:4317"    # OTLP gRPC
      - "4318:4318"    # OTLP HTTP
    environment:
      COLLECTOR_OTLP_ENABLED: true
    networks:
      - madsci

  # Metrics
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./otel/prometheus.yaml:/etc/prometheus/prometheus.yml
    networks:
      - madsci

  # Log aggregation
  loki:
    image: grafana/loki:latest
    ports:
      - "3100:3100"
    volumes:
      - ./otel/loki.yaml:/etc/loki/local-config.yaml
    networks:
      - madsci

  # Dashboards
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: admin
    volumes:
      - ./otel/grafana/provisioning:/etc/grafana/provisioning
      - grafana_data:/var/lib/grafana
    networks:
      - madsci

volumes:
  grafana_data:

networks:
  madsci:
    external: true
```

Start with observability:

```bash
docker compose --profile otel up -d
```

Access the UIs:
- **Grafana**: http://localhost:3000 (admin/admin)
- **Jaeger**: http://localhost:16686
- **Prometheus**: http://localhost:9090

## Step 10: Backup and Maintenance

### Database Backups

```bash
# Backup MongoDB
madsci-backup create --db-url mongodb://localhost:27017 --output ./backups

# Backup PostgreSQL
madsci-backup create --db-url postgresql://postgres:postgres@localhost:5432/madsci --output ./backups
```

### Health Checks

```bash
# Run diagnostics
madsci doctor

# Check specific services
madsci status
```

### Log Viewing

```bash
# View all logs
madsci logs --follow

# Filter by service
madsci logs event_manager --tail 100

# Filter by level
madsci logs --level error --since 1h
```

## Lab Directory Structure

Your complete lab should look like:

```
my_lab/
├── .env                          # Environment configuration
├── compose.yaml                  # Docker Compose main file
├── compose.otel.yaml             # Observability stack (optional)
├── modules/                      # Node modules
│   ├── temp_sensor/
│   │   ├── temp_sensor_rest_node.py
│   │   ├── temp_sensor_interface.py
│   │   └── temp_sensor_fake_interface.py
│   └── robot_arm/
│       ├── robot_arm_rest_node.py
│       └── ...
├── workflows/                    # Workflow definitions
│   ├── sample_collection.workflow.yaml
│   └── ...
├── experiments/                  # Experiment scripts
│   ├── full_lab_experiment.py
│   └── ...
├── otel/                         # Observability configs
│   ├── prometheus.yaml
│   ├── loki.yaml
│   └── grafana/
└── backups/                      # Database backups
```

## Stopping and Cleaning Up

```bash
# Stop all services
docker compose down

# Stop and remove volumes (WARNING: deletes data!)
docker compose down -v

# Full cleanup including images
docker compose down -v --rmi all
```

## Key Takeaways

1. **Docker Compose orchestrates everything**: Infrastructure, managers, and nodes
2. **All managers work together**: Resources, locations, data, events, workflows
3. **Observability is built-in**: Logging, tracing, and metrics support
4. **Experiments leverage the full stack**: Track resources, capture data, log events
5. **Backup your data**: Regular backups are essential for production

## What's Next?

Congratulations! You've completed the MADSci tutorial series. You now know how to:

- ✅ Explore MADSci concepts and use the CLI/TUI
- ✅ Create node modules with interfaces
- ✅ Write experiments in different modalities
- ✅ Coordinate multiple nodes with workflows
- ✅ Deploy a complete lab with all services

### Further Learning

- **[Equipment Integrator Guide](../guides/integrator/01-understanding-modules.md)** - Deep dive into module development
- **[Lab Operator Guide](../guides/operator/01-daily-operations.md)** - Day-to-day lab management
- **[Experimentalist Guide](../guides/experimentalist/01-running-experiments.md)** - Advanced experiment techniques
- **[Observability Guide](../guides/observability.md)** - Full observability setup

### Join the Community

- [GitHub Discussions](https://github.com/AD-SDL/MADSci/discussions)
- [Issue Tracker](https://github.com/AD-SDL/MADSci/issues)
- [Documentation](https://ad-sdl.github.io/MADSci/)
