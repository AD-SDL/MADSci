"""MADSci CLI stop command.

Wraps ``docker compose down`` for stopping MADSci lab services.
"""

from __future__ import annotations

import subprocess

import click


def _find_compose_file(config_path: str | None) -> str:
    """Locate a Docker Compose file (reuses start logic)."""
    from madsci.client.cli.commands.start import _find_compose_file as _find

    return str(_find(config_path))


@click.command()
@click.option(
    "--remove",
    is_flag=True,
    help="Remove locally-built images after stopping.",
)
@click.option(
    "--volumes",
    is_flag=True,
    help="Remove named volumes (destroys data — requires confirmation).",
)
@click.option(
    "--config",
    "config_path",
    type=click.Path(),
    help="Path to Docker Compose file.",
)
@click.pass_context
def stop(
    ctx: click.Context,
    remove: bool,
    volumes: bool,
    config_path: str | None,
) -> None:
    """Stop MADSci lab services via Docker Compose.

    \b
    Examples:
        madsci stop                Stop all services
        madsci stop --remove       Stop and remove images
        madsci stop --volumes      Stop and remove volumes (data loss!)
    """
    from rich.console import Console

    console: Console = ctx.obj.get("console", Console()) if ctx.obj else Console()

    compose_file = _find_compose_file(config_path)
    console.print(f"Using compose file: [cyan]{compose_file}[/cyan]")

    if volumes and not click.confirm(
        "This will remove named volumes and all stored data. Continue?",
        default=False,
    ):
        console.print("[yellow]Aborted.[/yellow]")
        return

    cmd: list[str] = ["docker", "compose", "-f", compose_file, "down"]

    if remove:
        cmd.extend(["--rmi", "local"])
    if volumes:
        cmd.append("-v")

    console.print("Stopping services...")

    try:
        subprocess.run(cmd, check=True)  # noqa: S603
        console.print("[green]Services stopped.[/green]")
    except subprocess.CalledProcessError as exc:
        raise click.ClickException(
            f"Docker Compose exited with code {exc.returncode}.\n"
            "  Check the output above for details."
        ) from exc
