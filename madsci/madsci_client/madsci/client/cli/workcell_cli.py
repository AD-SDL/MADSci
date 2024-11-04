"""Command Line Interface for managing MADSci Squid workcells."""

from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.pretty import pprint

from madsci.client.cli.lab_cli import LabContext, find_lab
from madsci.common.types.workcell_types import WorkcellDefinition
from madsci.common.utils import (
    prompt_for_input,
    prompt_yes_no,
    save_model,
    search_for_file_pattern,
    to_snake_case,
)

console = Console()


class WorkcellContext:
    """Context object for workcell commands."""

    def __init__(self):
        """Initialize the context object."""
        self.workcell: Optional[WorkcellDefinition] = None
        self.path: Optional[Path] = None
        self.lab: Optional[LabContext] = None


pass_workcell = click.make_pass_decorator(WorkcellContext)


def find_workcell(
    name: Optional[str], path: Optional[str], lab_context: Optional[LabContext] = None
) -> WorkcellContext:
    """Find a workcell by name or path."""
    workcell_context = WorkcellContext()
    workcell_context.lab = lab_context

    if path:
        workcell_context.path = Path(path)
        if workcell_context.path.exists():
            workcell_context.workcell = WorkcellDefinition.from_yaml(path)
            return workcell_context

    # If we have a lab context, search in the lab directory first
    if lab_context and lab_context.path:
        workcell_files = search_for_file_pattern(
            "*.workcell.yaml", start_dir=lab_context.path.parent
        )
        for workcell_file in workcell_files:
            workcell = WorkcellDefinition.from_yaml(workcell_file)
            if not name or workcell.name == name:
                workcell_context.path = Path(workcell_file)
                workcell_context.workcell = workcell
                return workcell_context

    # If not found in lab directory or no lab context, search everywhere
    workcell_files = search_for_file_pattern("*.workcell.yaml")
    for workcell_file in workcell_files:
        workcell = WorkcellDefinition.from_yaml(workcell_file)
        if not name or workcell.name == name:
            workcell_context.path = Path(workcell_file)
            workcell_context.workcell = workcell
            return workcell_context

    return workcell_context


@click.group()
@click.option("--name", "-n", type=str, help="Name of the workcell.")
@click.option("--path", "-p", type=str, help="Path to the workcell definition file.")
@click.option("--lab", "-l", type=str, help="Name or path of the lab to operate in.")
@click.pass_context
def workcell(ctx, name: Optional[str], path: Optional[str], lab: Optional[str]):
    """Manage workcells. Specify workcell by name or path."""
    lab_context = find_lab(name=lab, path=lab)
    ctx.obj = find_workcell(name=name, path=path, lab_context=lab_context)


@workcell.command()
@click.option("--description", "-d", type=str, help="The description of the workcell.")
@click.pass_context
def create(ctx, description: Optional[str]):
    """Create a new workcell."""
    name = ctx.parent.params.get("name")
    if not name:
        name = prompt_for_input("Workcell Name", required=True)
    if not description:
        description = prompt_for_input("Workcell Description")

    workcell = WorkcellDefinition(name=name, description=description)
    console.print(workcell)

    path = ctx.parent.params.get("path")
    if not path:
        if ctx.obj.lab and ctx.obj.lab.path:
            # If we have a lab context, create in the lab directory
            path = (
                ctx.obj.lab.path.parent
                / "workcells"
                / f"{to_snake_case(name)}.workcell.yaml"
            )
        else:
            current_path = Path.cwd()
            if current_path.name == "workcells":
                path = current_path / f"{to_snake_case(name)}.workcell.yaml"
            else:
                path = (
                    current_path / "workcells" / f"{to_snake_case(name)}.workcell.yaml"
                )

        new_path = prompt_for_input(
            "Path to save Workcell Definition file", default=path
        )
        if new_path:
            path = Path(new_path)
    else:
        path = Path(path)

    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
    save_model(path, workcell)

    if ctx.obj.lab and ctx.obj.lab.lab_def:
        if prompt_yes_no(
            f"Add workcell to lab [bold]{ctx.obj.lab.lab_def.name}[/] ([italic]{ctx.obj.lab.path}[/])?",
            default="yes",
        ):
            ctx.obj.lab.lab_def.workcells.append(
                path.relative_to(ctx.obj.lab.path.parent)
            )
            save_model(ctx.obj.lab.path, ctx.obj.lab.lab_def, overwrite_check=False)


@workcell.command()
@pass_workcell
def list(ctx: WorkcellContext):
    """List all workcells."""
    search_dir = ctx.lab.path.parent if ctx.lab and ctx.lab.path else None
    workcell_files = search_for_file_pattern("*.workcell.yaml", start_dir=search_dir)

    if workcell_files:
        for workcell_file in sorted(set(workcell_files)):
            workcell = WorkcellDefinition.from_yaml(workcell_file)
            console.print(
                f"[bold]{workcell.name}[/]: {workcell.description} ({workcell_file})"
            )
    else:
        lab_context = " in lab directory" if ctx.lab and ctx.lab.path else ""
        print(f"No workcell definitions found{lab_context}")


@workcell.command()
@pass_workcell
def info(ctx: WorkcellContext):
    """Get information about a workcell."""
    if ctx.workcell:
        pprint(ctx.workcell)
    else:
        print(
            "No workcell specified/found, please specify a workcell with --name or --path, or create a new workcell with 'madsci workcell create'"
        )


@workcell.command()
@pass_workcell
def delete(ctx: WorkcellContext):
    """Delete a workcell."""
    if ctx.workcell and ctx.path:
        console.print(f"Deleting workcell: {ctx.workcell.name} ({ctx.path})")
        if prompt_yes_no("Are you sure?", default="no"):
            ctx.path.unlink()
            console.print(f"Deleted {ctx.path}")
            if (
                ctx.lab
                and ctx.lab.lab_def
                and prompt_yes_no(
                    f"Remove from lab [bold]{ctx.lab.lab_def.name}[/] ([italic]{ctx.lab.path}[/])?",
                    default="yes",
                )
            ):
                new_workcells = []
                for workcell in ctx.lab.lab_def.workcells:
                    if isinstance(workcell, str) or isinstance(workcell, Path):
                        if Path(workcell).absolute() != ctx.path.absolute():
                            new_workcells.append(workcell)
                    elif isinstance(workcell, WorkcellDefinition):
                        if workcell.name != ctx.workcell.name:
                            new_workcells.append(workcell)
                ctx.lab.lab_def.workcells = new_workcells
                save_model(ctx.lab.path, ctx.lab.lab_def, overwrite_check=False)
    else:
        print(
            "No workcell specified/found, please specify a workcell with --name or --path, or create a new workcell with 'madsci workcell create'"
        )


@workcell.command()
@pass_workcell
def validate(ctx: WorkcellContext):
    """Validate a workcell definition file."""
    if ctx.workcell:
        console.print(ctx.workcell)
        return
    else:
        console.print(
            "No workcell specified, please specify a workcell with --name or --path, or create a new workcell with 'madsci workcell create'"
        )
        return
