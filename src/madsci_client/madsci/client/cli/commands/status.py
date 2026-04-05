"""MADSci CLI status command.

Displays status of MADSci services, using the shared utility layer for
health checking, formatting, and output rendering.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

import click
from madsci.client.cli.utils.formatting import format_status_colored, format_status_icon
from madsci.client.cli.utils.output import (
    OutputFormat,
    determine_output_format,
    get_console,
    output_result,
)
from madsci.client.cli.utils.service_health import (
    ServiceHealthResult,
    check_service_health_sync,
)

# ---------------------------------------------------------------------------
# Backward-compatible types used by start.py and its tests
# ---------------------------------------------------------------------------


class ServiceStatus(str, Enum):
    """Status of a service (backward-compatible re-export)."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


@dataclass
class ServiceInfo:
    """Information about a service (backward-compatible re-export)."""

    name: str
    url: str
    status: ServiceStatus
    version: str | None = None
    details: dict[str, Any] | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON output."""
        return {
            "name": self.name,
            "url": self.url,
            "status": self.status.value,
            "version": self.version,
            "details": self.details,
            "error": self.error,
        }


def check_service_health(name: str, url: str, timeout: float = 5.0) -> ServiceInfo:
    """Check the health of a service (backward-compatible wrapper).

    Delegates to :func:`check_service_health_sync` from the shared
    service_health module and translates the result to :class:`ServiceInfo`.
    """
    result = check_service_health_sync(name, url, timeout=timeout)
    if result.is_available:
        return ServiceInfo(
            name=result.name,
            url=result.url,
            status=ServiceStatus.HEALTHY,
            version=result.version,
        )
    if result.error and (
        "refused" in result.error.lower() or "timeout" in result.error.lower()
    ):
        return ServiceInfo(
            name=result.name,
            url=result.url,
            status=ServiceStatus.OFFLINE,
            error=result.error,
        )
    return ServiceInfo(
        name=result.name,
        url=result.url,
        status=ServiceStatus.UNHEALTHY if result.error else ServiceStatus.UNKNOWN,
        error=result.error,
    )


def _health_status_label(result: ServiceHealthResult) -> str:
    """Map a ServiceHealthResult to a human-readable status label."""
    if result.is_available:
        return "healthy"
    if result.error and "refused" in result.error.lower():
        return "offline"
    if result.error and "timeout" in result.error.lower():
        return "offline"
    return "unhealthy"


def _result_to_dict(result: ServiceHealthResult) -> dict[str, Any]:
    """Convert a ServiceHealthResult to a serialisable dict."""
    status = _health_status_label(result)
    return {
        "name": result.name,
        "url": result.url,
        "status": status,
        "version": result.version,
        "error": result.error,
        "response_time_ms": result.response_time_ms,
    }


def create_status_table(results: list[ServiceHealthResult]) -> Any:
    """Create a Rich table with service status."""
    from rich.table import Table

    table = Table(title="MADSci Service Status", show_header=True)
    table.add_column("Status", justify="center", width=4)
    table.add_column("Service", style="cyan")
    table.add_column("URL", style="dim")
    table.add_column("State", style="bold")
    table.add_column("Version")

    for result in results:
        status = _health_status_label(result)
        icon = format_status_icon(status)

        if result.is_available:
            status_text = format_status_colored(status)
        elif result.error:
            status_text = format_status_colored(status, result.error)
        else:
            status_text = format_status_colored(status)

        version = result.version or "-"

        table.add_row(
            icon,
            result.name,
            result.url,
            status_text,
            version,
        )

    return table


@click.command()
@click.argument("services", nargs=-1)
@click.option(
    "--watch",
    "-w",
    is_flag=True,
    help="Continuously update status.",
)
@click.option(
    "--interval",
    type=float,
    default=5.0,
    help="Watch interval in seconds (default: 5).",
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    help="Output as JSON.",
)
@click.option(
    "--timeout",
    type=float,
    default=5.0,
    help="Request timeout in seconds (default: 5).",
)
@click.pass_context
def status(  # noqa: C901, PLR0912, PLR0915
    ctx: click.Context,
    services: tuple[str, ...],
    watch: bool,
    interval: float,
    as_json: bool,
    timeout: float,
) -> None:
    """Show status of MADSci services.

    \b
    Examples:
        madsci status                    Show all services
        madsci status lab_manager        Show specific service
        madsci status --watch            Continuously update
        madsci status --json             Output as JSON
        madsci status --yaml             Output as YAML
        madsci status -q                 Quiet: service names and status only
    """
    from madsci.client.cli.tui.constants import get_default_services

    console = get_console(ctx)

    # Merge local --json flag into ctx.obj so determine_output_format sees it
    if as_json:
        ctx.ensure_object(dict)
        ctx.obj["json"] = True

    fmt = determine_output_format(ctx)

    resolved_services = get_default_services(ctx.obj.get("context"))

    if services:
        service_urls = {
            name: url for name, url in resolved_services.items() if name in services
        }
        for svc in services:
            if svc not in resolved_services and svc.startswith("http"):
                service_urls[svc] = svc
    else:
        service_urls = resolved_services.copy()

    def fetch_all_status() -> list[ServiceHealthResult]:
        """Fetch status of all services using shared health check."""
        return [
            check_service_health_sync(name, url, timeout=timeout)
            for name, url in service_urls.items()
        ]

    # --- Structured output modes (JSON / YAML / quiet) ---
    if fmt in (OutputFormat.JSON, OutputFormat.YAML, OutputFormat.QUIET):
        results = fetch_all_status()
        service_dicts = [_result_to_dict(r) for r in results]
        healthy = sum(1 for r in results if r.is_available)
        unhealthy = sum(
            1
            for r in results
            if not r.is_available
            and r.error
            and "refused" not in r.error.lower()
            and "timeout" not in r.error.lower()
        )
        offline = sum(
            1
            for r in results
            if not r.is_available
            and r.error
            and ("refused" in r.error.lower() or "timeout" in r.error.lower())
        )

        if fmt == OutputFormat.QUIET:
            # Quiet mode: just service names and their status
            for svc in service_dicts:
                console.print(f"{svc['name']}: {svc['status']}")
            return

        output = {
            "services": service_dicts,
            "summary": {
                "healthy": healthy,
                "unhealthy": unhealthy,
                "offline": offline,
            },
        }

        if fmt == OutputFormat.JSON:
            console.print_json(json.dumps(output))
        else:
            # YAML
            output_result(console, output, format="yaml")
        return

    # --- Watch mode (Rich table) ---
    if watch:
        from rich.live import Live
        from rich.panel import Panel

        try:
            with Live(console=console, refresh_per_second=1) as live:
                while True:
                    results = fetch_all_status()
                    table = create_status_table(results)
                    panel = Panel(
                        table,
                        title="[bold]MADSci Status[/bold] (Ctrl+C to stop)",
                        border_style="blue",
                    )
                    live.update(panel)
                    time.sleep(interval)
        except KeyboardInterrupt:
            console.print("\n[dim]Stopped watching.[/dim]")
            return

    # --- Default table output ---
    results = fetch_all_status()
    table = create_status_table(results)
    console.print(table)

    healthy = sum(1 for r in results if r.is_available)
    total = len(results)

    if healthy == total:
        console.print(f"\n[green]All {total} services healthy.[/green]")
    elif healthy == 0:
        console.print("\n[red]No services responding. Is the lab running?[/red]")
        console.print("[dim]Start with: madsci start lab[/dim]")
    else:
        console.print(f"\n[yellow]{healthy}/{total} services healthy.[/yellow]")
