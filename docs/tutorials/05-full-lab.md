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
│   │   │ FerretDB │   │PostgreSQL│   │  Valkey  │   │SeaweedFS │        │   │
│   │   │  :27017  │   │  :5432   │   │  :6379   │   │  :8333   │        │   │
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
DOCUMENT_DB_URL=mongodb://madsci_ferretdb:27017
POSTGRES_URL=postgresql://postgres:postgres@postgres:5432/madsci
REDIS_URL=redis://madsci_valkey:6379

# SeaweedFS (S3-compatible object storage)
SEAWEEDFS_ENDPOINT=madsci_seaweedfs:8333
SEAWEEDFS_ACCESS_KEY=madsci
SEAWEEDFS_SECRET_KEY=madsci123

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

  madsci_ferretdb:
    image: ghcr.io/ferretdb/ferretdb:2
    <<: *madsci-service
    ports:
      - "27017:27017"
    environment:
      - FERRETDB_POSTGRESQL_URL=postgres://postgres:postgres@postgres:5432/madsci
    depends_on:
      postgres:
        condition: service_healthy

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

  madsci_valkey:
    image: valkey/valkey:8-alpine
    <<: *madsci-service
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "valkey-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  madsci_seaweedfs:
    image: chrislusf/seaweedfs:4.17
    <<: *madsci-service
    ports:
      - "8333:8333"
      - "9333:9333"
    command: server -s3
    volumes:
      - seaweedfs_data:/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8333/status"]
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
      madsci_ferretdb:
        condition: service_healthy

  event_manager:
    image: ghcr.io/ad-sdl/madsci_event_manager:latest
    <<: *madsci-service
    ports:
      - "8001:8001"
    depends_on:
      madsci_ferretdb:
        condition: service_healthy

  experiment_manager:
    image: ghcr.io/ad-sdl/madsci_experiment_manager:latest
    <<: *madsci-service
    ports:
      - "8002:8002"
    depends_on:
      madsci_ferretdb:
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
      DATA_OBJECT_STORAGE_ENDPOINT: ${SEAWEEDFS_ENDPOINT}
      DATA_OBJECT_STORAGE_ACCESS_KEY: ${SEAWEEDFS_ACCESS_KEY}
      DATA_OBJECT_STORAGE_SECRET_KEY: ${SEAWEEDFS_SECRET_KEY}
    depends_on:
      madsci_ferretdb:
        condition: service_healthy
      madsci_seaweedfs:
        condition: service_healthy

  workcell_manager:
    image: ghcr.io/ad-sdl/madsci_workcell_manager:latest
    <<: *madsci-service
    ports:
      - "8005:8005"
    depends_on:
      madsci_ferretdb:
        condition: service_healthy
      madsci_valkey:
        condition: service_healthy

  location_manager:
    image: ghcr.io/ad-sdl/madsci_location_manager:latest
    <<: *madsci-service
    ports:
      - "8006:8006"
    depends_on:
      madsci_ferretdb:
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
  ferretdb_data:
  postgres_data:
  seaweedfs_data:
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

Define resource templates and create instances of them. The Resource Manager models labware, consumables, and assets as Pydantic resource types (Asset, Container, Stack, Slot, Pool, etc.) and persists them to PostgreSQL.

```python
from madsci.client.resource_client import ResourceClient
from madsci.common.types.resource_types import Container

client = ResourceClient("http://localhost:8003")

# Register a reusable template for sample tubes
client.init_template(
    resource=Container(
        resource_name="sample_tube_template",
        resource_class="sample_tube",
        resource_description="Standard 2mL sample tube",
        capacity=1,
        attributes={"volume_ml": 2.0, "material": "polypropylene"},
    ),
    template_name="sample_tube",
    description="Standard 2mL sample tube",
    required_overrides=["resource_name"],
    tags=["consumable", "tube"],
)

# Instantiate 10 tubes from the template
for i in range(10):
    tube = client.create_resource_from_template(
        template_name="sample_tube",
        resource_name=f"tube_{i + 1:03d}",
    )
    print(f"Created {tube.resource_name} ({tube.resource_id})")
```

`init_template()` is idempotent: calling it again with the same template name updates the existing template instead of erroring.

## Step 6: Configure Locations

Locations are best declared once in `locations.yaml` (a `LabLocationConfig` document the Location Manager reconciles on each cycle), or as `intrinsic_locations` on a node class. The example below creates a lab-managed location at runtime via a registered location template — useful for ad-hoc additions like a temporary storage rack:

