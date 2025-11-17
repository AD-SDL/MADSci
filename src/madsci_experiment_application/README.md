# MADSci Experiment Application

The MADSci Experiment Application provides a high-level framework for creating and managing scientific experiments within the MADSci ecosystem. This package serves as the primary interface for scientists and researchers to design, execute, and monitor automated and autonomous experimental campaigns.

## Overview

The `ExperimentApplication` class provides a comprehensive framework for experiment management that can:

- Manage complete experiment lifecycle (start, pause, resume, cancel, end)
- Integrate with all MADSci manager services (experiment, data, resource, workcell, event, location, lab)
- Evaluate complex resource and location conditions before and during experiments
- Operate in both standalone execution and server modes as a REST node
- Provide automatic experiment context management and error handling

## Key Features

- **Experiment Lifecycle Management**: Complete control over experiment states with proper error handling
- **Condition Evaluation System**: Advanced validation of resource availability, locations, and field constraints
- **Context Management**: Automatic experiment setup and teardown with context managers
- **Dual Operation Modes**: Standalone execution or REST node server for remote control
- **Exception Handling**: Built-in handling for experiment failures, cancellations, and pauses
- **Event Logging**: Integrated logging and monitoring through the MADSci event system
- **Resource Management**: Real-time resource tracking and validation

## Dependencies

- `madsci.common`: Shared types, utilities, and base classes
- `madsci.client`: Client libraries for all MADSci manager services
- `madsci.node_module`: REST node framework for server mode operation
- `rich`: Enhanced console output and formatting
- `pydantic`: Data validation and configuration management

## Installation

```bash
# Using PDM (for development)
pdm install

# Using pip (for production use)
pip install madsci.experiment_application
```

## Quick Start

### Basic Usage

```python
from madsci.experiment_application import ExperimentApplication
from madsci.common.types.experiment_types import ExperimentDesign

# Option 1: Create with experiment design
experiment_design = ExperimentDesign.from_yaml("my_experiment.yaml")
app = ExperimentApplication(
    lab_server_url="http://localhost:8000",
    experiment_design=experiment_design
)

# Start and manage an experiment using context manager
with app.manage_experiment(run_name="Test Run", run_description="Initial testing"):
    # Your experiment code here
    app.logger.info("Running experiment steps...")
    # Experiment automatically ends on successful completion
    # or fails on exception
```

### Class Methods for Different Scenarios

```python
# Start a completely new experiment
app = ExperimentApplication.start_new(
    lab_server_url="http://localhost:8000",
    experiment_design=experiment_design
)

# Continue an existing experiment
existing_experiment = experiment_client.get_experiment("01ARZ3NDEKTSV4RRFFQ69G5FAV")
app = ExperimentApplication.continue_experiment(
    experiment=existing_experiment,
    lab_server_url="http://localhost:8000"
)
```

### Manual Experiment Control

```python
app = ExperimentApplication(
    lab_server_url="http://localhost:8000",
    experiment_design=experiment_design
)

# Manual lifecycle management
app.start_experiment_run(run_name="Manual Control Run")
try:
    # Your experiment logic
    app.check_experiment_status()  # Checks for pause/cancel/fail
    # ... more experiment steps
except ExperimentCancelledError:
    app.logger.info("Experiment was cancelled")
except ExperimentFailedError:
    app.logger.info("Experiment failed")
else:
    app.end_experiment()
```

## Condition Evaluation System

The application includes a powerful condition evaluation system for validating resources, locations, and field values before and during experiments.

### Condition Types

```python
from madsci.common.types.condition_types import Condition

# Resource presence at location
condition = Condition(
    condition_name="sample_present",
    condition_type="resource_present",
    location_name="sample_holder_1",
    key="0",  # Position in location
    resource_class="Sample"
)

# Resource field validation
condition = Condition(
    condition_name="temperature_check",
    condition_type="resource_field_check",
    resource_name="furnace_1",
    field="temperature",
    operator="is_greater_than",
    target_value=500.0
)

# Resource child field validation
condition = Condition(
    condition_name="sample_volume_check",
    condition_type="resource_child_field_check",
    resource_name="sample_rack",
    key="position_1",
    field="volume",
    operator="is_greater_than_or_equal_to",
    target_value=1.0
)

# Evaluate conditions
if app.evaluate_condition(condition):
    app.logger.info("Condition satisfied")
```

### Supported Operators

- `is_greater_than`
- `is_less_than`
- `is_equal_to`
- `is_greater_than_or_equal_to`
- `is_less_than_or_equal_to`

