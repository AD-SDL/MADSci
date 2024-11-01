"""Command Line Interface for managing MADSci Squid workcells."""

from pathlib import Path
from typing import Optional

import click
from rich import print
from rich.console import Console
from rich.pretty import pprint

from madsci.common.types.workcell_types import Workcell
from madsci.common.utils import search_up_and_down_for_pattern, to_snake_case

console = Console()


@click.group()
def workcell():
    """Manage workcells."""
    pass


@workcell.command()
@click.option(
    "--name", "-n", type=str, help="The name of the workcell to create. (Optional)"
)
@click.option(
    "--description", "-d", type=str, help="The description of the workcell. (Optional)"
)
@click.option(
    "--path",
    "-p",
    type=str,
    help="The location to create the workcell definition in. (Optional)",
)
def create(name: Optional[str], description: Optional[str], path: Optional[str]):
    """Create a new workcell."""
    if not name:
        name = console.input("Name: ")
    if not description:
        description = console.input("Description (optional): ")
    workcell = Workcell(name=name, description=description)
    console.print(workcell)
    if not path:
        current_path = Path.cwd()
        if current_path.name == "workcells":
            path = current_path / f"{to_snake_case(name)}.workcell.yaml"
        else:
            path = current_path / "workcells" / f"{to_snake_case(name)}.workcell.yaml"
        new_path = console.input(f"Path (default: {path}): ")
        if new_path:
            path = Path(new_path)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        workcell.to_yaml(path)
    else:
        console.print(f"Workcell definition file already exists: [bold]{path}[/]")
        if console.input(r"Overwrite? \[y/n] ") == "y":
            workcell.to_yaml(path)


@workcell.command()
def list():
    """List all workcells. Will list all workcells in the current directory, subdirectories, and parent directories."""
    workcell_files = search_up_and_down_for_pattern("*.workcell.yaml")

    if workcell_files:
        for workcell_file in sorted(set(workcell_files)):
            workcell = Workcell.from_yaml(workcell_file)
            console.print(
                f"[bold]{workcell.name}[/]: {workcell.description} ({workcell_file})"
            )
    else:
        print("No workcell definitions found")


@workcell.command()
@click.argument("name", type=str, required=False)
@click.option(
    "--path",
    "-p",
    type=str,
    help="The path to the workcell definition (Required if name is not provided).",
)
def info(name: Optional[str], path: Optional[str]):
    """Get information about a workcell. Either provide a name or a path to the workcell definition."""
    if path:
        workcell = Workcell.from_yaml(path)
        pprint(workcell)
        return

    if name:
        workcell_files = search_up_and_down_for_pattern("*.workcell.yaml")
        for workcell_file in workcell_files:
            workcell = Workcell.from_yaml(workcell_file)
            if workcell.name == name:
                pprint(workcell)

    if not name and not path:
        ctx = click.get_current_context()
        click.echo(ctx.get_help())
        ctx.exit()


@workcell.command()
@click.argument("name", type=str, required=False)
@click.option(
    "--path",
    "-p",
    type=str,
    help="The path to the workcell definition (Required if name is not provided).",
)
def delete(name: Optional[str], path: Optional[str]):
    """Delete a workcell. Either provide a name or a path to the workcell definition."""
    if path:
        workcell = Workcell.from_yaml(path)
        console.print(f"Deleting workcell: {workcell.name} ({path})")
        if console.input(r"Are you sure? \[y/n] ") == "y":
            Path(path).unlink()
            console.print(f"Deleted {path}")
        return

    if name:
        workcell_files = search_up_and_down_for_pattern("*.workcell.yaml")
        found = False
        for workcell_file in workcell_files:
            workcell = Workcell.from_yaml(workcell_file)
            if workcell.name == name:
                console.print(f"Deleting workcell: {workcell.name} ({workcell_file})")
                if console.input(r"Are you sure? \[y/n] ") == "y":
                    Path(workcell_file).unlink()
                    console.print(f"Deleted {workcell_file}")
                    found = True
        if not found:
            console.print(f"No workcell definition found for [bold]{name}[/]")

    if not name and not path:
        ctx = click.get_current_context()
        click.echo(ctx.get_help())
        ctx.exit()


@workcell.command()
@click.argument("name", type=str, required=False)
@click.option("--path", "-p", type=str, help="The path to the workcell definition.")
def validate(name: Optional[str], path: Optional[str]):
    """Validate a workcell definition file by name or path."""
    if path:
        workcell = Workcell.from_yaml(path)
        console.print(workcell)
        return

    if name:
        workcell_files = search_up_and_down_for_pattern("*.workcell.yaml")
        for workcell_file in workcell_files:
            workcell = Workcell.from_yaml(workcell_file)
            if workcell.name == name:
                console.print(workcell)
                return

        console.print(f"No workcell definition found for [bold]{name}[/]")
        return

    if not name and not path:
        console.print(
            "No workcell file specified, searching for .workcell.yaml files in current file tree..."
        )

        workcell_files = search_up_and_down_for_pattern("*.workcell.yaml")
        for workcell_file in workcell_files:
            console.print(f"Validating {workcell_file}...")
            workcell = Workcell.from_yaml(workcell_file)
            console.print(workcell)
    return
