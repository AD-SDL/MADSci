"""MADSci CLI stop command.

Wraps ``docker compose down`` for stopping MADSci lab services.
Also supports stopping individual background managers and nodes.
"""

from __future__ import annotations

import os
import signal
import subprocess

import click


def _find_compose_file(config_path: str | None) -> str:
    """Locate a Docker Compose file (reuses start logic)."""
    from madsci.client.cli.commands.start import _find_compose_file as _find

    return str(_find(config_path))


@click.group(invoke_without_command=True)
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
        madsci stop manager event  Stop a background manager
        madsci stop node my_node   Stop a background node
    """
    # Only run the default Docker Compose flow when no subcommand is given.
    if ctx.invoked_subcommand is not None:
        return

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


@stop.command("manager")
@click.argument("name")
@click.pass_context
def stop_manager(ctx: click.Context, name: str) -> None:
    """Stop a background manager process.

    \b
    Examples:
        madsci stop manager event     Stop the event manager
    """
    from madsci.client.cli.commands.start import _read_pid, _remove_pid
    from rich.console import Console

    console: Console = ctx.obj.get("console", Console()) if ctx.obj else Console()

    pid_name = f"manager-{name}"
    pid = _read_pid(pid_name)

    if pid is None:
        raise click.ClickException(
            f"No running manager '{name}' found.\n"
            "  Check running processes with: madsci status"
        )

    try:
        os.kill(pid, signal.SIGTERM)
        console.print(f"[green]Stopped {name} manager[/green] (PID {pid})")
    except ProcessLookupError:
        console.print(f"[yellow]Manager '{name}' was already stopped.[/yellow]")
    finally:
        _remove_pid(pid_name)


@stop.command("node")
@click.argument("name")
@click.pass_context
def stop_node(ctx: click.Context, name: str) -> None:
    """Stop a background node process.

    \b
    Examples:
        madsci stop node my_node     Stop the node
    """
    from madsci.client.cli.commands.start import _read_pid, _remove_pid
    from rich.console import Console

    console: Console = ctx.obj.get("console", Console()) if ctx.obj else Console()

    pid_name = f"node-{name}"
    pid = _read_pid(pid_name)

    if pid is None:
        raise click.ClickException(
            f"No running node '{name}' found.\n"
            "  Check running processes with: madsci status"
        )

    try:
        os.kill(pid, signal.SIGTERM)
        console.print(f"[green]Stopped node '{name}'[/green] (PID {pid})")
    except ProcessLookupError:
        console.print(f"[yellow]Node '{name}' was already stopped.[/yellow]")
    finally:
        _remove_pid(pid_name)
