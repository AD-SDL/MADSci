# MADSci Squid (Lab Manager)

Central lab configuration manager and web dashboard provider for MADSci-powered laboratories.

## Features

- **Lab Management**: Central configuration and coordination point for all lab services
- **Web Dashboard**: Vue-based interface for monitoring and controlling lab operations
- **Service Discovery**: Provides lab context and service URLs to other components
- **Static File Serving**: Hosts the dashboard UI and provides lab-wide file access
- **CORS Support**: Enables cross-origin requests from dashboard to services

## Installation

See the main [README](../../README.md#installation) for installation options. This package is available as:

- PyPI: `pip install madsci.squid`
- Docker: Use `ghcr.io/ad-sdl/madsci_dashboard` for complete setup with UI
- **Example configuration**: See [example_lab/managers/example_lab.manager.yaml](../../example_lab/managers/example_lab.manager.yaml)

## Usage

### Quick Start

Use the [example_lab](../../example_lab/) as a starting point:

```bash
# Start complete lab with dashboard
docker compose up  # From repo root
# Dashboard available at http://localhost:8000

# Or run standalone (without dashboard)
python -m madsci.squid.lab_server
```

### Lab Manager Setup

Create a lab definition file:

```yaml
# lab.yaml
name: My_Lab
description: My MADSci-powered laboratory
manager_type: lab_manager
manager_id: 01JVDFED2K18FVF0E7JM7SX09F  # Generate with ulid
```

Run the lab manager:

```bash
# With dashboard (requires built UI files)
python -m madsci.squid.lab_server --lab-dashboard-files-path ./ui/dist

# Without dashboard
python -m madsci.squid.lab_server --lab-dashboard-files-path None
```

### Integration with MADSci Ecosystem

The Lab Manager provides centralized coordination:

```python
# Lab Manager serves context to all services
# Available at http://localhost:8000/context

{
  "lab_server_url": "http://localhost:8000",
  "event_server_url": "http://localhost:8001",
  "experiment_server_url": "http://localhost:8002",
  "resource_server_url": "http://localhost:8003",
  "data_server_url": "http://localhost:8004",
  "workcell_server_url": "http://localhost:8005",
  "location_server_url": "http://localhost:8006"
}
```

## Dashboard Features

The web dashboard provides real-time lab monitoring and control:

### Core Panels
- **Workcells**: Monitor workcell status, view running workflows, submit new workflows
- **Workflows**: Browse workflow history, view execution details, manage workflow lifecycle
- **Resources**: Explore resource inventory, view container hierarchies, track consumables
- **Experiments**: Monitor experimental campaigns, view experiment runs and status

### Administrative Controls
- **Node Management**: View node status, send admin commands (pause, resume, safety stop)
- **Workcell Controls**: Pause/resume workcells, view current operations
- **Resource Operations**: Add new resources, update quantities, manage containers
- **Real-time Updates**: Live status updates across all lab components

### Development

For dashboard development, see [ui/README.md](../../ui/README.md).

## Configuration

### Lab Definition
```yaml
name: Production_Lab
description: Production MADSci Laboratory
manager_type: lab_manager
manager_id: 01JVDFED2K18FVF0E7JM7SX09F
```

### Environment Variables

**Lab Manager Settings** (LAB_ prefix):
```bash
# Core Lab Manager Configuration
LAB_SERVER_URL=http://localhost:8000              # Lab manager server URL
LAB_DASHBOARD_FILES_PATH=./ui/dist                # Path to dashboard static files (set to None to disable)
LAB_MANAGER_DEFINITION=lab.manager.yaml           # Path to lab definition file

# Additional settings inherited from ManagerSettings:
LAB_VERBOSE=false                                 # Enable verbose logging
LAB_LOG_LEVEL=INFO                               # Logging level
LAB_CORS_ALLOWED_ORIGINS=["*"]                   # CORS origins for dashboard
```

**Service URLs** (for context endpoint - other manager settings):
```bash
# Manager Service URLs (used by /context endpoint)
EVENT_SERVER_URL=http://localhost:8001          # Event manager
EXPERIMENT_SERVER_URL=http://localhost:8002     # Experiment manager
RESOURCE_SERVER_URL=http://localhost:8003       # Resource manager
DATA_SERVER_URL=http://localhost:8004           # Data manager
WORKCELL_SERVER_URL=http://localhost:8005       # Workcell manager
LOCATION_SERVER_URL=http://localhost:8006       # Location manager
```

**Configuration Files** (alternative to environment variables):
- `.env` or `lab.env` - Environment variable file
- `settings.toml` or `lab.settings.toml` - TOML configuration
- `settings.yaml` or `lab.settings.yaml` - YAML configuration
- `settings.json` or `lab.settings.json` - JSON configuration

## API Endpoints

The Lab Manager provides REST endpoints for lab coordination:

### Core Endpoints

**`GET /context`** - Lab-wide service URLs and configuration
```json
{
  "lab_server_url": "http://localhost:8000",
  "event_server_url": "http://localhost:8001",
  "experiment_server_url": "http://localhost:8002",
  "resource_server_url": "http://localhost:8003",
  "data_server_url": "http://localhost:8004",
  "workcell_server_url": "http://localhost:8005",
  "location_server_url": "http://localhost:8006"
}
```

**`GET /health`** - Service health check
```json
{
  "healthy": true,
  "description": "Lab Manager is running"
}
```

**`GET /lab_health`** - Comprehensive lab health status
```json
{
  "healthy": true,
  "description": "5/6 managers are healthy",
  "managers": {
    "event_manager": {"healthy": true, "description": "Event Manager is running"},
    "experiment_manager": {"healthy": true, "description": "Experiment Manager is running"},
    "resource_manager": {"healthy": false, "description": "Failed to connect: Connection refused"},
    "data_manager": {"healthy": true, "description": "Data Manager is running"},
    "workcell_manager": {"healthy": true, "description": "Workcell Manager is running"},
    "location_manager": {"healthy": true, "description": "Location Manager is running"}
  },
  "total_managers": 6,
  "healthy_managers": 5
}
```

**`GET /definition`** - Lab definition and metadata
```json
{
  "name": "Example_Lab_Manager",
  "description": "A simple example of a lab manager definition",
  "manager_id": "01JVDFED2K18FVF0E7JM7SX09F",
  "manager_type": "lab_manager"
}
```

### Static File Serving
- Dashboard files served at root `/` when `LAB_DASHBOARD_FILES_PATH` is configured
- HTML fallback routing for SPA navigation
- API routes take precedence over static files

### Health Check Details
- **Lab Health Algorithm**: Lab considered healthy if >50% of configured managers are healthy
- **Timeout**: 5-second timeout for health check requests to managers
- **Error Handling**: Failed managers marked with specific error descriptions

**Full API documentation**: Available at `http://localhost:8000/docs` when running

**Examples**: See [example_lab/](../../example_lab/) for complete lab setup with dashboard integration.
