"""Command Line Interface for managing MADSci Squid managers."""

from pathlib import Path
from typing import Optional

import click
from click.core import Context
from madsci.common.types.squid_types import (
    LabDefinition,
    ManagerDefinition,
    ManagerType,
)
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


class ManagerContext:
    """Context object for manager commands."""

    def __init__(self) -> None:
        """Initialize the context object."""
        self.manager_def: Optional[ManagerDefinition] = None
        self.lab_def: Optional[LabDefinition] = None
        self.path: Optional[Path] = None
        self.quiet: bool = False


pass_manager = click.make_pass_decorator(ManagerContext)


def find_manager(name: Optional[str], path: Optional[str]) -> ManagerContext:
    """Find a manager by name or path."""
    manager_context = ManagerContext()

    if path:
        manager_context.path = Path(path)
        if manager_context.path.exists():
            manager_context.manager_def = ManagerDefinition.from_yaml(path)
            return manager_context

    if name:
        lab_files = search_for_file_pattern("*.lab.yaml")
        for lab_file in lab_files:
            lab_def = LabDefinition.from_yaml(lab_file)
            for manager_name, manager in lab_def.managers.items():
                if manager_name == name:
                    manager_context.path = Path(lab_file)
                    manager_context.lab_def = lab_def
                    manager_context.manager_def = (
                        manager
                        if isinstance(manager, ManagerDefinition)
                        else ManagerDefinition.from_yaml(manager)
                    )
                    return manager_context

    # * Search for any manager file
    manager_files = search_for_file_pattern("*.manager.yaml")
    if manager_files:
        manager_context.path = Path(manager_files[0])
        manager_context.manager_def = ManagerDefinition.from_yaml(manager_files[0])

    return manager_context


@click.group()
@click.option("--name", "-n", type=str, help="The name of the manager to operate on.")
@click.option("--path", "-p", type=str, help="The path to the manager definition file.")
@click.pass_context
def manager(ctx: Context, name: Optional[str], path: Optional[str]) -> None:
    """Manage managers."""
    ctx.obj = find_manager(name, path)
    ctx.obj.quiet = ctx.parent.params.get("quiet")


@manager.command(name="add")
@click.option("--name", "-n", type=str, help="The name of the manager.", required=False)
@click.option("--path", "-p", type=str, help="The path to the manager definition file.")
@click.option("--description", "-d", type=str, help="The description of the manager.")
@click.option(
    "--type",
    "-t",
    type=click.Choice([e.value for e in ManagerType]),
    help="The type of the manager.",
    required=True,
)
@click.pass_context
def add(
    ctx: Context,
    name: Optional[str],
    path: Optional[str],
    description: Optional[str],
    type: str,
) -> None:
    """Add a new manager."""
    if not name:
        name = ctx.parent.params.get("name")
    if not name:
        name = prompt_for_input("Manager Name", required=True, quiet=ctx.obj.quiet)
    if not description:
        description = prompt_for_input("Manager Description", quiet=ctx.obj.quiet)

    manager_definition = ManagerDefinition(
        name=name, description=description, manager_type=type
    )
    console.print(manager_definition)

    if ctx.obj.lab_def:
        ctx.obj.lab_def.managers[name] = manager_definition
        save_model(ctx.obj.path, ctx.obj.lab_def, overwrite_check=not ctx.obj.quiet)
    else:
        if not path:
            path = ctx.parent.params.get("path")
        if not path:
            default_path = Path.cwd() / f"{to_snake_case(name)}.manager.yaml"
            new_path = prompt_for_input(
                "Path to save Manager Definition file",
                default=str(default_path),
                quiet=ctx.obj.quiet,
            )
            if new_path:
                path = Path(new_path)
        print("Path:", path)
        save_model(
            path=path, model=manager_definition, overwrite_check=not ctx.obj.quiet
        )


@manager.command()
def list() -> None:
    """List all managers. Will list all managers in the current directory, subdirectories, and parent directories."""
    manager_files = search_for_file_pattern("*.manager.yaml")

    if manager_files:
        for manager_file in sorted(set(manager_files)):
            manager_definition = ManagerDefinition.from_yaml(manager_file)
            console.print(
                f"[bold]{manager_definition.name}[/]: {manager_definition.description} ({manager_file})",
            )
    else:
        lab_files = search_for_file_pattern("*.lab.yaml")
        for lab_file in lab_files:
            lab_def = LabDefinition.from_yaml(lab_file)
            for _, manager in lab_def.managers.items():
                manager_definition = (
                    manager
                    if isinstance(manager, ManagerDefinition)
                    else ManagerDefinition.from_yaml(manager)
                )
                console.print(
                    f"[bold]{manager_definition.name}[/]: {manager_definition.description} (defined in {lab_file})",
                )


@manager.command()
@pass_manager
def info(ctx: ManagerContext) -> None:
    """Get information about a manager."""
    if ctx.manager_def:
        pprint(ctx.manager_def)
    else:
        console.print(
            "No manager found. Specify manager by name or path. If you don't have a manager file, you can create one with 'madsci manager create'.",
        )


@manager.command()
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt.")
@pass_manager
def delete(ctx: ManagerContext, yes: bool) -> None:
    """Delete a manager."""
    if ctx.manager_def and ctx.path:
        console.print(f"Deleting manager: {ctx.manager_def.name} ({ctx.path})")
        if yes or ctx.quiet or prompt_yes_no("Are you sure?"):
            if ctx.obj.lab_def:
                del ctx.obj.lab_def.managers[ctx.manager_def.name]
                save_model(
                    ctx.obj.path, ctx.obj.lab_def, overwrite_check=not ctx.obj.quiet
                )
            else:
                ctx.path.unlink()
            console.print(f"Deleted {ctx.path}")
    else:
        console.print(
            "No manager found. Specify manager by name or path. If you don't have a manager file, you can create one with 'madsci manager create'.",
        )


@manager.command()
@pass_manager
def validate(ctx: ManagerContext) -> None:
    """Validate a manager definition file."""
    if ctx.manager_def:
        console.print(ctx.manager_def)
    else:
        console.print(
            "No manager found. Specify manager by name or path. If you don't have a manager definition file, you can create one with 'madsci manager create'.",
        )
