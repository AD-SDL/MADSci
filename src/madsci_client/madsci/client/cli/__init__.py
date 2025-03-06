"""Command Line Interface for the MADSci client."""

import click
from madsci.client.cli.lab_cli import lab
from madsci.client.cli.manager_cli import manager
from madsci.client.cli.node_cli import node
from madsci.client.cli.resources_cli import resource
from madsci.client.cli.workcell_cli import workcell
from rich.console import Console
from trogon import tui

console = Console()


@tui()
@click.group()
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    help="Run in quiet mode, skipping prompts.",
)
def root_cli(quiet: bool = False) -> None:
    """MADSci command line interface."""


@root_cli.command()
def version() -> None:
    """Display the MADSci client version."""
    console.print("MADSci Client v0.1.0")


root_cli.add_command(lab)
root_cli.add_command(workcell)
root_cli.add_command(node)
root_cli.add_command(resource)
root_cli.add_command(manager)

if __name__ == "__main__":
    tui(root_cli, auto_envvar_prefix="MADSCI_CLI_")
