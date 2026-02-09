"""MADSci CLI - Unified command-line interface for MADSci operations.

This module provides the main entry point for the MADSci CLI, offering a
comprehensive toolkit for building and operating self-driving laboratories.
"""

from typing import ClassVar

import click

# Import command functions from their modules
from madsci.client.cli.commands.doctor import doctor
from madsci.client.cli.commands.logs import logs
from madsci.client.cli.commands.migrate import migrate
from madsci.client.cli.commands.registry import registry
from madsci.client.cli.commands.status import status
from madsci.client.cli.commands.tui import tui
from madsci.client.cli.commands.version import version
from rich.console import Console

# Version will be loaded dynamically
__version__ = "0.6.2"


class AliasedGroup(click.Group):
    """Click group that supports command aliases."""

    _aliases: ClassVar[dict[str, str]] = {
        "n": "new",
        "s": "status",
        "l": "logs",
        "doc": "doctor",
        "val": "validate",
        "ui": "tui",
    }

    def get_command(self, ctx: click.Context, cmd_name: str) -> click.Command | None:
        """Resolve command aliases."""
        # Check if it's an alias
        if cmd_name in self._aliases:
            cmd_name = self._aliases[cmd_name]
        return super().get_command(ctx, cmd_name)

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
        madsci start lab      Start all services
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


# Register commands
madsci.add_command(version)
madsci.add_command(doctor)
madsci.add_command(status)
madsci.add_command(logs)
madsci.add_command(tui)
madsci.add_command(registry)
madsci.add_command(migrate)


def main() -> None:
    """CLI entry point."""
    madsci()


if __name__ == "__main__":
    main()
