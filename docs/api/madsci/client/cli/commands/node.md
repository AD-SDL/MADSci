Module madsci.client.cli.commands.node
======================================
MADSci CLI node command group.

Provides subcommands for node inspection, control, and interaction:
listing, info, status, state, log, admin commands, action execution,
action results, action history, config management, adding nodes, and
an interactive shell.

Classes
-------

`NodeShell(node_name: str, node_client: Any, node_data: Any)`
:   Interactive REPL for a MADSci node.
    
    Initialize the NodeShell.
    
    Args:
        node_name: Name of the node.
        node_client: RestNodeClient instance.
        node_data: Raw node data from workcell.

    ### Ancestors (in MRO)

    * cmd.Cmd

    ### Methods

    `do_EOF(self, _arg: str) ‑> bool`
    :   Exit the shell.

    `do_actions(self, _arg: str) ‑> None`
    :   List available actions.

    `do_admin(self, arg: str) ‑> None`
    :   Send admin command: admin <command>.

    `do_config(self, _arg: str) ‑> None`
    :   Show current node configuration.

    `do_exit(self, _arg: str) ‑> bool`
    :   Exit the shell.

    `do_info(self, _arg: str) ‑> None`
    :   Show node information.

    `do_log(self, arg: str) ‑> None`
    :   Show node log: log [N]  (default: last 20 entries).

    `do_quit(self, _arg: str) ‑> bool`
    :   Exit the shell.

    `do_run(self, arg: str) ‑> None`
    :   Run an action: run <action_name> [json_args].

    `do_state(self, _arg: str) ‑> None`
    :   Show the current state of the node.

    `do_status(self, _arg: str) ‑> None`
    :   Show the current status of the node.

    `emptyline(self) ‑> None`
    :   Do nothing on empty line.