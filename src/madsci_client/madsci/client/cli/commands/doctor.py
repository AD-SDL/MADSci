"""MADSci CLI doctor command.

Performs comprehensive system diagnostics to ensure MADSci is properly configured.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import click


class CheckStatus(str, Enum):
    """Status of a diagnostic check."""

    PASSED = "pass"
    FAIL = "fail"
    WARN = "warn"
    SKIP = "skip"


@dataclass
class CheckResult:
    """Result of a diagnostic check."""

    name: str
    status: CheckStatus
    message: str
    details: str | None = None
    fix_suggestion: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON output."""
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "fix_suggestion": self.fix_suggestion,
        }


@dataclass
class DiagnosticResults:
    """Collection of diagnostic check results."""

    checks: list[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> int:
        """Count of passed checks."""
        return sum(1 for c in self.checks if c.status == CheckStatus.PASSED)

    @property
    def failed(self) -> int:
        """Count of failed checks."""
        return sum(1 for c in self.checks if c.status == CheckStatus.FAIL)

    @property
    def warnings(self) -> int:
        """Count of warning checks."""
        return sum(1 for c in self.checks if c.status == CheckStatus.WARN)

    def add(self, result: CheckResult) -> None:
        """Add a check result."""
        self.checks.append(result)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON output."""
        return {
            "summary": {
                "passed": self.passed,
                "failed": self.failed,
                "warnings": self.warnings,
                "total": len(self.checks),
            },
            "checks": [c.to_dict() for c in self.checks],
        }


def check_python_version() -> CheckResult:
    """Check Python version meets requirements."""
    version = sys.version_info
    version_str = f"{version.major}.{version.minor}.{version.micro}"

    if version >= (3, 10):
        return CheckResult(
            name="Python Version",
            status=CheckStatus.PASSED,
            message=f"Python {version_str} (required: >=3.10)",
        )
    return CheckResult(
        name="Python Version",
        status=CheckStatus.FAIL,
        message=f"Python {version_str} is below minimum requirement",
        details="MADSci requires Python 3.10 or higher.",
        fix_suggestion="Install Python 3.10+ from https://python.org",
    )


def check_virtual_env() -> CheckResult:
    """Check if running in a virtual environment."""
    in_venv = sys.prefix != sys.base_prefix

    if in_venv:
        return CheckResult(
            name="Virtual Environment",
            status=CheckStatus.PASSED,
            message=f"Active: {sys.prefix}",
        )
    return CheckResult(
        name="Virtual Environment",
        status=CheckStatus.WARN,
        message="Not running in a virtual environment",
        details="Running in a virtual environment is recommended.",
        fix_suggestion="Create a venv: python -m venv .venv && source .venv/bin/activate",
    )


def check_docker() -> CheckResult:
    """Check Docker availability and version."""
    import shutil
    import subprocess

    docker_path = shutil.which("docker")

    if not docker_path:
        return CheckResult(
            name="Docker",
            status=CheckStatus.WARN,
            message="Docker not found in PATH",
            details="Docker is optional but recommended for running services.",
            fix_suggestion="Install Docker from https://docs.docker.com/get-docker/",
        )

    try:
        result = subprocess.run(
            ["docker", "version", "--format", "{{.Server.Version}}"],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            return CheckResult(
                name="Docker",
                status=CheckStatus.PASSED,
                message=f"Docker {version} running",
            )
        return CheckResult(
            name="Docker",
            status=CheckStatus.WARN,
            message="Docker installed but not running",
            details=result.stderr.strip()
            if result.stderr
            else "Docker daemon not started.",
            fix_suggestion="Start Docker Desktop or run: sudo systemctl start docker",
        )
    except subprocess.TimeoutExpired:
        return CheckResult(
            name="Docker",
            status=CheckStatus.WARN,
            message="Docker command timed out",
            fix_suggestion="Check Docker daemon status",
        )
    except Exception as e:
        return CheckResult(
            name="Docker",
            status=CheckStatus.WARN,
            message=f"Error checking Docker: {e}",
        )


def check_docker_compose() -> CheckResult:
    """Check Docker Compose availability and version."""
    import shutil
    import subprocess

    try:
        result = subprocess.run(
            ["docker", "compose", "version", "--short"],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            major = int(version.split(".")[0]) if version else 0
            if major >= 2:
                return CheckResult(
                    name="Docker Compose",
                    status=CheckStatus.PASSED,
                    message=f"Docker Compose v{version} (required: >=2.0)",
                )
            return CheckResult(
                name="Docker Compose",
                status=CheckStatus.WARN,
                message=f"Docker Compose v{version} is below recommended",
                fix_suggestion="Update Docker Desktop or install Docker Compose v2+",
            )
    except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
        pass

    compose_path = shutil.which("docker-compose")
    if compose_path:
        return CheckResult(
            name="Docker Compose",
            status=CheckStatus.WARN,
            message="docker-compose v1 found (v2 recommended)",
            fix_suggestion="Update to Docker Compose v2 for better compatibility",
        )

    return CheckResult(
        name="Docker Compose",
        status=CheckStatus.WARN,
        message="Docker Compose not found",
        details="Docker Compose is optional but needed for full lab deployment.",
        fix_suggestion="Install via Docker Desktop or: pip install docker-compose",
    )


def check_port(port: int, service_name: str) -> CheckResult:
    """Check if a port is available."""
    import socket

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    try:
        result = sock.connect_ex(("localhost", port))
        if result == 0:
            return CheckResult(
                name=f"Port {port}",
                status=CheckStatus.WARN,
                message=f"Port {port} in use ({service_name})",
                details=f"A service is already listening on port {port}.",
            )
        return CheckResult(
            name=f"Port {port}",
            status=CheckStatus.PASSED,
            message=f"Port {port} available ({service_name})",
        )
    except OSError:
        return CheckResult(
            name=f"Port {port}",
            status=CheckStatus.PASSED,
            message=f"Port {port} available ({service_name})",
        )
    finally:
        sock.close()


def check_required_packages() -> CheckResult:
    """Check that required packages are installed."""
    from importlib.metadata import PackageNotFoundError
    from importlib.metadata import version as pkg_version

    required = ["madsci.common", "madsci.client"]
    missing = []
    installed = []

    for pkg in required:
        try:
            ver = pkg_version(pkg)
            installed.append(f"{pkg}=={ver}")
        except PackageNotFoundError:
            missing.append(pkg)

    if missing:
        return CheckResult(
            name="Required Packages",
            status=CheckStatus.FAIL,
            message=f"Missing packages: {', '.join(missing)}",
            fix_suggestion=f"Install with: pip install {' '.join(missing)}",
        )
    return CheckResult(
        name="Required Packages",
        status=CheckStatus.PASSED,
        message=f"Installed: {', '.join(installed)}",
    )


def run_all_checks(categories: list[str] | None = None) -> DiagnosticResults:
    """Run all diagnostic checks."""
    results = DiagnosticResults()

    check_map = {
        "python": [
            check_python_version,
            check_virtual_env,
            check_required_packages,
        ],
        "docker": [
            check_docker,
            check_docker_compose,
        ],
        "ports": [
            lambda: check_port(8000, "lab_manager"),
            lambda: check_port(8001, "event_manager"),
            lambda: check_port(8002, "experiment_manager"),
            lambda: check_port(8003, "resource_manager"),
            lambda: check_port(8004, "data_manager"),
            lambda: check_port(8005, "workcell_manager"),
            lambda: check_port(8006, "location_manager"),
        ],
    }

    if categories:
        active_categories = [c for c in categories if c in check_map]
    else:
        active_categories = list(check_map.keys())

    for category in active_categories:
        for check_func in check_map[category]:
            try:
                results.add(check_func())
            except Exception as e:
                results.add(
                    CheckResult(
                        name=f"Check Error: {check_func.__name__}",
                        status=CheckStatus.FAIL,
                        message=str(e),
                    )
                )

    return results


def format_status_icon(status: CheckStatus) -> str:
    """Get the icon for a check status."""
    icons = {
        CheckStatus.PASSED: "[green]\u2713[/green]",
        CheckStatus.FAIL: "[red]\u2717[/red]",
        CheckStatus.WARN: "[yellow]\u26a0[/yellow]",
        CheckStatus.SKIP: "[dim]\u25cb[/dim]",
    }
    return icons.get(status, "?")


@click.command()
@click.option(
    "--fix",
    is_flag=True,
    help="Attempt to fix detected issues (not yet implemented).",
)
@click.option(
    "--check",
    "categories",
    type=click.Choice(["python", "docker", "ports", "network"]),
    multiple=True,
    default=None,
    help="Only run specific check categories.",
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    help="Output as JSON.",
)
@click.pass_context
def doctor(  # noqa: C901
    ctx: click.Context,
    fix: bool,
    categories: tuple[str, ...],
    as_json: bool,
) -> None:
    """Perform system diagnostics for MADSci.

    Checks Python environment, Docker availability, port availability,
    and network connectivity to ensure MADSci can run properly.

    \b
    Examples:
        madsci doctor                  Run all checks
        madsci doctor --check python   Only check Python environment
        madsci doctor --check docker   Only check Docker
        madsci doctor --json           Output as JSON
    """
    from madsci.client.cli.utils.output import get_console
    from rich.panel import Panel

    console = get_console(ctx)

    cat_list = list(categories) if categories else None
    results = run_all_checks(cat_list)

    if as_json or ctx.obj.get("json"):
        console.print_json(json.dumps(results.to_dict()))
        return

    console.print()
    console.print(
        Panel.fit(
            "[bold blue]MADSci System Diagnostics[/bold blue]",
            border_style="blue",
        )
    )
    console.print()

    for result in results.checks:
        icon = format_status_icon(result.status)
        console.print(f"  {icon} {result.message}")

        if result.details and ctx.obj.get("verbose", 0) > 0:
            console.print(f"      [dim]{result.details}[/dim]")

        if result.fix_suggestion and result.status in (
            CheckStatus.FAIL,
            CheckStatus.WARN,
        ):
            console.print(f"      [dim]\u2192 {result.fix_suggestion}[/dim]")

    console.print()
    summary_parts = []
    if results.passed:
        summary_parts.append(f"[green]{results.passed} passed[/green]")
    if results.warnings:
        summary_parts.append(f"[yellow]{results.warnings} warnings[/yellow]")
    if results.failed:
        summary_parts.append(f"[red]{results.failed} failed[/red]")

    console.print(f"Summary: {', '.join(summary_parts)}")

    if results.failed > 0:
        console.print()
        console.print(
            "[yellow]Some checks failed. "
            "Address the issues above before running MADSci.[/yellow]"
        )
        ctx.exit(1)
    elif results.warnings > 0:
        console.print()
        console.print(
            "[dim]Some warnings detected. "
            "MADSci may work with reduced functionality.[/dim]"
        )

    if fix:
        console.print()
        console.print("[yellow]--fix is not yet implemented.[/yellow]")
