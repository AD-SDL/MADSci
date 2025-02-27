"""Command Line Interface for managing MADSci Squid labs."""

import os
import shlex
from pathlib import Path
from typing import Optional

import click
from click.core import Context
from madsci.common.types.lab_types import LabDefinition
from madsci.common.utils import (
    prompt_for_input,
    prompt_yes_no,
    save_model,
    search_for_file_pattern,
    to_snake_case,
)
from rich import print
from rich.console import Console
from rich.pretty import pprint

console = Console()


class LabContext:
    """Context object for lab commands."""

    def __init__(self) -> None:
        """Initialize the context object."""
        self.lab_def: Optional[LabDefinition] = None
        self.path: Optional[Path] = None
        self.quiet: bool = False


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
def lab(ctx: Context, name: Optional[str], path: Optional[str]) -> None:
    """Manage labs."""
    ctx.obj = find_lab(name, path)
    ctx.obj.quiet = ctx.parent.params.get("quiet")


@lab.command()
@click.option("--name", "-n", type=str, help="The name of the lab.", required=False)
@click.option("--path", "-p", type=str, help="The path to the lab definition file.")
@click.option("--description", "-d", type=str, help="The description of the lab.")
@click.pass_context
def create(
    ctx: Context,
    name: Optional[str],
    path: Optional[str],
    description: Optional[str],
) -> None:
    """Create a new lab."""
    if not name:
        name = ctx.parent.params.get("name")
    if not name:
        name = prompt_for_input("Lab Name", required=True, quiet=ctx.obj.quiet)
    if not description:
        description = prompt_for_input("Lab Description", quiet=ctx.obj.quiet)

    lab_definition = LabDefinition(name=name, description=description)
    console.print(lab_definition)

    if not path:
        path = ctx.parent.params.get("path")
    if not path:
        default_path = Path.cwd() / f"{to_snake_case(name)}.lab.yaml"
        new_path = prompt_for_input(
            "Path to save Lab Definition file",
            default=str(default_path),
            quiet=ctx.obj.quiet,
        )
        if new_path:
            path = Path(new_path)
    print("Path:", path)
    save_model(path=path, model=lab_definition, overwrite_check=not ctx.obj.quiet)


@lab.command()
def list() -> None:
    """List all labs. Will list all labs in the current directory, subdirectories, and parent directories."""
    lab_files = search_for_file_pattern("*.lab.yaml")

    if lab_files:
        for lab_file in sorted(set(lab_files)):
            lab_definition = LabDefinition.from_yaml(lab_file)
            console.print(
                f"[bold]{lab_definition.name}[/]: {lab_definition.description} ({lab_file})",
            )
    else:
        print("No lab definitions found")


@lab.command()
@pass_lab
def info(ctx: LabContext) -> None:
    """Get information about a lab."""
    if ctx.lab_def:
        pprint(ctx.lab_def)
    else:
        console.print(
            "No lab found. Specify lab by name or path. If you don't have a lab file, you can create one with 'madsci lab create'.",
        )


@lab.command()
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt.")
@pass_lab
def delete(ctx: LabContext, yes: bool) -> None:
    """Delete a lab."""
    if ctx.lab_def and ctx.path:
        console.print(f"Deleting lab: {ctx.lab_def.name} ({ctx.path})")
        if yes or ctx.quiet or prompt_yes_no("Are you sure?"):
            ctx.path.unlink()
            console.print(f"Deleted {ctx.path}")
    else:
        console.print(
            "No lab found. Specify lab by name or path. If you don't have a lab file, you can create one with 'madsci lab create'.",
        )


@lab.command()
@pass_lab
def validate(ctx: LabContext) -> None:
    """Validate a lab definition file."""
    if ctx.lab_def:
        console.print(ctx.lab_def)
    else:
        console.print(
            "No lab found. Specify lab by name or path. If you don't have a lab definition file, you can create one with 'madsci lab create'.",
        )


def run_command(command: str, lab: LabDefinition, path: Path) -> None:
    """Run a command in a lab."""
    console.print(
        f"Running command: [bold]{command}[/] ({lab.commands[command]}) in lab: [bold]{lab.name}[/] ({path})",
    )
    args = shlex.split(lab.commands[command])
    os.execvp(args[0], args)  # noqa: S606


@lab.command()
@click.argument("command", type=str)
@pass_lab
def run(ctx: LabContext, command: str) -> None:
    """Run a command in a lab."""
    if not ctx.lab_def:
        console.print(
            "No lab found. Specify lab by name or path. If you don't have a lab file, you can create one with 'madsci lab create'.",
        )
        return

    if ctx.lab_def.commands.get(command):
        run_command(command, ctx.lab_def, ctx.path)
    else:
        console.print(
            f"Command [bold]{command}[/] not found in lab definition: [bold]{ctx.lab_def.name}[/] ({ctx.path})",
        )


@lab.command()
@click.option("--command_name", "--name", "-n", type=str, required=False)
@click.option("--command", "-c", type=str, required=False)
@pass_lab
def add_command(ctx: LabContext, command_name: str, command: str) -> None:
    """Add a command to a lab definition."""
    if not ctx.lab_def:
        console.print(
            "No lab found. Specify lab by name or path. If you don't have a lab file, you can create one with 'madsci lab create'.",
        )
        return

    if not command_name:
        command_name = prompt_for_input("Command Name", required=True)
    if not command:
        command = prompt_for_input("Command", required=True)

    if command_name in ctx.lab_def.commands:
        console.print(
            f"Command [bold]{command_name}[/] already exists in lab definition: [bold]{ctx.lab_def.name}[/] ({ctx.path})",
        )
        if not prompt_yes_no("Do you want to overwrite it?", default="no"):
            return

    ctx.lab_def.commands[command_name] = command
    save_model(ctx.path, ctx.lab_def, overwrite_check=False)
    console.print(
        f"Added command [bold]{command_name}[/] to lab: [bold]{ctx.lab_def.name}[/]",
    )


@lab.command()
@click.argument("command_name", type=str, required=False)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt.")
@pass_lab
def delete_command(ctx: LabContext, command_name: str, yes: bool) -> None:
    """Delete a command from a lab definition."""
    if not ctx.lab_def:
        console.print(
            "No lab found. Specify lab by name or path. If you don't have a lab file, you can create one with 'madsci lab create'.",
        )
        return

    if not command_name:
        command_name = prompt_for_input("Command Name", required=True)

    if command_name in ctx.lab_def.commands:
        if (
            yes
            or ctx.quiet
            or prompt_yes_no(
                f"Are you sure you want to delete command [bold]{command_name}[/]?",
                default="no",
            )
        ):
            del ctx.lab_def.commands[command_name]
            save_model(ctx.path, ctx.lab_def, overwrite_check=False)
            console.print(
                f"Deleted command [bold]{command_name}[/] from lab: [bold]{ctx.lab_def.name}[/]",
            )
    else:
        console.print(
            f"Command [bold]{command_name}[/] not found in lab definition: [bold]{ctx.lab_def.name}[/] ({ctx.path})",
        )
