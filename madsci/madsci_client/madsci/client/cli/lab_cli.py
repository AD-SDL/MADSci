"""Command Line Interface for managing MADSci Squid labs."""

import os
from pathlib import Path
from typing import Optional

import click
from rich import print
from rich.console import Console
from rich.pretty import pprint

from madsci.common.types.squid_types import LabDefinition
from madsci.common.utils import search_up_and_down_for_pattern, to_snake_case

console = Console()


@click.group()
def lab():
    """Manage labs."""
    pass


@lab.command()
@click.option(
    "--name", "-n", type=str, help="The name of the lab to create. (Optional)"
)
@click.option(
    "--description", "-d", type=str, help="The description of the lab. (Optional)"
)
@click.option(
    "--path",
    "-p",
    type=str,
    help="The location to create the lab definition in. (Optional)",
)
def create(name: Optional[str], description: Optional[str], path: Optional[str]):
    """Create a new lab."""
    if not name:
        name = console.input("Name: ")
    if not description:
        description = console.input("Description (optional): ")
    lab_definition = LabDefinition(name=name, description=description)
    console.print(lab_definition)
    if not path:
        path = Path.cwd() / f"{to_snake_case(name)}.lab.yaml"
        new_path = console.input(f"Path (default: {path}): ")
        if new_path:
            path = Path(new_path)
    if not path.exists():
        lab_definition.to_yaml(path)
    else:
        console.print(f"Lab definition file already exists: [bold]{path}[/]")
        if console.input(r"Overwrite? \[y/n] ") == "y":
            lab_definition.to_yaml(path)


@lab.command()
def list():
    """List all labs. Will list all labs in the current directory, subdirectories, and parent directories."""

    # Search for .lab.yaml files in current dir and subdirs
    lab_files = search_up_and_down_for_pattern("*.lab.yaml")

    if lab_files:
        for lab_file in sorted(set(lab_files)):
            lab_definition = LabDefinition.from_yaml(lab_file)
            console.print(
                f"[bold]{lab_definition.name}[/]: {lab_definition.description} ({lab_file})"
            )
    else:
        print("No lab definitions found")


@lab.command()
@click.argument("name", type=str, required=False)
@click.option(
    "--path",
    "-p",
    type=str,
    help="The path to the lab definition (Required if name is not provided).",
)
def info(name: Optional[str], path: Optional[str]):
    """Get information about a lab. Either provide a name or a path to the lab definition. If both are provided, the name will be ignored. If there are multiple labs with the same name, all will be listed."""
    if path:
        lab_definition = LabDefinition.from_yaml(path)
        pprint(lab_definition)
        return

    if name:
        # Search for .lab.yaml files in current dir and subdirs
        lab_files = search_up_and_down_for_pattern("*.lab.yaml")
        for lab_file in lab_files:
            lab_definition = LabDefinition.from_yaml(lab_file)
            if lab_definition.name == name:
                pprint(lab_definition)

    if not name and not path:
        ctx = click.get_current_context()
        click.echo(ctx.get_help())
        ctx.exit()


@lab.command()
@click.argument("name", type=str, required=False)
@click.option(
    "--path",
    "-p",
    type=str,
    help="The path to the lab definition (Required if name is not provided).",
)
def delete(name: Optional[str], path: Optional[str]):
    """Delete a lab. Either provide a name or a path to the lab definition. If both are provided, the name will be ignored. If there are multiple labs with the same name, you will be prompted to confirm deletion of each of them."""
    if path:
        lab_definition = LabDefinition.from_yaml(path)
        console.print(f"Deleting lab: {lab_definition.name} ({path})")
        if console.input(r"Are you sure? \[y/n] ") == "y":
            Path(path).unlink()
            console.print(f"Deleted {path}")
        return

    if name:
        # Search for .lab.yaml files in current dir and subdirs
        lab_files = search_up_and_down_for_pattern("*.lab.yaml")
        found = False
        for lab_file in lab_files:
            lab_definition = LabDefinition.from_yaml(lab_file)
            if lab_definition.name == name:
                found = True
                console.print(f"Deleting lab: {lab_definition.name} ({lab_file})")
                if console.input(r"Are you sure? \[y/n] ") == "y":
                    Path(lab_file).unlink()
                    console.print(f"Deleted {lab_file}")
        if not found:
            console.print(f"No lab definition found for [bold]{name}[/]")

    if not name and not path:
        ctx = click.get_current_context()
        click.echo(ctx.get_help())
        ctx.exit()