## Server Mode Operation

The application can operate as a REST node for remote experiment execution:

```python
from madsci.experiment_application import ExperimentApplicationConfig

# Configure for server mode
config = ExperimentApplicationConfig(
    server_mode=True,
    node_name="experiment_app_server",
    node_description="Automated experiment server",
    port=8010
)

class MyExperimentApp(ExperimentApplication):
    def __init__(self):
        super().__init__(config=config)

    def run_experiment(self, parameter1: str, parameter2: float):
        """Custom experiment implementation"""
        with self.manage_experiment(run_name=f"Auto_{parameter1}"):
            # Experiment logic using parameters
            self.logger.info(f"Running with {parameter1}, {parameter2}")

# Start server
app = MyExperimentApp()
app.start_app()  # Starts REST server on configured port
```

## Configuration

### Environment Variables

All configuration can be set via environment variables with the `EXPERIMENT_` prefix:

```bash
export EXPERIMENT_SERVER_MODE=true
export EXPERIMENT_LAB_SERVER_URL=http://localhost:8000
export EXPERIMENT_NODE_NAME=my_experiment_app
export EXPERIMENT_PORT=8010
```

### Configuration Files

Supports multiple configuration file formats:

- `.env` or `experiment.env`
- `settings.toml` or `experiment.settings.toml`
- `settings.yaml` or `experiment.settings.yaml`
- `settings.json` or `experiment.settings.json`

Example `experiment.settings.toml`:

```toml
server_mode = false
lab_server_url = "http://localhost:8000"
node_name = "experiment_application"
port = 8010

[run_args]
# Arguments for run_experiment when not in server mode

[run_kwargs]
# Keyword arguments for run_experiment when not in server mode
parameter1 = "default_value"
parameter2 = 100.0
```

## Advanced Usage

### Custom Exception Handling

```python
class MyExperimentApp(ExperimentApplication):
    def handle_exception(self, exception: Exception):
        """Custom exception handling"""
        if isinstance(exception, KeyboardInterrupt):
            self.logger.info("Experiment interrupted by user")
            self.pause_experiment()
        else:
            # Use default behavior
            super().handle_exception(exception)
```

### Experiment Loop for Autonomous Operation

```python
class AutonomousApp(ExperimentApplication):
    @threaded_daemon
    def loop(self):
        """Continuous experiment loop"""
        while True:
            # Check conditions
            if self.evaluate_condition(my_condition):
                with self.manage_experiment():
                    # Run experiment iteration
                    pass
            time.sleep(60)  # Wait before next iteration
```

### Using the Decorator Pattern

```python
app = ExperimentApplication(experiment_design=design)

@app.add_experiment_management
def my_experiment_function(param1: str, param2: int):
    """This function will automatically be wrapped with experiment management"""
    app.logger.info(f"Running experiment with {param1}, {param2}")
    # Function automatically starts/ends experiment

# Call the decorated function
my_experiment_function("test", 42)
```

## Manager Service Integration

The application provides direct access to all MADSci manager services:

```python
app = ExperimentApplication(lab_server_url="http://localhost:8000")

# Access to all manager clients
app.experiment_client  # Experiment management (port 8002)
app.data_client       # Data storage and retrieval (port 8004)
app.resource_client   # Resource and inventory tracking (port 8003)
app.workcell_client   # Workflow coordination (port 8005)
app.event_client      # Event logging (port 8001)
app.location_client   # Location management (port 8006)
app.lab_client        # Lab configuration

# Example usage
resources = app.resource_client.list_resources()
app.data_client.store_data(experiment_id=app.experiment.experiment_id, data=results)
```

## Error Handling

The application provides comprehensive error handling for experiment states:

```python
from madsci.common.exceptions import ExperimentCancelledError, ExperimentFailedError

try:
    with app.manage_experiment():
        app.check_experiment_status()  # Raises exception if cancelled/failed
        # Experiment logic
except ExperimentCancelledError:
    app.logger.info("Experiment was cancelled externally")
except ExperimentFailedError:
    app.logger.info("Experiment failed externally")
except Exception as e:
    app.logger.error(f"Unexpected error: {e}")
    # Application will automatically mark experiment as failed
```

## ULID Usage

MADSci uses ULID (Universally Unique Lexicographically Sortable Identifier) for all ID generation:

```python
from madsci.common.utils import new_ulid_str

# All experiment IDs, resource IDs, etc. are ULIDs
experiment_id = app.experiment.experiment_id  # ULID string
new_resource_id = new_ulid_str()  # Generate new ULID
```
