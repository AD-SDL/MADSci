"""MADSci CLI start command.

Wraps `docker compose up` for starting MADSci lab services, or launches
all managers in a single process with in-memory backends (local mode).
Also supports starting individual managers and nodes as subprocesses.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from typing import IO

    from rich.console import Console

# Manager name -> Python module mapping.
MANAGER_MODULES: dict[str, str] = {
    "lab": "madsci.squid.lab_server",
    "event": "madsci.event_manager.event_server",
    "experiment": "madsci.experiment_manager.experiment_server",
    "resource": "madsci.resource_manager.resource_server",
    "data": "madsci.data_manager.data_server",
    "workcell": "madsci.workcell_manager.workcell_server",
    "location": "madsci.location_manager.location_server",
}

# Directory for PID files.
_PID_DIR = Path.home() / ".madsci" / "pids"

# Directory for detached process logs.
_LOG_DIR = Path.home() / ".madsci" / "logs"


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


def _print_health_summary(
    console: Console,
    results: dict,
    total: int,
    elapsed: int,
    timeout: int,
) -> None:
    """Print a summary of service health check results."""
    from madsci.client.cli.commands.status import ServiceStatus

    healthy = sum(1 for s in results.values() if s == ServiceStatus.HEALTHY)

    if healthy == total:
        console.print(
            f"\n[green]All {total} services healthy (took {elapsed}s).[/green]"
        )
    else:
        console.print(
            f"\n[yellow]{healthy}/{total} healthy after {timeout}s timeout.[/yellow]"
        )
        for name, st in results.items():
            if st != ServiceStatus.HEALTHY:
                console.print(f"  [red]\u25cb[/red] {name}: {st.value}")


def _wait_for_health(console: Console, timeout: int) -> None:
    """Poll service health endpoints and display progress.

    Uses ``check_service_health`` from the status module and
    ``get_default_services`` from TUI constants to avoid duplicating
    health-check logic.
    """
    from madsci.client.cli.commands.status import (
        ServiceStatus,
        check_service_health,
    )
    from madsci.client.cli.tui.constants import get_default_services
    from madsci.common.context import get_current_madsci_context
    from rich.live import Live
    from rich.table import Table

    services = get_default_services(get_current_madsci_context())
    start_time = time.monotonic()
    deadline = start_time + timeout
    total = len(services)

    def _build_table(results: dict[str, ServiceStatus]) -> Table:
        table = Table(title="Waiting for services...", show_header=True)
        table.add_column("Status", justify="center", width=4)
        table.add_column("Service", style="cyan")
        for name in services:
            st = results.get(name, ServiceStatus.UNKNOWN)
            icon = (
                "[green]\u25cf[/green]"
                if st == ServiceStatus.HEALTHY
                else "[dim]\u25cb[/dim]"
            )
            table.add_row(icon, name)
        return table

    results: dict[str, ServiceStatus] = {}

    try:
        with Live(console=console, refresh_per_second=2) as live:
            while time.monotonic() < deadline:
                for name, url in services.items():
                    info = check_service_health(name, url, timeout=3.0)
                    results[name] = info.status
                live.update(_build_table(results))

                healthy = sum(1 for s in results.values() if s == ServiceStatus.HEALTHY)
                if healthy == total:
                    break
                time.sleep(2)
    except KeyboardInterrupt:
        console.print("\n[yellow]Health check interrupted.[/yellow]")
        return

    elapsed = int(time.monotonic() - start_time)
    _print_health_summary(console, results, total, elapsed, timeout)


def _open_log_file(name: str) -> tuple[Path, IO]:
    """Create and open a timestamped log file for a detached process.

    Returns the log path and the open file handle (caller is responsible
    for the handle's lifetime — it is inherited by the child process).
    """
    from datetime import datetime

    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = _LOG_DIR / f"{name}_{ts}.log"
    fh = log_path.open("a")
    return log_path, fh


def _write_pid(name: str, pid: int) -> Path:
    """Write a PID file for a named process.

    Records the PID and the executable path so that ``_read_pid`` can
    verify the process identity before sending signals.
    """
    import json as _json

    _PID_DIR.mkdir(parents=True, exist_ok=True)
    pid_file = _PID_DIR / f"{name}.pid"
    pid_data = {"pid": pid, "exe": sys.executable, "name": name}
    pid_file.write_text(_json.dumps(pid_data))
    return pid_file


def _read_pid(name: str) -> int | None:
    """Read a PID file and check if the process is still alive.

    Also verifies that the running process matches the expected
    executable to guard against PID reuse after the original process
    exits.
    """
    import json as _json

    pid_file = _PID_DIR / f"{name}.pid"
    if not pid_file.exists():
        return None
    try:
        content = pid_file.read_text().strip()
        # Support both new JSON format and legacy plain-int format
        try:
            pid_data = _json.loads(content)
            pid = int(pid_data["pid"])
            expected_exe = pid_data.get("exe")
        except (_json.JSONDecodeError, KeyError):
            pid = int(content)
            expected_exe = None

        os.kill(pid, 0)  # Check if process exists

        # Verify process identity to avoid PID reuse issues
        if expected_exe:
            try:
                proc_exe = Path(f"/proc/{pid}/exe").resolve()
                if proc_exe != Path(expected_exe).resolve():
                    pid_file.unlink(missing_ok=True)
                    return None
            except (OSError, ValueError):
                pass  # /proc not available (macOS), skip verification

        return pid
    except (ValueError, ProcessLookupError, PermissionError):
        # Stale PID file
        pid_file.unlink(missing_ok=True)
        return None


def _remove_pid(name: str) -> None:
    """Remove a PID file."""
    pid_file = _PID_DIR / f"{name}.pid"
    pid_file.unlink(missing_ok=True)


@click.group(invoke_without_command=True)
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
@click.option(
    "--wait/--no-wait",
    default=None,
    help="Wait for services to become healthy after starting (default: wait when -d is used).",
)
@click.option(
    "--wait-timeout",
    type=int,
    default=60,
    help="Timeout in seconds for health check polling (default: 60).",
)
@click.option(
    "--settings-dir",
    "settings_dir",
    type=click.Path(exists=True, file_okay=False),
    default=None,
    help="Settings directory for walk-up config file discovery. Sets MADSCI_SETTINGS_DIR for child processes.",
)
@click.pass_context
def start(
    ctx: click.Context,
    detach: bool,
    do_build: bool,
    services: tuple[str, ...],
    config_path: str | None,
    mode: str,
    wait: bool | None,
    wait_timeout: int,
    settings_dir: str | None,
) -> None:
    """Start MADSci lab services.

    \b
    Examples:
        madsci start              Start all services via Docker (foreground)
        madsci start -d           Start in background (Docker mode)
        madsci start -d --no-wait Skip health polling after starting
        madsci start --build      Rebuild images first (Docker mode)
        madsci start --mode local Start all managers in-process (no Docker)
        madsci start --services workcell_manager --services lab_manager
        madsci start manager event       Start a single manager
        madsci start manager event -d    Start manager in background
        madsci start node ./node.py      Start a node module
    """
    # Store settings_dir for subcommands to access.
    ctx.ensure_object(dict)
    ctx.obj["settings_dir"] = settings_dir

    # Set env var so it's picked up by settings classes in this process.
    if settings_dir:
        os.environ["MADSCI_SETTINGS_DIR"] = str(Path(settings_dir).resolve())

    # Only run the default Docker/local flow when no subcommand is given.
    if ctx.invoked_subcommand is not None:
        return

    from madsci.client.cli.utils.output import get_console

    console = get_console(ctx)

    if mode == "local":
        _start_local(console)
    else:
        _start_docker(console, detach, do_build, services, config_path)

        # Health polling: default to True when detached, False otherwise.
        should_wait = wait if wait is not None else detach
        if should_wait:
            _wait_for_health(console, wait_timeout)


def _build_child_env(settings_dir: str | None) -> dict[str, str] | None:
    """Build environment dict for child processes with MADSCI_SETTINGS_DIR.

    Returns ``None`` if no settings_dir is set, which tells subprocess to
    inherit the current environment unmodified.
    """
    if not settings_dir:
        return None
    env = os.environ.copy()
    env["MADSCI_SETTINGS_DIR"] = str(Path(settings_dir).resolve())
    return env


@start.command("manager")
@click.argument("name", type=click.Choice(sorted(MANAGER_MODULES.keys())))
@click.option(
    "-d", "--detach", is_flag=True, help="Run in the background with PID tracking."
)
@click.option(
    "--settings-dir",
    "settings_dir",
    type=click.Path(exists=True, file_okay=False),
    default=None,
    help="Settings directory for walk-up config file discovery.",
)
@click.pass_context
def start_manager(
    ctx: click.Context, name: str, detach: bool, settings_dir: str | None
) -> None:
    """Start a single manager as a subprocess.

    \b
    Examples:
        madsci start manager event       Start event manager (foreground)
        madsci start manager event -d    Start in background
    """
    from madsci.client.cli.utils.output import get_console

    console = get_console(ctx)

    # Inherit settings_dir from parent group if not set directly.
    effective_settings_dir = settings_dir or (ctx.obj or {}).get("settings_dir")
    child_env = _build_child_env(effective_settings_dir)

    module = MANAGER_MODULES[name]

    # Check for already running process
    existing_pid = _read_pid(f"manager-{name}")
    if existing_pid is not None:
        raise click.ClickException(
            f"Manager '{name}' is already running (PID {existing_pid}).\n"
            f"  Stop it first: madsci stop manager {name}"
        )

    cmd = [sys.executable, "-m", module]

    if detach:
        log_path, log_fh = _open_log_file(f"manager-{name}")
        try:
            proc = subprocess.Popen(  # noqa: S603
                cmd,
                stdout=log_fh,
                stderr=log_fh,
                start_new_session=True,
                env=child_env,
            )
        except Exception:
            log_fh.close()
            raise
        log_fh.close()
        pid_file = _write_pid(f"manager-{name}", proc.pid)
        console.print(f"[green]Started {name} manager[/green] (PID {proc.pid})")
        console.print(f"  PID file: [dim]{pid_file}[/dim]")
        console.print(f"  Log file: [dim]{log_path}[/dim]")
        console.print(f"  Stop with: madsci stop manager {name}")
    else:
        console.print(f"Starting {name} manager...")
        console.print("[dim]Press Ctrl+C to stop.[/dim]")
        try:
            subprocess.run(cmd, check=True, env=child_env)  # noqa: S603
        except subprocess.CalledProcessError as exc:
            raise click.ClickException(
                f"Manager '{name}' exited with code {exc.returncode}."
            ) from exc
        except KeyboardInterrupt:
            console.print(f"\n[yellow]{name} manager stopped.[/yellow]")
            sys.exit(130)


@start.command("node")
@click.argument("path", type=click.Path(exists=True))
@click.option(
    "-d", "--detach", is_flag=True, help="Run in the background with PID tracking."
)
@click.option(
    "--name", "node_name", help="Name for PID tracking (default: filename stem)."
)
@click.option(
    "--settings-dir",
    "settings_dir",
    type=click.Path(exists=True, file_okay=False),
    default=None,
    help="Settings directory for walk-up config file discovery.",
)
@click.pass_context
def start_node(
    ctx: click.Context,
    path: str,
    detach: bool,
    node_name: str | None,
    settings_dir: str | None,
) -> None:
    """Start a node module as a subprocess.

    \b
    Examples:
        madsci start node ./my_node.py           Start node (foreground)
        madsci start node ./my_node.py -d        Start in background
        madsci start node ./my_node.py --name lh Start with custom name
    """
    from madsci.client.cli.utils.output import get_console

    console = get_console(ctx)

    # Inherit settings_dir from parent group if not set directly.
    effective_settings_dir = settings_dir or (ctx.obj or {}).get("settings_dir")
    child_env = _build_child_env(effective_settings_dir)

    node_path = Path(path).resolve()
    name = node_name or node_path.stem

    # Check for already running process
    existing_pid = _read_pid(f"node-{name}")
    if existing_pid is not None:
        raise click.ClickException(
            f"Node '{name}' is already running (PID {existing_pid}).\n"
            f"  Stop it first: madsci stop node {name}"
        )

    cmd = [sys.executable, str(node_path)]

    if detach:
        log_path, log_fh = _open_log_file(f"node-{name}")
        try:
            proc = subprocess.Popen(  # noqa: S603
                cmd,
                stdout=log_fh,
                stderr=log_fh,
                start_new_session=True,
                env=child_env,
            )
        except Exception:
            log_fh.close()
            raise
        log_fh.close()
        pid_file = _write_pid(f"node-{name}", proc.pid)
        console.print(f"[green]Started node '{name}'[/green] (PID {proc.pid})")
        console.print(f"  PID file: [dim]{pid_file}[/dim]")
        console.print(f"  Log file: [dim]{log_path}[/dim]")
        console.print(f"  Stop with: madsci stop node {name}")
    else:
        console.print(f"Starting node '{name}' from {node_path}...")
        console.print("[dim]Press Ctrl+C to stop.[/dim]")
        try:
            subprocess.run(cmd, check=True, env=child_env)  # noqa: S603
        except subprocess.CalledProcessError as exc:
            raise click.ClickException(
                f"Node '{name}' exited with code {exc.returncode}."
            ) from exc
        except KeyboardInterrupt:
            console.print(f"\n[yellow]Node '{name}' stopped.[/yellow]")
            sys.exit(130)


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
