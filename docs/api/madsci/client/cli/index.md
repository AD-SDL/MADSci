Module madsci.client.cli
========================
MADSci CLI - Unified command-line interface for MADSci operations.

This module provides the main entry point for the MADSci CLI, offering a
comprehensive toolkit for building and operating self-driving laboratories.

Sub-modules
-----------
* madsci.client.cli.commands
* madsci.client.cli.tui
* madsci.client.cli.utils

Functions
---------

`main() ‑> None`
:   CLI entry point.

Classes
-------

`AliasedGroup(name: str | None = None, commands: cabc.MutableMapping[str, Command] | cabc.Sequence[Command] | None = None, invoke_without_command: bool = False, no_args_is_help: bool | None = None, subcommand_metavar: str | None = None, chain: bool = False, result_callback: t.Callable[..., t.Any] | None = None, **kwargs: t.Any)`
:   Click group that supports command aliases and lazy command loading.
    
    Commands are imported only when they are actually invoked or when
    help text is requested, reducing CLI startup time.

    ### Ancestors (in MRO)

    * click.core.Group
    * click.core.Command

    ### Methods

    `get_command(self, ctx: click.core.Context, cmd_name: str) ‑> click.core.Command | None`
    :   Resolve command aliases and lazily import commands.

    `list_commands(self, ctx: click.core.Context) ‑> list[str]`
    :   List all available commands, including lazy ones.

    `resolve_command(self, ctx: click.core.Context, args: list[str]) ‑> tuple[str | None, click.core.Command | None, list[str]]`
    :   Resolve command, handling aliases.