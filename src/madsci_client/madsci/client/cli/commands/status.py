"""MADSci CLI status command.

Displays status of MADSci services.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

import click

# Default service URLs
DEFAULT_SERVICES = {
    "lab_manager": "http://localhost:8000/",
    "event_manager": "http://localhost:8001/",
    "experiment_manager": "http://localhost:8002/",
    "resource_manager": "http://localhost:8003/",
    "data_manager": "http://localhost:8004/",
    "workcell_manager": "http://localhost:8005/",
    "location_manager": "http://localhost:8006/",
}


class ServiceStatus(str, Enum):
    """Status of a service."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


@dataclass
class ServiceInfo:
    """Information about a service."""

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
    """Check the health of a service."""
    import httpx

    health_url = url.rstrip("/") + "/health"

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(health_url)

            if response.status_code == 200:
                data = response.json() if response.text else {}
                return ServiceInfo(
                    name=name,
                    url=url,
                    status=ServiceStatus.HEALTHY,
                    version=data.get("version"),
                    details=data,
                )
            return ServiceInfo(
                name=name,
                url=url,
                status=ServiceStatus.UNHEALTHY,
                error=f"HTTP {response.status_code}",
            )
    except httpx.ConnectError:
        return ServiceInfo(
            name=name,
            url=url,
            status=ServiceStatus.OFFLINE,
            error="Connection refused",
        )
    except httpx.TimeoutException:
        return ServiceInfo(
            name=name,
            url=url,
            status=ServiceStatus.OFFLINE,
            error="Connection timeout",
        )
    except Exception as e:
        return ServiceInfo(
            name=name,
            url=url,
            status=ServiceStatus.UNKNOWN,
            error=str(e),
        )


def get_status_icon(status: ServiceStatus) -> str:
    """Get the icon for a service status."""
    icons = {
        ServiceStatus.HEALTHY: "[green]\u25cf[/green]",
        ServiceStatus.UNHEALTHY: "[yellow]\u25cf[/yellow]",
        ServiceStatus.OFFLINE: "[red]\u25cb[/red]",
        ServiceStatus.UNKNOWN: "[dim]\u25cb[/dim]",
    }
    return icons.get(status, "?")


def create_status_table(services: list[ServiceInfo]) -> Any:
    """Create a Rich table with service status."""
    from rich.table import Table

    table = Table(title="MADSci Service Status", show_header=True)
    table.add_column("Status", justify="center", width=4)
    table.add_column("Service", style="cyan")
    table.add_column("URL", style="dim")
    table.add_column("State", style="bold")
    table.add_column("Version")

    for svc in services:
        icon = get_status_icon(svc.status)
        status_text = svc.status.value
        if svc.error and svc.status != ServiceStatus.HEALTHY:
            status_text = f"{svc.error}"

        version = svc.version or "-"

        if svc.status == ServiceStatus.HEALTHY:
            status_style = "green"
        elif svc.status == ServiceStatus.UNHEALTHY:
            status_style = "yellow"
        else:
            status_style = "red"

        table.add_row(
            icon,
            svc.name,
            svc.url,
            f"[{status_style}]{status_text}[/{status_style}]",
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
def status(  # noqa: C901
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
    """
    from rich.console import Console

    console: Console = ctx.obj.get("console", Console())

    if services:
        service_urls = {
            name: url for name, url in DEFAULT_SERVICES.items() if name in services
        }
        for svc in services:
            if svc not in DEFAULT_SERVICES and svc.startswith("http"):
                service_urls[svc] = svc
    else:
        service_urls = DEFAULT_SERVICES.copy()

    def fetch_all_status() -> list[ServiceInfo]:
        """Fetch status of all services."""
        return [
            check_service_health(name, url, timeout)
            for name, url in service_urls.items()
        ]

    if as_json or ctx.obj.get("json"):
        results = fetch_all_status()
        output = {
            "services": [svc.to_dict() for svc in results],
            "summary": {
                "healthy": sum(1 for s in results if s.status == ServiceStatus.HEALTHY),
                "unhealthy": sum(
                    1 for s in results if s.status == ServiceStatus.UNHEALTHY
                ),
                "offline": sum(1 for s in results if s.status == ServiceStatus.OFFLINE),
            },
        }
        console.print_json(json.dumps(output))
        return

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

    results = fetch_all_status()
    table = create_status_table(results)
    console.print(table)

    healthy = sum(1 for s in results if s.status == ServiceStatus.HEALTHY)
    total = len(results)

    if healthy == total:
        console.print(f"\n[green]All {total} services healthy.[/green]")
    elif healthy == 0:
        console.print("\n[red]No services responding. Is the lab running?[/red]")
        console.print("[dim]Start with: madsci start lab[/dim]")
    else:
        console.print(f"\n[yellow]{healthy}/{total} services healthy.[/yellow]")
