# MADSci Experiment Application

## Overview
The Experiment Application package provides a comprehensive framework for managing automated and autonomous experiments using MADSci-powered laboratories. This package serves as the primary interface for scientists and researchers to design, execute, and monitor complex experimental campaigns.

## Key Components

### ExperimentApplication Class
- **experiment_application.py**: Main class inheriting from `RestNode` for experiment management
- Provides high-level API for complete experiment lifecycle management
- Integration with all MADSci manager services via client libraries
- Support for both standalone execution and server mode operation
- Advanced condition evaluation system for resource and location validation

### ExperimentApplicationConfig Class
- **Configuration management**: Inherits from `RestNodeConfig` with experiment-specific settings
- **Environment integration**: Supports multiple configuration file formats and environment variables
- **Server mode control**: Configurable operation as REST node or standalone application

## Core Implementation Details

### Class Methods and Initialization
```python
# Correct initialization patterns
app = ExperimentApplication(
    lab_server_url="http://localhost:8000",
    experiment_design=experiment_design,
    experiment=existing_experiment  # Optional for continuing experiments
)

# Class methods for different scenarios
app = ExperimentApplication.start_new(lab_server_url, experiment_design)
app = ExperimentApplication.continue_experiment(experiment, lab_server_url)
```

### Available Methods
- **Lifecycle Management**:
  - `start_experiment_run(run_name, run_description)`: Start new experiment run
  - `end_experiment(status)`: End experiment with optional status
  - `pause_experiment()`: Pause current experiment
  - `cancel_experiment()`: Cancel current experiment
  - `fail_experiment()`: Mark experiment as failed

- **Context Management**:
  - `manage_experiment(run_name, run_description)`: Context manager for automatic lifecycle
  - `add_experiment_management(func)`: Decorator for wrapping functions with experiment management

- **Status and Monitoring**:
  - `check_experiment_status()`: Check and handle experiment state changes
  - `handle_exception(exception)`: Custom exception handling (overridable)

- **Condition Evaluation**:
  - `evaluate_condition(condition)`: Evaluate resource/location conditions
  - `get_resource_from_condition(condition)`: Retrieve resource from condition
  - `get_location_from_condition(condition)`: Retrieve location from condition
  - `check_resource_field(resource, condition)`: Validate resource field values

### Manager Service Clients
The application provides direct access to all MADSci manager clients:
- `experiment_client`: ExperimentClient for experiment management
- `data_client`: DataClient for data storage and retrieval
- `resource_client`: ResourceClient for resource tracking
- `workcell_client`: WorkcellClient for workflow coordination
- `event_client`: EventClient for logging (also available as `logger`)
- `location_client`: LocationClient for location management
- `lab_client`: LabClient for lab configuration

### Condition System
The application implements a sophisticated condition evaluation system supporting:

#### Condition Types
- `resource_present`: Check if specific resource exists at location
- `no_resource_present`: Check absence of resource at location
- `resource_field_check`: Validate resource field values
- `resource_child_field_check`: Validate child resource field values

#### Supported Operators
- `is_greater_than`, `is_less_than`, `is_equal_to`
- `is_greater_than_or_equal_to`, `is_less_than_or_equal_to`

## Development Patterns

### Subclassing for Custom Applications
```python
class MyExperimentApp(ExperimentApplication):
    def run_experiment(self, *args, **kwargs):
        """Override this method for custom experiment logic"""
        with self.manage_experiment():
            # Custom experiment implementation
            pass

    def handle_exception(self, exception):
        """Override for custom error handling"""
        if isinstance(exception, SpecificError):
            # Custom handling
            pass
        else:
            super().handle_exception(exception)
```

### Server Mode Operation
```python
# Configure for REST node server
config = ExperimentApplicationConfig(
    server_mode=True,
    node_name="experiment_server",
    port=8010
)

app = ExperimentApplication(config=config)
app.start_app()  # Starts REST server
```

### Autonomous Operation
```python
class AutonomousApp(ExperimentApplication):
    @threaded_daemon
    def loop(self):
        """Continuous experiment loop for autonomous operation"""
        while True:
            if self.evaluate_condition(trigger_condition):
                with self.manage_experiment():
                    # Autonomous experiment logic
                    pass
            time.sleep(monitoring_interval)
```

## Configuration Options

### Environment Variables (EXPERIMENT_ prefix)
- `EXPERIMENT_SERVER_MODE`: Enable/disable server mode
- `EXPERIMENT_LAB_SERVER_URL`: Lab server connection URL
- `EXPERIMENT_NODE_NAME`: Node name for server mode
- `EXPERIMENT_PORT`: Server port
- `EXPERIMENT_RUN_ARGS`: Arguments for standalone run_experiment
- `EXPERIMENT_RUN_KWARGS`: Keyword arguments for standalone run_experiment

### Configuration Files
Supports multiple formats: `.env`, `experiment.env`, `settings.toml`, `experiment.settings.toml`, etc.

## Integration with MADSci Ecosystem

### Manager Service Ports
- Event Manager: 8001
- Experiment Manager: 8002
- Resource Manager: 8003
- Data Manager: 8004
- Workcell Manager: 8005
- Location Manager: 8006

### ULID Usage
- All IDs use ULID format for better performance and sortability
- Use `new_ulid_str()` from `madsci.common.utils` for ID generation

### Exception Handling
- `ExperimentCancelledError`: Raised when experiment is cancelled externally
- `ExperimentFailedError`: Raised when experiment fails externally
- Automatic experiment failure on unhandled exceptions

## Testing and Development
- Inherits from `RestNode` providing standard node testing patterns
- Integration tests should use docker containers for manager services
- Unit tests can mock manager clients
- Use `pytest` directly (not `python -m pytest`) for running tests
