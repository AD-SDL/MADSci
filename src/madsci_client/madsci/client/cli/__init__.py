"""MADSci CLI - Unified command-line interface for MADSci operations.

This module provides the main entry point for the MADSci CLI, offering a
comprehensive toolkit for building and operating self-driving laboratories.
"""

import importlib
from typing import ClassVar

import click
from rich.console import Console

# Version will be loaded dynamically
__version__ = "0.6.2"

# Lazy command registry: maps command names to (module_path, attr_name) tuples.
# Commands are only imported when actually invoked.
_LAZY_COMMANDS: dict[str, tuple[str, str]] = {
    "version": ("madsci.client.cli.commands.version", "version"),
    "doctor": ("madsci.client.cli.commands.doctor", "doctor"),
    "status": ("madsci.client.cli.commands.status", "status"),
    "logs": ("madsci.client.cli.commands.logs", "logs"),
    "tui": ("madsci.client.cli.commands.tui", "tui"),
    "registry": ("madsci.client.cli.commands.registry", "registry"),
    "migrate": ("madsci.client.cli.commands.migrate", "migrate"),
    "new": ("madsci.client.cli.commands.new", "new"),
    "start": ("madsci.client.cli.commands.start", "start"),
    "stop": ("madsci.client.cli.commands.stop", "stop"),
    "init": ("madsci.client.cli.commands.init", "init"),
    "validate": ("madsci.client.cli.commands.validate", "validate"),
    "run": ("madsci.client.cli.commands.run", "run"),
    "completion": ("madsci.client.cli.commands.completion", "completion"),
    "backup": ("madsci.client.cli.commands.backup", "backup"),
    "commands": ("madsci.client.cli.commands.commands", "commands"),
    "config": ("madsci.client.cli.commands.config", "config"),
}


class AliasedGroup(click.Group):
    """Click group that supports command aliases and lazy command loading.

    Commands are imported only when they are actually invoked or when
    help text is requested, reducing CLI startup time.
    """

    _aliases: ClassVar[dict[str, str]] = {
        "n": "new",
        "s": "status",
        "l": "logs",
        "doc": "doctor",
        "val": "validate",
        "ui": "tui",
        "cmd": "commands",
        "cfg": "config",
    }

    def list_commands(self, ctx: click.Context) -> list[str]:
        """List all available commands, including lazy ones."""
        # Combine eagerly registered commands with lazy ones
        eager = set(super().list_commands(ctx))
        return sorted(eager | set(_LAZY_COMMANDS.keys()))

    def get_command(self, ctx: click.Context, cmd_name: str) -> click.Command | None:
        """Resolve command aliases and lazily import commands."""
        # Check if it's an alias
        if cmd_name in self._aliases:
            cmd_name = self._aliases[cmd_name]

        # Try eagerly registered commands first
        cmd = super().get_command(ctx, cmd_name)
        if cmd is not None:
            return cmd

        # Lazily import the command
        if cmd_name in _LAZY_COMMANDS:
            module_path, attr_name = _LAZY_COMMANDS[cmd_name]
            module = importlib.import_module(module_path)
            cmd = getattr(module, attr_name)
            # Cache it so we don't import again
            self.add_command(cmd, cmd_name)
            return cmd

        return None

    def resolve_command(
        self, ctx: click.Context, args: list[str]
    ) -> tuple[str | None, click.Command | None, list[str]]:
        """Resolve command, handling aliases."""
        _, cmd, args = super().resolve_command(ctx, args)
        return cmd.name if cmd else None, cmd, args


@click.group(cls=AliasedGroup)
@click.option(
    "-c",
    "--config",
    type=click.Path(exists=True),
    help="Configuration file path.",
    envvar="MADSCI_CONFIG",
)
@click.option(
    "--lab-url",
    envvar="MADSCI_LAB_URL",
    default="http://localhost:8000/",
    help="Lab manager URL.",
)
@click.option(
    "-v",
    "--verbose",
    count=True,
    help="Increase verbosity (can be repeated: -vv, -vvv).",
)
@click.option(
    "-q",
    "--quiet",
    is_flag=True,
    help="Suppress non-essential output.",
)
@click.option(
    "--no-color",
    is_flag=True,
    envvar="NO_COLOR",
    help="Disable colored output.",
)
@click.option(
    "--json",
    "json_output",
    is_flag=True,
    help="Output in JSON format (where applicable).",
)
@click.version_option(version=__version__, prog_name="madsci")
@click.pass_context
def madsci(
    ctx: click.Context,
    config: str | None,
    lab_url: str,
    verbose: int,
    quiet: bool,
    no_color: bool,
    json_output: bool,
) -> None:
    """MADSci - Modular Autonomous Discovery for Science.

    A comprehensive toolkit for building and operating self-driving laboratories.

    \b
    Quick start:
        madsci init           Initialize a new lab
        madsci start          Start all services
        madsci status         Check service status
        madsci tui            Launch interactive interface

    \b
    For more information:
        madsci <command> --help
        https://ad-sdl.github.io/MADSci/
    """
    # Ensure context object exists
    ctx.ensure_object(dict)

    # Store configuration in context
    ctx.obj["config_path"] = config
    ctx.obj["lab_url"] = lab_url
    ctx.obj["verbose"] = verbose
    ctx.obj["quiet"] = quiet
    ctx.obj["json"] = json_output

    # Create console with appropriate settings
    ctx.obj["console"] = Console(
        no_color=no_color,
        quiet=quiet,
        force_terminal=None,  # Auto-detect
    )


def main() -> None:
    """CLI entry point."""
    madsci()


if __name__ == "__main__":
    main()