@lab.command()
@click.argument("name", type=str, required=False)
@click.option("--path", "-p", type=str, help="The path to the lab definition.")
def validate(name: Optional[str], path: Optional[str]):
    """Validate a lab definition file by name or path. If no name or path is provided, will search for .lab.yaml files in the current file tree."""

    if path:
        lab_definition = LabDefinition.from_yaml(path)
        console.print(lab_definition)
        return

    if name:
        # *Search for .lab.yaml files in current dir and subdirs
        lab_files = search_up_and_down_for_pattern("*.lab.yaml")
        for lab_file in lab_files:
            lab_definition = LabDefinition.from_yaml(lab_file)
            if lab_definition.name == name:
                console.print(lab_definition)
                return

        console.print(f"No lab definition found for [bold]{name}[/]")
        return

    if not name and not path:
        console.print(
            "No lab file specified, searching for .lab.yaml files in current file tree..."
        )

        lab_files = search_up_and_down_for_pattern("*.lab.yaml")
        for lab_file in lab_files:
            console.print(f"Validating {lab_file}...")
            lab_definition = LabDefinition.from_yaml(lab_file)
            console.print(lab_definition)
    return


def run_command(command: str, lab_definition: LabDefinition, path: Optional[str]):
    """Run a command in a lab."""
    console.print(
        f"Running command: [bold]{command}[/] ({lab_definition.commands[command]}) in lab: [bold]{lab_definition.name}[/] ({path})"
    )
    print(os.popen(lab_definition.commands[command]).read())


@lab.command()
@click.argument("command", type=str)
@click.option("--path", "-p", type=str, help="The path to the lab definition.")
@click.option("--name", "-n", type=str, help="The name of the lab.")
def run(command: str, path: Optional[str], name: Optional[str]):
    """Run a command in a lab. Either provide a name or a path to the lab definition. If both are provided, the name will be ignored. If no name or path is provided, will search for .lab.yaml files in the current file tree and run the command in the first one found."""

    if path:
        lab_definition = LabDefinition.from_yaml(path)
        if lab_definition.commands.get(command):
            run_command(command, lab_definition, path)
            return
        else:
            console.print(
                f"Command [bold]{command}[/] not found in lab definition: [bold]{lab_definition.name}[/] ({path})"
            )
            return

    if name:
        # Search for .lab.yaml files in current dir and subdirs
        lab_files = search_up_and_down_for_pattern("*.lab.yaml")
        for lab_file in lab_files:
            lab_definition = LabDefinition.from_yaml(lab_file)
            if lab_definition.name == name:
                if lab_definition.commands.get(command):
                    run_command(command, lab_definition, lab_file)
                else:
                    console.print(
                        f"Command [bold]{command}[/] not found in lab definition: [bold]{lab_definition.name}[/] ({lab_file})"
                    )

        console.print(f"No lab definition found for [bold]{name}[/]")
        return

    if not name and not path:
        console.print(
            "No lab file specified, searching for .lab.yaml files in current file tree..."
        )

        lab_files = search_up_and_down_for_pattern("*.lab.yaml")
        for lab_file in lab_files:
            lab_definition = LabDefinition.from_yaml(lab_file)
            if lab_definition.commands.get(command):
                run_command(command, lab_definition, lab_file)
                return
            else:
                console.print(
                    f"Command [bold]{command}[/] not found in lab definition: [bold]{lab_definition.name}[/] ({lab_file})"
                )
                return

        console.print(
            f"No lab definition file found to run command: [bold]{command}[/]"
        )
        return
