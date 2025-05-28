"""Command Line Interface for the MADSci client."""

import click
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


if __name__ == "__main__":
    tui(root_cli, auto_envvar_prefix="MADSCI_CLI_")
