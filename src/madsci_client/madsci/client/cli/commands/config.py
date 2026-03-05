"""MADSci CLI config command group.

Provides explicit commands for managing MADSci configuration, replacing
the implicit auto-writing behavior with user-initiated actions.

Subcommands:
    export   - Export configuration with secret redaction
    create   - Generate a new configuration file from template
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import click

# --- Manager settings registry: maps manager type to (settings_class_path, friendly_name)
_MANAGER_SETTINGS: dict[str, tuple[str, str]] = {
    "lab": ("madsci.common.types.lab_types.LabManagerSettings", "Lab Manager"),
    "event": ("madsci.common.types.event_types.EventManagerSettings", "Event Manager"),
    "experiment": (
        "madsci.common.types.experiment_types.ExperimentManagerSettings",
        "Experiment Manager",
    ),
    "resource": (
        "madsci.common.types.resource_types.definitions.ResourceManagerSettings",
        "Resource Manager",
    ),
    "data": ("madsci.common.types.datapoint_types.DataManagerSettings", "Data Manager"),
    "workcell": (
        "madsci.common.types.workcell_types.WorkcellManagerSettings",
        "Workcell Manager",
    ),
    "location": (
        "madsci.common.types.location_types.LocationManagerSettings",
        "Location Manager",
    ),
}


def _validate_output_path(output: str) -> None:
    """Warn if the output path is absolute or contains '..' components."""
    path = Path(output)
    if path.is_absolute():
        click.echo(
            f"Warning: output path '{output}' is absolute; "
            "consider using a relative path.",
            err=True,
        )
    if ".." in path.parts:
        click.echo(
            f"Warning: output path '{output}' contains '..'; "
            "consider using a path without parent directory references.",
            err=True,
        )


def _import_class(dotted_path: str) -> type:
    """Dynamically import a class from a dotted path."""
    import importlib

    module_path, _, class_name = dotted_path.rpartition(".")
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def _export_settings(
    settings_class_path: str,
    include_secrets: bool,
    include_defaults: bool,
    output_format: str,
    settings_dir: str | None = None,
) -> str:
    """Export settings from a class, with optional secret redaction.

    Uses by_alias=True so that settings with a prefixed alias_generator
    produce prefixed keys (e.g., event_server_url instead of server_url),
    which is correct for a shared settings.yaml file.
    """
    settings_cls = _import_class(settings_class_path)
    init_kwargs: dict = {}
    if settings_dir:
        init_kwargs["_settings_dir"] = settings_dir
    settings = settings_cls(**init_kwargs)

    if hasattr(settings, "model_dump_safe"):
        data = settings.model_dump_safe(include_secrets=include_secrets, by_alias=True)
    else:
        data = settings.model_dump(mode="json", by_alias=True)

    if not include_defaults:
        try:
            defaults = settings_cls().model_dump(mode="json", by_alias=True)
            data = {k: v for k, v in data.items() if data.get(k) != defaults.get(k)}
        except Exception:
            import logging as _logging

            _logging.getLogger(__name__).debug(
                "Could not create default settings instance for comparison",
                exc_info=True,
            )

    if output_format == "json":
        return json.dumps(data, indent=2, default=str)
    import yaml

    return yaml.dump(data, indent=2, sort_keys=False, default_flow_style=False)


@click.group()
def config() -> None:
    """Manage MADSci configuration.

    \b
    Export, create, and manage configuration files explicitly.
    Replaces the deprecated auto-writing behavior.

    \b
    Examples:
        madsci config export event             Export Event Manager settings
        madsci config export --all             Export all manager settings
        madsci config create manager event     Create Event Manager config file
    """


@config.command()
@click.argument(
    "manager_type",
    required=False,
    type=click.Choice(list(_MANAGER_SETTINGS.keys())),
)
@click.option("--all", "export_all", is_flag=True, help="Export all manager settings.")
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=None,
    help="Write output to file instead of stdout.",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["yaml", "json"]),
    default="yaml",
    help="Output format (default: yaml).",
)
@click.option(
    "--include-secrets",
    is_flag=True,
    default=False,
    help="Include actual secret values (WARNING: exposes credentials).",
)
@click.option(
    "--include-defaults/--no-include-defaults",
    default=True,
    help="Include fields with default values.",
)
@click.option(
    "--settings-dir",
    "settings_dir",
    type=click.Path(exists=True, file_okay=False),
    default=None,
    help="Settings directory for walk-up config file discovery.",
)
@click.pass_context
def export(
    ctx: click.Context,
    manager_type: Optional[str],
    export_all: bool,
    output: Optional[str],
    output_format: str,
    include_secrets: bool,
    include_defaults: bool,
    settings_dir: Optional[str],
) -> None:
    """Export current manager settings.

    Exports settings with sensitive fields redacted by default.
    Use --include-secrets to reveal actual values (use with caution).

    \b
    Examples:
        madsci config export event                 Export Event Manager settings
        madsci config export resource --format json Export as JSON
        madsci config export event --include-secrets Include secret values
        madsci config export --all                  Export all managers
    """
    from madsci.client.cli.utils.output import get_console

    console = get_console(ctx)

    if not manager_type and not export_all:
        console.print(
            "[red]Error: specify a manager type or use --all[/red]\n"
            f"Available types: {', '.join(_MANAGER_SETTINGS.keys())}"
        )
        ctx.exit(1)
        return

    if include_secrets:
        from rich.console import Console as StderrConsole

        StderrConsole(stderr=True).print(
            "[yellow]WARNING: Secret values will be included in output![/yellow]"
        )

    managers_to_export = (
        list(_MANAGER_SETTINGS.keys()) if export_all else [manager_type]
    )
    outputs: list[str] = []

    for mgr_type in managers_to_export:
        if mgr_type not in _MANAGER_SETTINGS:
            continue
        class_path, friendly_name = _MANAGER_SETTINGS[mgr_type]
        try:
            result = _export_settings(
                class_path,
                include_secrets,
                include_defaults,
                output_format,
                settings_dir=settings_dir,
            )
            if export_all:
                separator = (
                    f"# --- {friendly_name} ---\n" if output_format == "yaml" else ""
                )
                outputs.append(f"{separator}{result}")
            else:
                outputs.append(result)
        except Exception as exc:
            console.print(f"[red]Error exporting {friendly_name}: {exc}[/red]")

    combined = "\n".join(outputs)

    if output:
        _validate_output_path(output)
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        Path(output).write_text(combined)
        console.print(f"[green]Configuration written to {output}[/green]")
    else:
        click.echo(combined)


@config.group()
def create() -> None:
    """Create a new configuration file.

    \b
    Generate configuration files for managers or nodes from defaults.

    \b
    Examples:
        madsci config create manager event
        madsci config create manager resource --output resource-settings.yaml
    """


@create.command("manager")
@click.argument(
    "manager_type",
    type=click.Choice(list(_MANAGER_SETTINGS.keys())),
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=None,
    help="Output file path (default: <type>.settings.yaml).",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["yaml", "json"]),
    default="yaml",
    help="Output format (default: yaml).",
)
@click.pass_context
def create_manager(
    ctx: click.Context,
    manager_type: str,
    output: Optional[str],
    output_format: str,
) -> None:
    """Generate a manager configuration file with default values.

    Creates a settings file from the manager's defaults. Sensitive fields
    are included as placeholders that you should fill in.

    \b
    Examples:
        madsci config create manager event
        madsci config create manager resource -o my-resource.yaml
    """
    from madsci.client.cli.utils.output import get_console

    console = get_console(ctx)

    class_path, friendly_name = _MANAGER_SETTINGS[manager_type]

    try:
        result = _export_settings(
            class_path,
            include_secrets=False,
            include_defaults=True,
            output_format=output_format,
        )
    except Exception as exc:
        console.print(f"[red]Error creating config for {friendly_name}: {exc}[/red]")
        ctx.exit(1)
        return

    output_path = output or f"{manager_type}.settings.{output_format}"
    _validate_output_path(output_path)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(result)
    console.print(
        f"[green]Created {friendly_name} configuration: {output_path}[/green]"
    )
    console.print(
        "[dim]Edit the file and replace ***REDACTED*** placeholders "
        "with actual values.[/dim]"
    )


@create.command("node")
@click.argument(
    "node_type",
    type=click.Choice(["basic", "rest"]),
    default="rest",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=None,
    help="Output file path (default: node.settings.yaml).",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["yaml", "json"]),
    default="yaml",
    help="Output format (default: yaml).",
)
@click.pass_context
def create_node(
    ctx: click.Context,
    node_type: str,
    output: Optional[str],
    output_format: str,
) -> None:
    """Generate a node configuration file with default values.

    \b
    Types:
        basic   - Minimal node configuration
        rest    - REST node with HTTP API settings

    \b
    Examples:
        madsci config create node rest
        madsci config create node basic -o my-node.yaml
    """
    from madsci.client.cli.utils.output import get_console

    console = get_console(ctx)

    config_classes = {
        "basic": "madsci.common.types.node_types.NodeConfig",
        "rest": "madsci.common.types.node_types.RestNodeConfig",
    }

    class_path = config_classes[node_type]

    try:
        result = _export_settings(
            class_path,
            include_secrets=False,
            include_defaults=True,
            output_format=output_format,
        )
    except Exception as exc:
        console.print(f"[red]Error creating node config: {exc}[/red]")
        ctx.exit(1)
        return

    output_path = output or f"node.settings.{output_format}"
    _validate_output_path(output_path)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(result)
    console.print(
        f"[green]Created {node_type} node configuration: {output_path}[/green]"
    )
