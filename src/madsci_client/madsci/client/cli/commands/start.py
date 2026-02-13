"""MADSci CLI start command.

Wraps `docker compose up` for starting MADSci lab services, or launches
all managers in a single process with in-memory backends (local mode).
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from rich.console import Console


def _find_compose_file(config_path: str | None) -> Path:
    """Locate a Docker Compose file.

    Searches in the following order:
    1. Explicit ``--config`` path (if provided)
    2. Current directory
    3. Parent directory

    Returns the path to the compose file, or raises ``click.ClickException``.
    """
    candidates: list[Path] = []
    if config_path:
        candidates.append(Path(config_path))
    else:
        for name in (
            "compose.yaml",
            "compose.yml",
            "docker-compose.yaml",
            "docker-compose.yml",
        ):
            candidates.append(Path.cwd() / name)
            candidates.append(Path.cwd().parent / name)

    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()

    searched = ", ".join(str(c.parent) for c in candidates[:2])
    raise click.ClickException(
        f"No Docker Compose file found. Searched: {searched}\n"
        "  Hint: Run this command from your lab directory, or use --config <path>."
    )


def _check_docker() -> None:
    """Verify that Docker is available and running."""
    if not shutil.which("docker"):
        raise click.ClickException(
            "Docker is not installed or not in PATH.\n"
            "  Install Docker: https://docs.docker.com/get-docker/\n"
            "  Then try again: madsci start"
        )

    result = subprocess.run(
        ["docker", "info"],  # noqa: S607
        capture_output=True,
        timeout=10,
        check=False,
    )
    if result.returncode != 0:
        raise click.ClickException(
            "Docker is installed but not running.\n"
            "  Start Docker Desktop, or run: sudo systemctl start docker"
        )


@click.command()
@click.option("-d", "--detach", is_flag=True, help="Run services in the background.")
@click.option("--build", "do_build", is_flag=True, help="Build images before starting.")
@click.option(
    "--services",
    multiple=True,
    help="Start only specific services (can be repeated).",
)
@click.option(
    "--config",
    "config_path",
    type=click.Path(),
    help="Path to Docker Compose file.",
)
@click.option(
    "--mode",
    type=click.Choice(["docker", "local"], case_sensitive=False),
    default="docker",
    help="Run mode: 'docker' (default) uses Docker Compose; 'local' runs all managers in-process with in-memory backends.",
)
@click.pass_context
def start(
    ctx: click.Context,
    detach: bool,
    do_build: bool,
    services: tuple[str, ...],
    config_path: str | None,
    mode: str,
) -> None:
    """Start MADSci lab services.

    \b
    Examples:
        madsci start              Start all services via Docker (foreground)
        madsci start -d           Start in background (Docker mode)
        madsci start --build      Rebuild images first (Docker mode)
        madsci start --mode local Start all managers in-process (no Docker)
        madsci start --services workcell_manager --services lab_manager
    """
    from rich.console import Console

    console: Console = ctx.obj.get("console", Console()) if ctx.obj else Console()

    if mode == "local":
        _start_local(console)
    else:
        _start_docker(console, detach, do_build, services, config_path)


def _start_local(console: Console) -> None:
    """Start all managers in a single process with in-memory backends."""
    from madsci.common.local_backends.local_runner import LocalRunner

    console.print()
    console.print("[bold green]MADSci Local Mode[/bold green]")
    console.print("[dim]All managers running in-process with in-memory backends.[/dim]")
    console.print(
        "[yellow]Warning: Data is ephemeral and will not persist across restarts.[/yellow]"
    )
    console.print()
    console.print("Managers starting on ports 8000-8006...")
    console.print("[dim]Press Ctrl+C to stop.[/dim]")
    console.print()

    runner = LocalRunner()

    try:
        runner.start()
    except KeyboardInterrupt:
        console.print("\n[yellow]Shutting down...[/yellow]")
        sys.exit(130)


def _start_docker(
    console: Console,
    detach: bool,
    do_build: bool,
    services: tuple[str, ...],
    config_path: str | None,
) -> None:
    """Start services via Docker Compose."""
    _check_docker()

    compose_file = _find_compose_file(config_path)
    console.print(f"Using compose file: [cyan]{compose_file}[/cyan]")

    cmd: list[str] = ["docker", "compose", "-f", str(compose_file), "up"]

    if detach:
        cmd.append("-d")
    if do_build:
        cmd.append("--build")
    if services:
        cmd.extend(services)

    console.print(
        f"Starting services: [bold]{'all' if not services else ', '.join(services)}[/bold]"
    )

    try:
        subprocess.run(cmd, check=True)  # noqa: S603
    except subprocess.CalledProcessError as exc:
        raise click.ClickException(
            f"Docker Compose exited with code {exc.returncode}.\n"
            "  Check the output above for details.\n"
            "  Common issues: port conflicts, missing .env file, image build errors."
        ) from exc
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted.[/yellow]")
        sys.exit(130)
