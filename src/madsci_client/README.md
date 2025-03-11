# MADSci Clients

Provides a collection of clients for interacting with the different components of a MADSci interface.

## Clients

### CLI

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

### Node Clients

Node clients allow you to interface with MADSci Nodes to:

- Send actions and get action results
- Get information about the node
- Get the current state and status of the node
- Send administrative commands (safety stop, pause, resume, etc)

As MADSci is designed to support multiple communications protocols, we provide a client for each. In addition, an `AbstractNodeClient` base class is provided, which can be inherited from to implement your own node clients for different interfaces.

#### REST Client

The Rest Client

### Event Client

Allows a user or system to interface with a MADSci EventManager, or log events locally if one isn't available/configured. Can be used to both log new events and query logged events.

For detailed documentation on usage, see the [EventManager Documentation](../madsci_event_manager/README.md).
