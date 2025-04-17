# MADSci Clients

Provides a collection of clients for interacting with the different components of a MADSci interface.

## CLI

**Note: the MADSci CLI is not currently stable, and commands/options/arguments may have breaking changes from update to update**

The command line interface is a tool for MADSci-powered lab administrators and users to interact with the system. It's designed to facilitate common interactions with the definition files used to configure and control a MADSci Lab.

For a complete and up-to-date list of subcommands, run `madsci --help`. Alternatively, you can use the MADSci Terminal User Interface (TUI) to easily craft commands with `madsci tui`.

```
Usage: madsci [OPTIONS] COMMAND [ARGS]...

  MADSci command line interface.

Options:
  -q, --quiet  Run in quiet mode, skipping prompts.
  --help       Show this message and exit.

Commands:
  lab       Manage labs.
  manager   Manage lab system managers.
  node      Manage nodes.
  resource  Manage resources.
  tui       Open Textual TUI.
  version   Display the MADSci client version.
  workcell  Manage workcells
```

## Node Clients

Node clients allow you to interface with MADSci Nodes to:

- Send actions and get action results
- Get information about the node
- Get the current state and status of the node
- Send administrative commands (safety stop, pause, resume, etc)

As MADSci is designed to support multiple communications protocols, we provide a client for each. In addition, an `AbstractNodeClient` base class is provided, which can be inherited from to implement your own node clients for different interfaces.

### REST Client

The RestNodeClient class allows you to communicate with and control any server implementing the MADSci Node standard (see [MADSci Node Module](../madsci_node_module/README.md)). See a basic example below, or the `node_notebook.ipynb` in the [MADSci Examples](https://github.com/ad-sdl/MADSci_Examples).

```python
from madsci.client.node.rest_node_client import RestNodeClient

client = RestNodeClient(url="http://example:2000")
client.get_status()
```

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
