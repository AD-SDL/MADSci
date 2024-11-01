"""Command Line Interface for the MADSci client."""

import click
from rich.console import Console
from trogon import tui

from madsci.client.cli.lab_cli import lab
from madsci.client.cli.workcell_cli import workcell

console = Console()


@tui()
@click.group()
def root_cli():
    """MADSci command line interface."""
    pass


@root_cli.command()
def version():
    """Display the MADSci client version."""
    console.print("MADSci Client v0.1.0")


root_cli.add_command(lab)
root_cli.add_command(workcell)

if __name__ == "__main__":
    root_cli()
