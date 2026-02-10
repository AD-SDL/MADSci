"""MADSci CLI version command.

Displays version information for MADSci and all installed packages.
"""

from __future__ import annotations

import json
import sys

import click

# List of MADSci packages to check
MADSCI_PACKAGES = [
    "madsci.common",
    "madsci.client",
    "madsci.squid",
    "madsci.node_module",
    "madsci.experiment_application",
    "madsci.event_manager",
    "madsci.experiment_manager",
    "madsci.resource_manager",
    "madsci.data_manager",
    "madsci.workcell_manager",
    "madsci.location_manager",
]


def get_package_version(package_name: str) -> str | None:
    """Get the version of an installed package.

    Args:
        package_name: The name of the package to check.

    Returns:
        The version string if installed, None otherwise.
    """
    from importlib.metadata import PackageNotFoundError
    from importlib.metadata import version as pkg_version

    try:
        return pkg_version(package_name)
    except PackageNotFoundError:
        return None


def get_installed_packages() -> dict[str, str]:
    """Get versions of all installed MADSci packages.

    Returns:
        Dictionary mapping package names to versions.
    """
    packages = {}
    for pkg in MADSCI_PACKAGES:
        ver = get_package_version(pkg)
        if ver:
            packages[pkg] = ver
    return packages


def get_system_info() -> dict[str, str]:
    """Get system information.

    Returns:
        Dictionary with system information.
    """
    import platform

    return {
        "python_version": sys.version.split()[0],
        "python_implementation": platform.python_implementation(),
        "platform": platform.system(),
        "platform_version": platform.version(),
        "architecture": platform.machine(),
    }


@click.command()
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    help="Output as JSON.",
)
@click.option(
    "--check-updates",
    is_flag=True,
    help="Check PyPI for available updates.",
)
@click.pass_context
def version(ctx: click.Context, as_json: bool, check_updates: bool) -> None:
    """Show version information for MADSci and installed packages.

    \b
    Examples:
        madsci version              Show version info
        madsci version --json       Output as JSON
        madsci version --check-updates  Check for updates
    """
    from rich.console import Console
    from rich.table import Table

    console: Console = ctx.obj.get("console", Console())

    # Gather information
    packages = get_installed_packages()
    system_info = get_system_info()

    # Determine main version (from madsci.common or madsci.client)
    main_version = packages.get("madsci.common") or packages.get(
        "madsci.client", "unknown"
    )

    if as_json or ctx.obj.get("json"):
        # JSON output
        output = {
            "version": main_version,
            "packages": packages,
            "system": system_info,
        }
        console.print_json(json.dumps(output))
        return

    # Rich formatted output
    console.print(f"[bold blue]MADSci[/bold blue] v{main_version}")
    console.print()

    # Installed packages table
    if packages:
        table = Table(title="Installed Packages", show_header=True)
        table.add_column("Package", style="cyan")
        table.add_column("Version", style="green")

        for pkg_name, pkg_ver in sorted(packages.items()):
            table.add_row(pkg_name, pkg_ver)

        console.print(table)
        console.print()

    # System info
    console.print(
        f"[dim]Python:[/dim] {system_info['python_version']} "
        f"({system_info['python_implementation']})",
    )
    console.print(
        f"[dim]Platform:[/dim] {system_info['platform']} "
        f"({system_info['architecture']})",
    )

    if check_updates:
        console.print()
        console.print("[yellow]Update checking not yet implemented.[/yellow]")
        # TODO: Implement PyPI version checking
