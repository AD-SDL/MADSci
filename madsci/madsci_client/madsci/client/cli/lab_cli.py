"""Command Line Interface for managing MADSci Squid labs."""

import os
from pathlib import Path
from typing import Optional

import click
from rich import print
from rich.console import Console
from rich.pretty import pprint

from madsci.common.types.squid_types import LabDefinition
from madsci.common.utils import (
    prompt_for_input,
    prompt_yes_no,
    save_model,
    search_for_file_pattern,
    to_snake_case,
)

console = Console()


class LabContext:
    """Context object for lab commands."""

    def __init__(self):
        """Initialize the context object."""
        self.lab_def: Optional[LabDefinition] = None
        self.path: Optional[Path] = None


pass_lab = click.make_pass_decorator(LabContext)


def find_lab(name: Optional[str], path: Optional[str]) -> LabContext:
    """Find a lab by name or path."""
    lab_context = LabContext()

    if path:
        lab_context.path = Path(path)
        if lab_context.path.exists():
            lab_context.lab_def = LabDefinition.from_yaml(path)
            return lab_context

    if name:
        lab_files = search_for_file_pattern("*.lab.yaml")
        for lab_file in lab_files:
            lab_def = LabDefinition.from_yaml(lab_file)
            if lab_def.name == name:
                lab_context.path = Path(lab_file)
                lab_context.lab_def = lab_def
                return lab_context

    # * Search for any lab file
    lab_files = search_for_file_pattern("*.lab.yaml")
    if lab_files:
        lab_context.path = Path(lab_files[0])
        lab_context.lab_def = LabDefinition.from_yaml(lab_files[0])

    return lab_context


@click.group()
@click.option("--name", "-n", type=str, help="The name of the lab to operate on.")
@click.option("--path", "-p", type=str, help="The path to the lab definition file.")
@click.pass_context
def lab(ctx, name: Optional[str], path: Optional[str]):
    """Manage labs."""
    ctx.obj = find_lab(name, path)


@lab.command()
@click.option("--description", "-d", type=str, help="The description of the lab.")
@click.pass_context
def create(ctx, description: Optional[str]):
    """Create a new lab."""
    name = ctx.parent.params.get("name")
    if not name:
        name = prompt_for_input("Lab Name", required=True)
    if not description:
        description = prompt_for_input("Lab Description")

    lab_definition = LabDefinition(name=name, description=description)
    console.print(lab_definition)

    path = ctx.parent.params.get("path")
    if not path:
        default_path = Path.cwd() / f"{to_snake_case(name)}.lab.yaml"
        new_path = prompt_for_input(
            "Path to save Lab Definition file", default=str(default_path)
        )
        if new_path:
            path = Path(new_path)
    save_model(path=path, model=lab_definition)


@lab.command()
def list():
    """List all labs. Will list all labs in the current directory, subdirectories, and parent directories."""
    lab_files = search_for_file_pattern("*.lab.yaml")

    if lab_files:
        for lab_file in sorted(set(lab_files)):
            lab_definition = LabDefinition.from_yaml(lab_file)
            console.print(
                f"[bold]{lab_definition.name}[/]: {lab_definition.description} ({lab_file})"
            )
    else:
        print("No lab definitions found")


@lab.command()
@pass_lab
def info(ctx: LabContext):
    """Get information about a lab."""
    if ctx.lab_def:
        pprint(ctx.lab_def)
    else:
        console.print(
            "No lab found. Specify lab by name or path. If you don't have a lab file, you can create one with 'madsci lab create'."
        )


@lab.command()
@pass_lab
def delete(ctx: LabContext):
    """Delete a lab."""
    if ctx.lab_def and ctx.path:
        console.print(f"Deleting lab: {ctx.lab_def.name} ({ctx.path})")
        if prompt_yes_no("Are you sure?"):
            ctx.path.unlink()
            console.print(f"Deleted {ctx.path}")
    else:
        console.print(
            "No lab found. Specify lab by name or path. If you don't have a lab file, you can create one with 'madsci lab create'."
        )


@lab.command()
@pass_lab
def validate(ctx: LabContext):
    """Validate a lab definition file."""
    if ctx.lab_def:
        console.print(ctx.lab_def)
    else:
        console.print(
            "No lab found. Specify lab by name or path. If you don't have a lab definition file, you can create one with 'madsci lab create'."
        )


def run_command(command: str, lab: LabDefinition, path: Path):
    """Run a command in a lab."""
    console.print(
        f"Running command: [bold]{command}[/] ({lab.commands[command]}) in lab: [bold]{lab.name}[/] ({path})"
    )
    print(os.popen(lab.commands[command]).read())


@lab.command()
@click.argument("command", type=str)
@pass_lab
def run(ctx: LabContext, command: str):
    """Run a command in a lab."""
    if not ctx.lab_def:
        console.print(
            "No lab found. Specify lab by name or path. If you don't have a lab file, you can create one with 'madsci lab create'."
        )
        return

    if ctx.lab_def.commands.get(command):
        run_command(command, ctx.lab_def, ctx.path)
    else:
        console.print(
            f"Command [bold]{command}[/] not found in lab definition: [bold]{ctx.lab_def.name}[/] ({ctx.path})"
        )
