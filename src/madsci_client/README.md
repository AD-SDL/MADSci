# MADSci Clients

Provides a collection of clients for interacting with the different components of a MADSci interface.

## Node Clients

Node clients allow you to interface with MADSci Nodes to:

- Send actions and get action results
- Get information about the node
- Get the current state and status of the node
- Send administrative commands (safety stop, pause, resume, etc)

As MADSci is designed to support multiple communications protocols, we provide a client for each. In addition, an `AbstractNodeClient` base class is provided, which can be inherited from to implement your own node clients for different interfaces.

### REST Client

Communicate with MADSci Nodes via REST API:

```python
from madsci.client.node.rest_node_client import RestNodeClient

client = RestNodeClient(url="http://example:2000")
status = client.get_status()
result = client.execute_action("my_action", {"param": "value"})
```

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

For detailed documentation on usage, see the [DataManager Documentation](../madsci_data_manager/README.md).

## Resource Client

Allows the user or an automated system/agent to interface with a MADSci ResourceManager to initialize, manage, track, query, update, and remove physical resources (including samples, consumables, containers, labware, etc.).

For detailed documentation on usage, see the [ResourceManager Documentation](../madsci_resource_manager/README.md).

## Workcell Client

Allows the user or an automated system/agent to interface with a MADSci WorkcellManager. Includes support for submitting, querying, and controlling Workflows, sending admin commands to the Workcell, and interacting with Workcell Locations.

For detailed documentation on usage, see the [WorkcellManager Documentation](../madsci_workcell_manager/README.md).
