# MADSci Experiment Manager

Manages experimental runs and campaigns across a MADSci-powered lab, providing experiment design, tracking, and lifecycle management.

## Features

- **Experiment Campaigns**: Organize related experiments under a common research goal
- **Experiment Designs**: Define experimental parameters, conditions, and metadata
- **Experiment Runs**: Track individual experiment executions with status and results
- **Lifecycle Management**: Monitor experiment progress from design to completion
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
python -m madsci.experiment_manager.experiment_server
```

### Manager Setup

For custom deployments, see [example_experiment.manager.yaml](../../example_lab/managers/example_experiment.manager.yaml) for configuration options.

### Experiment Client

Use `ExperimentClient` to manage experiments programmatically:

```python
from madsci.client.experiment_client import ExperimentClient
from madsci.common.types.experiment_types import (
    ExperimentDesign,
    ExperimentRegistration,
    ExperimentalCampaign
)

client = ExperimentClient("http://localhost:8002")

# Create an experiment campaign
campaign = ExperimentalCampaign(
    name="Drug Discovery Campaign",
    description="Testing compound effectiveness",
    principal_investigator="Dr. Smith"
)
created_campaign = client.create_campaign(campaign)

# Design an experiment
design = ExperimentDesign(
    name="Compound Screen Experiment",
    description="Screen compounds for activity",
    campaign_id=created_campaign.campaign_id,
    parameters={"compounds": ["A", "B", "C"], "concentrations": [1, 10, 100]}
)
created_design = client.create_experiment_design(design)

# Register and run an experiment
registration = ExperimentRegistration(
    experiment_design_id=created_design.design_id,
    parameters={"compound": "A", "concentration": 10}
)
experiment = client.register_experiment(registration)

# Track experiment status
status = client.get_experiment_status(experiment.experiment_id)
```

## Core Concepts

### Experiment Campaigns
Group related experiments under a research theme or project:
- **Campaign management**: Track multiple related experiments
- **Principal investigator**: Associate experiments with researchers
- **Metadata**: Store campaign-level information and goals

### Experiment Designs
Templates defining experimental parameters and structure:
- **Parameter definitions**: Specify experiment variables and ranges
- **Conditions**: Define prerequisites and constraints
- **Metadata**: Store design rationale and protocols

### Experiment Runs
Individual executions of an experiment design:
- **Status tracking**: Monitor progress from registration to completion
- **Results storage**: Capture experimental outcomes and data
- **Lineage**: Link runs to their designs and campaigns

### Experiment Application

The `ExperimentApplication` class provides scaffolding for custom experiment logic:

```python
from madsci.experiment_application import ExperimentApplication

class MyExperiment(ExperimentApplication):
    def run_experiment(self, experiment_id: str) -> dict:
        # Custom experimental logic
        # Use other MADSci clients (workcell, data, etc.)
        return {"result": "success"}

app = MyExperiment(experiment_server_url="http://localhost:8002")
app.start()
```

## Integration with MADSci Ecosystem

The Experiment Manager coordinates with other MADSci components:
- **Workcell Manager**: Execute workflows as part of experiments
- **Data Manager**: Store experimental results and files
- **Event Manager**: Log experimental events and milestones
- **Resource Manager**: Track samples and consumables used

**Example**: See [example_lab/](../../example_lab/) for complete integration examples with all managers working together.