```python
from madsci.client.location_client import LocationClient

client = LocationClient("http://localhost:8006")

# Look up an existing location by name (e.g., one declared in locations.yaml
# or auto-registered by a node's intrinsic_locations).
deck = client.get_location_by_name("liquidhandler_1.deck_1")
print(f"{deck.location_name} -> resource {deck.resource_id}")

# Create a lab-managed location from a previously registered template
rack = client.create_location_from_template(
    location_name="overflow_rack",
    template_name="storage_rack_nest",
    node_bindings={"transfer_arm": "robotarm_1"},
    representation_overrides={"transfer_arm": {"position": [40, 25, 10]}},
    description="Temporary overflow rack for sample tubes",
)
print(f"Created {rack.location_name}")

# List every lab-managed location
for loc in client.get_locations(managed_by="lab"):
    print(f"  {loc.location_name} (managed_by={loc.managed_by})")
```

For the canonical declarative approach, see [Layered Location Ownership](../guides/integrator/10-location-templates.md) and the example lab's `locations.yaml`.

## Step 7: Configure Data Capture

The Data Manager stores datapoints — JSON values or files — and tags them with workflow/experiment ownership. Nodes typically submit datapoints automatically by returning them from action results, but you can also submit directly:

```python
from madsci.client.data_client import DataClient
from madsci.common.types.datapoint_types import ValueDataPoint

client = DataClient("http://localhost:8004")

# Submit a JSON datapoint (e.g., a temperature reading)
reading = client.submit_datapoint(
    ValueDataPoint(
        label="temperature_reading",
        value={"celsius": 23.7, "sensor_id": "temp_sensor_1"},
    )
)
print(f"Stored datapoint {reading.datapoint_id}")

# Query datapoints — the selector is a MongoDB-style filter on stored fields
matches = client.query_datapoints({"label": "temperature_reading"})
for dp_id, dp in matches.items():
    print(f"  {dp_id}: {dp.value}")
```

To submit a file instead, use `FileDataPoint` (`from madsci.common.types.datapoint_types`) with a `path` pointing at a local file — the client uploads the file to object storage and stores the resulting URL alongside the datapoint metadata.

## Step 8: Run a Full Experiment

Now run an experiment that uses all the services. `ExperimentScript` provides every manager client as an attribute — `self.workcell_client`, `self.resource_client`, `self.location_client`, `self.data_client`, plus `self.logger` (an `EventClient`) — so you don't construct them yourself.

```python
"""Complete lab experiment with resource tracking and data capture."""

from madsci.common.types.experiment_types import ExperimentDesign
from madsci.common.types.resource_types import Asset
from madsci.experiment_application import ExperimentScript


class FullLabExperiment(ExperimentScript):
    """Experiment demonstrating full MADSci lab capabilities."""

    experiment_design = ExperimentDesign(
        experiment_name="Full Lab Demo",
        experiment_description="Resource tracking, data capture, and workflow execution",
    )

    def run_experiment(self, samples: int = 3) -> dict:
        """Process `samples` plates through the example workflow."""
        self.logger.info(
            "Starting full lab experiment", samples_planned=samples
        )

        readings: list[dict] = []
        for i in range(samples):
            # 1. Stage a fresh plate on liquidhandler_1.deck_1
            plate = self.resource_client.add_resource(
                Asset(resource_name=f"sample_plate_{i + 1}")
            )
            deck = self.location_client.get_location_by_name(
                "liquidhandler_1.deck_1"
            )
            # Clear any plate already on the deck before staging the new one.
            deck_resource = self.resource_client.get_resource(deck.resource_id)
            if deck_resource.quantity > 0:
                self.resource_client.pop(deck.resource_id)
            self.resource_client.push(deck.resource_id, plate.resource_id)

            # 2. Run the workflow defined elsewhere (YAML or WorkflowDefinition)
            workflow = self.workcell_client.start_workflow(
                workflow_definition="sample_collection.workflow.yaml",
                json_inputs={"sample_location": "liquidhandler_1.deck_1"},
                prompt_on_error=False,
            )
            self.logger.info(
                "Workflow finished",
                workflow_id=workflow.workflow_id,
                status=workflow.status.value,
            )

            # 3. Pull the temperature datapoint produced by the `measure` step.
            #    The `measure` key is set on the measure_temperature step in the
            #    workflow YAML from tutorial 04.
            try:
                datapoint = workflow.get_datapoint(step_key="measure")
            except KeyError:
                datapoint = None
            if datapoint is not None:
                readings.append(
                    {"sample": plate.resource_name, "value": datapoint.value}
                )

        self.logger.info("Experiment complete", readings_captured=len(readings))
        return {"readings": readings}


if __name__ == "__main__":
    FullLabExperiment.main(lab_server_url="http://localhost:8000")
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
# Backup document database
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
