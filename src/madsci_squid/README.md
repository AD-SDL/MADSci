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
- **Example configuration**: See [example_lab/example_lab.lab.yaml](../../example_lab/example_lab.lab.yaml)

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
manager_id: 01JYKZDPANTNRYXF5TQKRJS0F2  # Generate with ulid
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
  "workcell_server_url": "http://localhost:8005"
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
manager_id: 01JYKZDPANTNRYXF5TQKRJS0F2
```

### Environment Variables
```bash
# Lab Manager settings
LAB_SERVER_URL=http://localhost:8000
LAB_DASHBOARD_FILES_PATH=./ui/dist
LAB_DEFINITION=lab.yaml

# Service URLs (for context endpoint)
EVENT_SERVER_URL=http://localhost:8001
WORKCELL_SERVER_URL=http://localhost:8005
# ... etc for other services
```

## API Endpoints

The Lab Manager provides REST endpoints for lab coordination:

- `GET /context`: Lab-wide service URLs and configuration
- `GET /health`: Service health check
- `GET /lab_health`: Collected health information for the lab
- `GET /definition`: Lab definition and metadata
- Dashboard files served at root when configured

**Full API documentation**: Available at `http://localhost:8000/docs` when running

**Examples**: See [example_lab/](../../example_lab/) for complete lab setup with dashboard integration.
