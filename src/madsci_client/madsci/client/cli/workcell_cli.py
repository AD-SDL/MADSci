"""Command Line Interface for managing MADSci Squid workcells."""

from pathlib import Path
from typing import Optional

import click
from click import Context
from madsci.client.cli.lab_cli import LabContext, find_lab
from madsci.common.types.workcell_types import WorkcellDefinition, WorkcellLink
from madsci.common.utils import (
    prompt_for_input,
    prompt_yes_no,
    save_model,
    search_for_file_pattern,
    to_snake_case,
)
from rich.console import Console
from rich.pretty import pprint

console = Console()


class WorkcellContext:
    """Context object for workcell commands."""

    def __init__(self) -> None:
        """Initialize the context object."""
        self.workcell: Optional[WorkcellDefinition] = None
        self.path: Optional[Path] = None
        self.lab: Optional[LabContext] = None
        self.quiet: bool = False


pass_workcell = click.make_pass_decorator(WorkcellContext)


def find_workcell(
    name: Optional[str],
    path: Optional[str],
    lab_context: Optional[LabContext] = None,
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
            "*.workcell.yaml",
            start_dir=lab_context.path.parent,
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
def workcell(
    ctx: Context,
    name: Optional[str],
    path: Optional[str],
    lab: Optional[str],
) -> None:
    """Manage workcells. Specify workcell by name or path."""
    lab_context = find_lab(name=lab, path=lab)
    ctx.obj = find_workcell(name=name, path=path, lab_context=lab_context)
    ctx.obj.quiet = ctx.parent.params.get("quiet")


@workcell.command()
@click.option("--name", "-n", type=str, help="The name of the workcell.")
@click.option(
    "--path",
    "-p",
    type=str,
    help="The path to the workcell definition file.",
)
@click.option("--description", "-d", type=str, help="The description of the workcell.")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt.")
@click.pass_context
def create(
    ctx: Context,
    name: Optional[str],
    path: Optional[str],
    description: Optional[str],
    yes: bool,
) -> None:
    """Create a new workcell."""
    name = name if name else ctx.parent.params.get("name")
    name = (
        name
        if name
        else prompt_for_input("Workcell Name", required=True, quiet=ctx.obj.quiet)
    )
    description = (
        description
        if description
        else prompt_for_input("Workcell Description", quiet=ctx.obj.quiet)
    )

    workcell = WorkcellDefinition(name=name, description=description)
    console.print(workcell)

    path = path if path else ctx.parent.params.get("path")
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
            "Path to save Workcell Definition file",
            default=path,
            quiet=ctx.obj.quiet,
        )
        if new_path:
            path = Path(new_path)
    else:
        path = Path(path)

    if not path.expanduser().exists():
        path.expanduser().parent.mkdir(parents=True, exist_ok=True)
    save_model(path, workcell, overwrite_check=not ctx.obj.quiet and not yes)

    if (
        ctx.obj.lab
        and ctx.obj.lab.lab_def
        and (
            yes
            or ctx.obj.quiet
            or prompt_yes_no(
                f"Add workcell to lab [bold]{ctx.obj.lab.lab_def.name}[/] ([italic]{ctx.obj.lab.path}[/])?",
                default="yes",
            )
        )
    ):
        relative_path = path.relative_to(ctx.obj.lab.path.parent)
        if name not in ctx.obj.lab.lab_def.managers:
            ctx.obj.lab.lab_def.managers[name] = WorkcellLink(path=relative_path)
            save_model(ctx.obj.lab.path, ctx.obj.lab.lab_def, overwrite_check=False)


@workcell.command()
@pass_workcell
def list(ctx: WorkcellContext) -> None:
    """List all workcells."""
    search_dir = ctx.lab.path.parent if ctx.lab and ctx.lab.path else None
    workcell_files = search_for_file_pattern("*.workcell.yaml", start_dir=search_dir)

    if workcell_files:
        for workcell_file in sorted(set(workcell_files)):
            workcell = WorkcellDefinition.from_yaml(workcell_file)
            console.print(
                f"[bold]{workcell.name}[/]: {workcell.description} ({workcell_file})",
            )
    else:
        lab_context = " in lab directory" if ctx.lab and ctx.lab.path else ""
        print(  # noqa: T201
            f"No workcell definitions found{lab_context}, you can create one with 'madsci workcell create'",
        )


@workcell.command()
@pass_workcell
def info(ctx: WorkcellContext) -> None:
    """Get information about a workcell."""
    if ctx.workcell:
        pprint(ctx.workcell)
    else:
        print(  # noqa: T201
            "No workcell specified/found, please specify a workcell with --name or --path, or create a new workcell with 'madsci workcell create'",
        )


@workcell.command()
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt.")
@click.option("--name", "-n", type=str, help="The name of the workcell.")
@click.option(
    "--path",
    "-p",
    type=str,
    help="The path to the workcell definition file.",
)
@pass_workcell
def delete(
    ctx: WorkcellContext,
    yes: bool,
    name: Optional[str],
    path: Optional[str],
) -> None:
    """Delete a workcell."""
    if name or path:
        ctx.workcell = find_workcell(name=name, path=None, lab_context=ctx.lab).workcell
    if ctx.workcell and ctx.path:
        console.print(f"Deleting workcell: {ctx.workcell.name} ({ctx.path})")
        if yes or ctx.quiet or prompt_yes_no("Are you sure?", default="no"):
            ctx.path.unlink()
            console.print(f"Deleted {ctx.path}")
            if (
                (ctx.lab and ctx.lab.lab_def and yes)
                or ctx.quiet
                or prompt_yes_no(
                    f"Remove from lab [bold]{ctx.lab.lab_def.name}[/] ([italic]{ctx.lab.path}[/])?",
                    default="yes",
                )
            ) and ctx.workcell.name in ctx.lab.lab_def.managers:
                del ctx.lab.lab_def.managers[ctx.workcell.name]
                save_model(ctx.lab.path, ctx.lab.lab_def, overwrite_check=False)
    else:
        print(  # noqa: T201
            "No workcell specified/found, please specify a workcell with --name or --path, or create a new workcell with 'madsci workcell create'",
        )


@workcell.command()
@pass_workcell
def validate(ctx: WorkcellContext) -> None:
    """Validate a workcell definition file."""
    if ctx.workcell:
        console.print(ctx.workcell)
        return
    console.print(
        "No workcell specified, please specify a workcell with --name or --path, or create a new workcell with 'madsci workcell create'",
    )
    return
