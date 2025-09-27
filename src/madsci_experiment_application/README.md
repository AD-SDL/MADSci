# MADSci Experiment Application

The MADSci Experiment Application provides a framework for creating and managing scientific experiments within the MADSci ecosystem.

## Overview

The `ExperimentApplication` class serves as a base class for creating experiment applications that can:

- Manage experiment lifecycle (start, pause, cancel, end)
- Interact with MADSci manager services (experiment, data, resource, workcell, event)
- Handle experiment conditions and resource validation
- Operate in both standalone and server modes

## Key Features

- **Experiment Management**: Start, pause, resume, cancel, and end experiments
- **Resource Validation**: Evaluate resource conditions before experiment execution
- **Event Logging**: Integrated logging through the event management system
- **Context Management**: Automatic experiment context handling
- **Server Mode**: Can operate as a REST node for remote experiment execution

## Dependencies

- `madsci.common`: Shared types and utilities
- `madsci.client`: Client libraries for MADSci services
- `madsci.node_module`: Node framework for REST endpoints

## Usage

```python
from madsci.experiment_application import ExperimentApplication

# Create an experiment application
app = ExperimentApplication(
    experiment_design=my_experiment_design,
    experiment_server_url="http://localhost:8002"
)

# Start and manage an experiment
with app.manage_experiment(run_name="My Experiment"):
    # Your experiment code here
    pass
```

## Configuration

The application can be configured through environment variables, TOML files, or direct instantiation:

- Environment prefix: `EXPERIMENT_`
- Config files: `experiment.env`, `experiment.settings.toml`, etc.
