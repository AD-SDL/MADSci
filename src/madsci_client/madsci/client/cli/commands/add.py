"""CLI command for adding components to existing module projects."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from madsci.common.templates.engine import TemplateEngine
    from madsci.common.types.template_types import GeneratedProject

import click
from rich.console import Console

console = Console()


def _load_pyproject(target_dir: Path) -> dict[str, Any] | None:
    """Load and parse pyproject.toml from *target_dir*, returning None on failure."""
    pyproject = target_dir / "pyproject.toml"
    if not pyproject.exists():
        return None
    try:
        import tomllib
    except ModuleNotFoundError:
        import tomli as tomllib  # type: ignore[no-redef]
    try:
        return tomllib.loads(pyproject.read_text())
    except (OSError, tomllib.TOMLDecodeError):
        return None


def detect_module_name(
    target_dir: Path, data: dict[str, Any] | None = None
) -> str | None:
    """Detect module_name from pyproject.toml in target_dir."""
    if data is None:
        data = _load_pyproject(target_dir)
    if data is None:
        return None
    name = data.get("project", {}).get("name", "")
    for suffix in ["-module", "_module", "-node", "_node"]:
        if name.endswith(suffix):
            name = name.removesuffix(suffix)
            break
    return name.replace("-", "_") or None


def detect_module_description(
    target_dir: Path, data: dict[str, Any] | None = None
) -> str | None:
    """Detect module description from pyproject.toml in target_dir."""
    if data is None:
        data = _load_pyproject(target_dir)
    if data is None:
        return None
    return data.get("project", {}).get("description") or None


def _resolve_context(ctx: click.Context) -> tuple[Path, str, str]:
    """Resolve target directory, module name, and description from context."""
    target_dir = Path(ctx.obj["directory"]).resolve()
    pyproject_data = _load_pyproject(target_dir)
    name = ctx.obj.get("name")
    if not name:
        name = detect_module_name(target_dir, data=pyproject_data)
    if not name:
        if ctx.obj.get("no_interactive"):
            raise click.UsageError(
                "Could not auto-detect module name. Use --name to specify it."
            )
        name = click.prompt("Module name (could not auto-detect)")
    description = ctx.obj.get("description")
    if not description:
        description = (
            detect_module_description(target_dir, data=pyproject_data)
            or "A MADSci node module"
        )
    return target_dir, name, description


def _load_addon_engine(template_id: str) -> TemplateEngine:
    """Load and return a template engine for the given addon template."""
    from madsci.common.templates.registry import TemplateNotFoundError, TemplateRegistry

    registry = TemplateRegistry()
    try:
        return registry.get_template(template_id)
    except TemplateNotFoundError as exc:
        console.print(f"[red]Template not found: {template_id}[/red]")
        raise SystemExit(1) from exc


def _detect_conflicts(
    dry_result: GeneratedProject,
    on_conflict: str,
) -> tuple[list[Path], list[tuple[Path, Path]], list[Path]]:
    """Identify file conflicts without modifying the filesystem.

    Returns (skipped, will_backup, will_overwrite) where will_backup contains
    (original, planned_backup_path) pairs. Actual backup copies
    are deferred to ``_execute_backups``.
    """
    skipped: list[Path] = []
    will_backup: list[tuple[Path, Path]] = []
    will_overwrite: list[Path] = []
    for file_path in dry_result.files_created:
        if not file_path.exists():
            continue
        if on_conflict == "skip":
            skipped.append(file_path)
        elif on_conflict == "backup":
            backup_path = file_path.with_suffix(file_path.suffix + ".bak")
            will_backup.append((file_path, backup_path))
        elif on_conflict == "overwrite":
            will_overwrite.append(file_path)
    return skipped, will_backup, will_overwrite


def _execute_backups(will_backup: list[tuple[Path, Path]]) -> None:
    """Create backup copies for conflicting files (called after confirmation)."""
    for original, backup_path in will_backup:
        shutil.copy2(original, backup_path)


def _preview_and_confirm(
    dry_result: GeneratedProject,
    target_dir: Path,
    skipped: list[Path],
    backed_up: list[tuple[Path, Path]],
    will_overwrite: list[Path],
) -> bool:
    """Show preview and ask for confirmation. Returns False if cancelled."""
    will_create = [
        f
        for f in dry_result.files_created
        if f not in skipped and f not in will_overwrite
    ]
    if will_create:
        console.print("\n[bold]Files to create:[/bold]")
        for f in will_create:
            console.print(f"  [green]+[/green] {f.relative_to(target_dir)}")
    if will_overwrite:
        console.print("\n[bold]Files to overwrite:[/bold]")
        for f in will_overwrite:
            console.print(f"  [red]![/red] {f.relative_to(target_dir)}")
    if skipped:
        console.print("\n[bold]Files to skip (already exist):[/bold]")
        for f in skipped:
            console.print(f"  [yellow]~[/yellow] {f.relative_to(target_dir)}")
    if backed_up:
        console.print("\n[bold]Files backed up:[/bold]")
        for orig, bak in backed_up:
            console.print(
                f"  [blue]>[/blue] {orig.relative_to(target_dir)} -> {bak.name}"
            )
    return click.confirm("\nProceed?", default=True)


def _render_addon(
    template_id: str,
    target_dir: Path,
    parameters: dict[str, Any],
    on_conflict: str,
    no_interactive: bool,
) -> None:
    """Render an addon template into an existing project directory."""
    from madsci.common.templates.engine import TemplateValidationError

    engine = _load_addon_engine(template_id)

    # Validate parameters
    errors = engine.validate_parameters(parameters)
    if errors:
        console.print("[red]Parameter validation errors:[/red]")
        for error in errors:
            console.print(f"  - {error}")
        raise SystemExit(1)

    # Dry-run to identify files
    try:
        dry_result = engine.render(
            output_dir=target_dir, parameters=parameters, dry_run=True
        )
    except TemplateValidationError as exc:
        console.print(f"[red]Template error: {exc}[/red]")
        raise SystemExit(1) from exc

    # Detect conflicts (no filesystem changes yet)
    skipped, will_backup, will_overwrite = _detect_conflicts(dry_result, on_conflict)

    # Interactive preview
    if (
        not no_interactive
        and dry_result.files_created
        and not _preview_and_confirm(
            dry_result, target_dir, skipped, will_backup, will_overwrite
        )
    ):
        console.print("[yellow]Cancelled.[/yellow]")
        return

    # Now that the user has confirmed, create backup copies
    _execute_backups(will_backup)

    # Filter skipped files without permanently mutating the engine manifest
    original_files = engine.manifest.files
    try:
        if on_conflict == "skip" and skipped:
            skip_rel = {str(f.relative_to(target_dir)) for f in skipped}
            engine.manifest.files = [
                f for f in original_files if f.destination not in skip_rel
            ]

        # Render
        result = engine.render(output_dir=target_dir, parameters=parameters)
    finally:
        engine.manifest.files = original_files

    # Summary
    created_count = len(result.files_created)
    console.print(f"\n[green]Added {created_count} file(s)[/green]")
    if skipped:
        console.print(f"[yellow]Skipped {len(skipped)} existing file(s)[/yellow]")


@click.group()
@click.option("--name", "-n", help="Module name (auto-detected from pyproject.toml).")
@click.option(
    "--description",
    help="Module description (auto-detected from pyproject.toml).",
)
@click.option(
    "--dir",
    "-d",
    "directory",
    default=".",
    type=click.Path(exists=True, file_okay=False),
    help="Target directory (default: current directory).",
)
@click.option(
    "--on-conflict",
    type=click.Choice(["skip", "overwrite", "backup"]),
    default="skip",
    help="How to handle existing files.",
)
@click.option("--no-interactive", is_flag=True, help="Skip interactive prompts.")
@click.pass_context
def add(
    ctx: click.Context,
    name: str | None,
    description: str | None,
    directory: str,
    on_conflict: str,
    no_interactive: bool,
) -> None:
    """Add components to an existing module project.

    Auto-detects module_name and description from pyproject.toml in the
    target directory. Use --name / --description to override.

    Examples:

        madsci add docs

        madsci add notebooks

        madsci add all

        madsci add dev-tools --on-conflict overwrite
    """
    ctx.ensure_object(dict)
    ctx.obj["name"] = name
    ctx.obj["description"] = description
    ctx.obj["directory"] = directory
    ctx.obj["on_conflict"] = on_conflict
    ctx.obj["no_interactive"] = no_interactive


@add.command()
@click.pass_context
def docs(ctx: click.Context) -> None:
    """Add documentation directories (docs/, docs/private/)."""
    target_dir, name, description = _resolve_context(ctx)
    _render_addon(
        "addon/docs",
        target_dir,
        {"module_name": name, "module_description": description},
        ctx.obj["on_conflict"],
        ctx.obj["no_interactive"],
    )


@add.command()
@click.pass_context
def drivers(ctx: click.Context) -> None:
    """Add instrument driver directories (src/drivers/, src/drivers/private/)."""
    target_dir, name, _description = _resolve_context(ctx)
    _render_addon(
        "addon/drivers",
        target_dir,
        {"module_name": name},
        ctx.obj["on_conflict"],
        ctx.obj["no_interactive"],
    )


@add.command()
@click.option("--port", "-p", type=int, default=2000, help="Node port number.")
@click.pass_context
def notebooks(ctx: click.Context, port: int) -> None:
    """Add testing notebooks (interface_testing.ipynb, node_testing.ipynb)."""
    target_dir, name, _description = _resolve_context(ctx)
    _render_addon(
        "addon/notebooks",
        target_dir,
        {"module_name": name, "port": port},
        ctx.obj["on_conflict"],
        ctx.obj["no_interactive"],
    )


@add.command()
@click.pass_context
def gitignore(ctx: click.Context) -> None:
    """Add Python .gitignore with MADSci-specific entries."""
    target_dir, name, _description = _resolve_context(ctx)
    _render_addon(
        "addon/gitignore",
        target_dir,
        {"module_name": name},
        ctx.obj["on_conflict"],
        ctx.obj["no_interactive"],
    )


@add.command()
@click.option("--port", "-p", type=int, default=2000, help="Node port number.")
@click.pass_context
def compose(ctx: click.Context, port: int) -> None:
    """Add Docker Compose file for building and running the node."""
    target_dir, name, _description = _resolve_context(ctx)
    _render_addon(
        "addon/compose",
        target_dir,
        {"module_name": name, "port": port},
        ctx.obj["on_conflict"],
        ctx.obj["no_interactive"],
    )


@add.command("dev-tools")
@click.option("--port", "-p", type=int, default=2000, help="Node port number.")
@click.pass_context
def dev_tools(ctx: click.Context, port: int) -> None:
    """Add developer tooling (pre-commit, ruff config, justfile)."""
    target_dir, name, _description = _resolve_context(ctx)
    _render_addon(
        "addon/dev_tools",
        target_dir,
        {"module_name": name, "port": port, "include_dockerfile": True},
        ctx.obj["on_conflict"],
        ctx.obj["no_interactive"],
    )


@add.command("agent-config")
@click.option(
    "--tool",
    "-t",
    "tools",
    multiple=True,
    type=click.Choice(["claude", "agents"]),
    default=("claude", "agents"),
    help="Which agent tools to configure (default: both).",
)
@click.pass_context
def agent_config(ctx: click.Context, tools: tuple[str, ...]) -> None:
    """Add agentic coding configuration (CLAUDE.md, AGENTS.md, skills)."""
    target_dir, name, description = _resolve_context(ctx)
    _render_addon(
        "addon/agent_config",
        target_dir,
        {
            "module_name": name,
            "module_description": description,
            "include_agent_config": list(tools),
        },
        ctx.obj["on_conflict"],
        ctx.obj["no_interactive"],
    )


@add.command("all")
@click.option("--port", "-p", type=int, default=2000, help="Node port number.")
@click.option(
    "--tool",
    "-t",
    "tools",
    multiple=True,
    type=click.Choice(["claude", "agents"]),
    default=("claude", "agents"),
    help="Which agent tools to configure (default: both).",
)
@click.pass_context
def add_all(ctx: click.Context, port: int, tools: tuple[str, ...]) -> None:
    """Add all available components to an existing module project."""
    target_dir, name, description = _resolve_context(ctx)
    _render_addon(
        "addon/all",
        target_dir,
        {
            "module_name": name,
            "module_description": description,
            "port": port,
            "include_dockerfile": True,
            "include_dev_tooling": True,
            "include_agent_config": list(tools),
        },
        ctx.obj["on_conflict"],
        ctx.obj["no_interactive"],
    )
