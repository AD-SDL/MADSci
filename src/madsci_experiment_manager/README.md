# MADSci Experiment Manager

Manages experimental runs across a MADSci-powered lab, providing experiment design, tracking, and lifecycle management.

## Features

- **Experiment Designs**: Define experimental parameters, conditions, and metadata
- **Experiment Runs**: Track individual experiment executions with status and results
- **Lifecycle Management**: Monitor experiment progress from design to completion
- **Status Management**: Support for pausing, resuming, cancelling, and failing experiments
- **Integration**: Works with all MADSci managers for comprehensive lab coordination

## Installation

See the main [README](../../README.md#installation) for installation options. This package is available as:

- PyPI: `pip install madsci.experiment_manager`
- Docker: Included in `ghcr.io/ad-sdl/madsci`
- **Example configuration**: See [example_lab/managers/example_experiment.manager.yaml](../../example_lab/managers/example_experiment.manager.yaml)

**Dependencies**: MongoDB database (see [example_lab](../../example_lab/))

## Usage

### Quick Start

Use the [example_lab](../../example_lab/) as a starting point:

```bash
# Start with working example
docker compose up  # From repo root
# Experiment Manager available at http://localhost:8002/docs

# Or run standalone
python src/madsci_experiment_manager/madsci/experiment_manager/experiment_server.py
```

### Manager Setup

For custom deployments, see [example_experiment.manager.yaml](../../example_lab/managers/example_experiment.manager.yaml) for configuration options.

### Environment Variables

The Experiment Manager supports configuration via environment variables with the `EXPERIMENT_` prefix:

- `EXPERIMENT_SERVER_URL`: Experiment Manager server URL (default: `http://localhost:8002`)
- `EXPERIMENT_MANAGER_DEFINITION`: Path to manager definition file (default: `experiment.manager.yaml`)
- `EXPERIMENT_DB_URL`: Database connection URL (default: `mongodb://localhost:27017`)

**Example:**
```bash
export EXPERIMENT_SERVER_URL=http://localhost:8002
export EXPERIMENT_DB_URL=mongodb://localhost:27017
export EXPERIMENT_MANAGER_DEFINITION=my_experiment.manager.yaml
```

Configuration files are also supported: `.env`, `experiments.env`, `settings.toml`, `experiments.settings.toml`, etc.

### Experiment Client

Use `ExperimentClient` to manage experiments programmatically:

```python
from madsci.client.experiment_client import ExperimentClient
from madsci.common.types.experiment_types import (
    ExperimentDesign,
    ExperimentRegistration,
)

client = ExperimentClient("http://localhost:8002")

# Design an experiment
design = ExperimentDesign(
    experiment_name="Compound Screen Experiment",
    experiment_description="Screen compounds for activity",
    resource_conditions=[]  # Define required resources/conditions
)

# Register and start an experiment
experiment = client.start_experiment(
    experiment_design=design,
    run_name="Screen Run 1",
    run_description="Testing compound A at concentration 10"
)

# Get experiment details
experiment_details = client.get_experiment(experiment.experiment_id)

# Control experiment lifecycle
paused = client.pause_experiment(experiment.experiment_id)
continued = client.continue_experiment(experiment.experiment_id)
ended = client.end_experiment(experiment.experiment_id)
```

## Core Concepts

### Experiment Designs
Templates defining experimental parameters and structure:
- **Parameter definitions**: Specify experiment variables and ranges
- **Conditions**: Define prerequisites and constraints
- **Metadata**: Store design rationale and protocols

**ExperimentDesign Fields:**
- `experiment_name` (str): The name of the experiment
- `experiment_description` (Optional[str]): A description of the experiment
- `resource_conditions` (list[Conditions]): Starting layout of resources required
- `ownership_info` (OwnershipInfo): Information about users, campaigns, etc. that own this design

**ExperimentRegistration Fields:**
- `experiment_design` (ExperimentDesign): The experiment design to execute
- `run_name` (Optional[str]): Name for this specific experiment run
- `run_description` (Optional[str]): Description of the experiment run

### Experiment Runs
Individual executions of an experiment design:
- **Status tracking**: Monitor progress from registration to completion
- **Results storage**: Capture experimental outcomes and data
- **Lineage**: Link runs to their designs

**Experiment States:**
- `in_progress`: Experiment is currently running
- `paused`: Experiment is not currently running but can be resumed
- `completed`: Experiment run has finished successfully
- `failed`: Experiment has failed during execution
- `cancelled`: Experiment has been cancelled by user or system
- `unknown`: Experiment status is unknown

### Experiment Application

The `ExperimentApplication` class provides scaffolding for custom experiment logic:

```python
from madsci.experiment_application.experiment_application import ExperimentApplication

class MyExperiment(ExperimentApplication):
    def run_experiment(self, experiment_id: str) -> dict:
        # Custom experimental logic
        # Use other MADSci clients (workcell, data, etc.)
        return {"result": "success"}

app = MyExperiment(experiment_server_url="http://localhost:8002")
app.start()
```

## API Endpoints

The Experiment Manager provides the following REST endpoints:

### Experiment Management
- `GET /experiment/{experiment_id}` - Get an experiment by ID
- `GET /experiments?number=10` - Get latest experiments (default: 10)
- `POST /experiment` - Start a new experiment (body: ExperimentRegistration)

### Experiment Lifecycle Control
- `POST /experiment/{experiment_id}/end` - End an experiment
- `POST /experiment/{experiment_id}/continue` - Continue a paused experiment
- `POST /experiment/{experiment_id}/pause` - Pause an experiment
- `POST /experiment/{experiment_id}/cancel` - Cancel an experiment
- `POST /experiment/{experiment_id}/fail` - Mark an experiment as failed

### Service Management
- `GET /definition` - Get manager definition and configuration
- `GET /health` - Get manager health status (includes database connectivity)

Full API documentation is available at `http://localhost:8002/docs` when the service is running.

## Integration with MADSci Ecosystem

The Experiment Manager coordinates with other MADSci components:
- **Workcell Manager**: Execute workflows as part of experiments
- **Data Manager**: Store experimental results and files
- **Event Manager**: Log experimental events and milestones
- **Resource Manager**: Track samples and consumables used

**Example**: See [example_lab/](../../example_lab/) for complete integration examples with all managers working together.

## Database Migration Tools

MADSci Experiment Manager includes automated MongoDB migration tools that handle schema changes and version tracking for the experiment management system.

### Features

- **Version Compatibility Checking**: Automatically detects mismatches between MADSci package version and MongoDB schema version
- **Automated Backup**: Creates MongoDB dumps using `mongodump` before applying migrations to enable rollback on failure
- **Schema Management**: Creates collections and indexes based on schema definitions
- **Index Management**: Ensures required indexes exist for optimal query performance
- **Location Independence**: Auto-detects schema files or accepts explicit paths
- **Safe Migration**: All changes are applied transactionally with automatic rollback on failure

### Usage

#### Standard Usage
```bash
# Run migration for experiments database (auto-detects schema file)
python -m madsci.common.mongodb_migration_tool --database madsci_experiments

# Migrate with explicit database URL
python -m madsci.common.mongodb_migration_tool --db-url mongodb://localhost:27017 --database madsci_experiments

# Use custom schema file
python -m madsci.common.mongodb_migration_tool --database madsci_experiments --schema-file /path/to/schema.json

# Create backup only
python -m madsci.common.mongodb_migration_tool --database madsci_experiments --backup-only

# Restore from backup
python -m madsci.common.mongodb_migration_tool --database madsci_experiments --restore-from /path/to/backup

# Check version compatibility without migrating
python -m madsci.common.mongodb_migration_tool --database madsci_experiments --check-version
```

#### Docker Usage
When running in Docker containers, use docker-compose to execute migration commands:

```bash
# Run migration for experiments database in Docker
docker-compose run --rm experiment-manager python -m madsci.common.mongodb_migration_tool --db-url 'mongodb://mongodb:27017' --database 'madsci_experiments' --schema-file '/app/madsci/experiment_manager/schema.json'

# Create backup only in Docker
docker-compose run --rm experiment-manager python -m madsci.common.mongodb_migration_tool --db-url 'mongodb://mongodb:27017' --database 'madsci_experiments' --schema-file '/app/madsci/experiment_manager/schema.json' --backup-only

# Check version compatibility in Docker
docker-compose run --rm experiment-manager python -m madsci.common.mongodb_migration_tool --db-url 'mongodb://mongodb:27017' --database 'madsci_experiments' --schema-file '/app/madsci/experiment_manager/schema.json' --check-version
```

### Server Integration

The Experiment Manager server automatically checks for version compatibility on startup. If a mismatch is detected, the server will refuse to start and display migration instructions:

```bash
DATABASE INITIALIZATION REQUIRED! SERVER STARTUP ABORTED!
The database exists but needs version tracking setup.
To resolve this issue, run the migration tool and restart the server.
```

### Schema File Location

The migration tool automatically searches for schema files in:
- `madsci/experiment_manager/schema.json`

### Backup Location

Backups are stored in `.madsci/mongodb/backups/` with timestamped filenames:
- Format: `madsci_experiments_backup_YYYYMMDD_HHMMSS`
- Can be restored using the `--restore-from` option

### Requirements

- MongoDB server running and accessible
- MongoDB tools (`mongodump`, `mongorestore`) installed
- Appropriate database permissions for the specified user
