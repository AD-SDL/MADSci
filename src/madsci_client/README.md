# MADSci Clients

Provides a collection of clients for interacting with the different components of a MADSci interface.

## Installation

See the main [README](../../README.md#installation) for installation options. This package is available as:

- PyPI: `pip install madsci.client`
- Docker: Included in `ghcr.io/ad-sdl/madsci`
- **Dependency**: Required by most other MADSci packages

## Node Clients

Node clients provide a robust interface for interacting with MADSci Nodes:

- **Action execution**: Send actions with automatic parameter serialization and result handling
- **Node introspection**: Get detailed node information, capabilities, and schemas
- **State monitoring**: Monitor current state and status with real-time updates
- **Administrative control**: Send commands (safety stop, pause, resume, etc.)
- **Error handling**: Comprehensive error reporting and retry mechanisms
- **File operations**: Seamless file upload/download support

Multiple communication protocols are supported through a common interface. The `AbstractNodeClient` base class enables custom protocol implementations.

### REST Client

Communicate with MADSci Nodes via REST API with enhanced argument handling:

```python
from madsci.client.node.rest_node_client import RestNodeClient
from madsci.common.types.action_types import ActionRequest
from pathlib import Path

client = RestNodeClient(url="http://example:2000")

# Simple action execution
action_request = ActionRequest(action_name="get_temperature", args={}, files={})
result = client.send_action(action_request)

# Action with parameters (automatically serialized)
action_request = ActionRequest(
    action_name="analyze_sample",
    args={"sample_id": "sample_001", "duration": 60, "temperature": 25.0},
    files={}
)
result = client.send_action(action_request)

# File upload handling
action_request = ActionRequest(
    action_name="process_file",
    args={"output_dir": "./results"},
    files={"input_file": Path("./data.csv")}
)
result = client.send_action(action_request)

# Get comprehensive node info
info = client.get_info()
status = client.get_status()
```

**Key Features:**
- Automatic parameter validation and serialization
- File upload/download handling with progress tracking
- Comprehensive error messages and debugging information
- Support for complex return types (JSON, files, datapoint IDs)
- Node capability checking and schema introspection

**Examples**: See [example_lab/notebooks/node_notebook.ipynb](../../example_lab/notebooks/node_notebook.ipynb) for detailed usage.

## Event Client

Allows a user or system to interface with a MADSci EventManager, or log events locally if one isn't available/configured. Can be used to both log new events and query logged events.

For detailed documentation on usage, see the [EventManager Documentation](../madsci_event_manager/README.md).

## Experiment Application

The `ExperimentApplication` class is a helper class designed to act as scaffolding for a user's own python experiment. It provides helpful tooling around tracking and responding to changes in Experiment status, marshalling the clients needed to leverage different parts of a MADSci-enabled lab, and implementing your own custom experimental logic.

## Experiment Client

Allows the user or an automated system/agent to inerface with a MADSci ExperimentManager to capture Experiment Designs and track status and metadata related to specific Experimental Runs and whole Experimental Campaigns.

For detailed documentation on usage, see the [ExperimentManager Documentation](../madsci_experiment_manager/README.md)

## Data Client

Allows the user or an automated system/agent to interface with a MADSci DataManager to upload, query, and fetch `DataPoint`s. Currently supports `ValueDataPoint`s (which can include any JSON-serializable data) and `FileDataPoint`s (which directly stores the files).

### Enhanced Datapoint Operations

The Data Client provides comprehensive methods for working with datapoints in workflows:

```python
from madsci.client.data_client import DataClient

client = DataClient()

# Upload value datapoints
datapoint_id = client.submit_datapoint({
    "label": "experiment_result",
    "value": {"temperature": 25.0, "pressure": 1.2}
})

# Upload file datapoints
file_datapoint_id = client.submit_file_datapoint(
    file_path=Path("./results.csv"),
    label="analysis_results"
)

# Batch fetch multiple datapoints efficiently
datapoints = client.get_datapoints_by_ids(["id1", "id2", "id3"])

# Query datapoints with filters
results = client.query_datapoints(
    label_pattern="experiment_*",
    limit=10
)

# Get lightweight metadata without loading full data
metadata = client.get_datapoint_metadata("datapoint_id")
```

The Data Client integrates seamlessly with the workflow system, storing only ULID strings in workflows for optimal performance while providing easy access to full datapoint objects when needed.

**Integration with Workflows:**
```python
# Workflow helper methods
from madsci.client.workcell_client import WorkcellClient

workcell = WorkcellClient()
workflow = workcell.submit_workflow("analysis.yaml")

# Get datapoint from workflow step
datapoint_id = workflow.get_datapoint_id("analysis_step")
datapoint = workflow.get_datapoint("analysis_step")
```

For detailed documentation on usage, see the [DataManager Documentation](../madsci_data_manager/README.md).

## Resource Client

Allows the user or an automated system/agent to interface with a MADSci ResourceManager to initialize, manage, track, query, update, and remove physical resources (including samples, consumables, containers, labware, etc.).

For detailed documentation on usage, see the [ResourceManager Documentation](../madsci_resource_manager/README.md).

## Workcell Client

Allows the user or an automated system/agent to interface with a MADSci WorkcellManager. Includes support for submitting, querying, and controlling Workflows, sending admin commands to the Workcell, and interacting with Workcell Locations.

For detailed documentation on usage, see the [WorkcellManager Documentation](../madsci_workcell_manager/README.md).
