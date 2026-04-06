"""MADSci CLI experiment command group.

Provides subcommands for experiment lifecycle management: listing, viewing,
starting, running, pausing, continuing, cancelling, and ending experiments.
"""

from __future__ import annotations

from pathlib import Path

import click
from madsci.client.cli.utils.cli_decorators import (
    timeout_option,
    with_service_error_handling,
)
from madsci.client.cli.utils.formatting import (
    format_status_colored,
    format_status_icon,
    format_timestamp,
)
from madsci.client.cli.utils.output import (
    ColumnDef,
    OutputFormat,
    determine_output_format,
    get_console,
    info,
    output_result,
    success,
)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_EXPERIMENT_URL_OPTION = click.option(
    "--experiment-url",
    envvar="MADSCI_EXPERIMENT_URL",
    default=None,
    help="Experiment manager URL (default: from config or http://localhost:8002/).",
)


def _get_experiment_url(ctx: click.Context, experiment_url: str | None) -> str:
    """Resolve the experiment URL from the option, context, or default."""
    if experiment_url:
        return experiment_url
    context = ctx.obj.get("context") if ctx.obj else None
    if context and context.experiment_server_url:
        return str(context.experiment_server_url)
    return "http://localhost:8002/"


def _make_client(experiment_url: str, timeout: float) -> ExperimentClient:  # noqa: F821 -- lazy import
    from madsci.client.experiment_client import ExperimentClient
    from madsci.common.types.client_types import ExperimentClientConfig

    config = ExperimentClientConfig(timeout_default=timeout)
    return ExperimentClient(experiment_server_url=experiment_url, config=config)


def _experiment_status_label(exp) -> str:  # noqa: ANN001
    """Return a human-friendly status label from an Experiment."""
    return exp.status.value if hasattr(exp.status, "value") else str(exp.status)


def _experiment_to_row(exp) -> dict:  # noqa: ANN001
    """Convert an Experiment to a dict for table rendering."""
    status_label = _experiment_status_label(exp)
    name = None
    if exp.experiment_design:
        name = exp.experiment_design.experiment_name
    return {
        "status": f"{format_status_icon(status_label)} {format_status_colored(status_label)}",
        "name": name or "-",
        "id": exp.experiment_id,
        "run_name": exp.run_name or "-",
        "started": format_timestamp(exp.started_at),
        "ended": format_timestamp(exp.ended_at),
    }


def _experiment_to_dict(exp) -> dict:  # noqa: ANN001
    """Convert an Experiment to a serialisable dict for JSON/YAML output."""
    name = None
    if exp.experiment_design:
        name = exp.experiment_design.experiment_name
    return {
        "experiment_id": exp.experiment_id,
        "name": name,
        "status": _experiment_status_label(exp),
        "run_name": exp.run_name,
        "run_description": exp.run_description,
        "started_at": str(exp.started_at) if exp.started_at else None,
        "ended_at": str(exp.ended_at) if exp.ended_at else None,
    }


_LIST_COLUMNS = [
    ColumnDef("Status", "status"),
    ColumnDef("Name", "name", style="cyan"),
    ColumnDef("ID", "id", style="dim"),
    ColumnDef("Run Name", "run_name"),
    ColumnDef("Started", "started", style="dim"),
    ColumnDef("Ended", "ended", style="dim"),
]


# ---------------------------------------------------------------------------
# Top-level group
# ---------------------------------------------------------------------------


@click.group()
def experiment() -> None:
    """Manage experiments.

    \b
    Examples:
        madsci experiment list                   List recent experiments
        madsci experiment get <id>               Show experiment details
        madsci experiment start --name "run 1"   Start a new experiment
        madsci experiment run ./my_exp.py        Execute experiment script
        madsci experiment pause <id>             Pause an experiment
        madsci experiment continue <id>          Continue a paused experiment
        madsci experiment cancel <id>            Cancel an experiment
        madsci experiment end <id>               End an experiment
    """


# ---------------------------------------------------------------------------
# experiment list
# ---------------------------------------------------------------------------


@experiment.command("list")
@click.option(
    "--count",
    type=int,
    default=20,
    show_default=True,
    help="Number of experiments to retrieve.",
)
@click.option(
    "--status",
    "filter_status",
    default=None,
    help="Filter by status (in_progress, completed, failed, paused, cancelled).",
)
@_EXPERIMENT_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def list_experiments(
    ctx: click.Context,
    count: int,
    filter_status: str | None,
    experiment_url: str | None,
    timeout: float,
) -> None:
    """List recent experiments.

    \b
    Examples:
        madsci experiment list
        madsci experiment list --count 50
        madsci experiment list --status completed
        madsci experiment list --json
    """
    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_experiment_url(ctx, experiment_url)
    client = _make_client(url, timeout)

    experiments = client.get_experiments(number=count)

    # Client-side status filter
    if filter_status:
        experiments = [
            e for e in experiments if _experiment_status_label(e) == filter_status
        ]

    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        data = [_experiment_to_dict(e) for e in experiments]
        output_result(console, data, format=fmt.value)
        return

    if fmt == OutputFormat.QUIET:
        for e in experiments:
            console.print(f"{e.experiment_id} {_experiment_status_label(e)}")
        return

    if not experiments:
        info(console, "No experiments found.")
        return

    rows = [_experiment_to_row(e) for e in experiments]
    output_result(
        console, rows, format="text", title="Experiments", columns=_LIST_COLUMNS
    )


# ---------------------------------------------------------------------------
# experiment get
# ---------------------------------------------------------------------------


@experiment.command("get")
@click.argument("experiment_id")
@_EXPERIMENT_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def get_experiment(
    ctx: click.Context,
    experiment_id: str,
    experiment_url: str | None,
    timeout: float,
) -> None:
    """Show details of a single experiment.

    \b
    Examples:
        madsci experiment get 01J5ABCDEF12
        madsci experiment get 01J5ABCDEF12 --json
    """
    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_experiment_url(ctx, experiment_url)
    client = _make_client(url, timeout)

    exp = client.get_experiment(experiment_id)

    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        output_result(console, exp, format=fmt.value)
    elif fmt == OutputFormat.QUIET:
        console.print(f"{exp.experiment_id} {_experiment_status_label(exp)}")
    else:
        output_result(
            console, _experiment_to_dict(exp), format="text", title="Experiment"
        )


# ---------------------------------------------------------------------------
# experiment start
# ---------------------------------------------------------------------------


@experiment.command("start")
@click.option(
    "--design",
    "design_file",
    type=click.Path(exists=True),
    default=None,
    help="Path to an ExperimentDesign YAML file.",
)
@click.option("--name", "exp_name", default=None, help="Experiment name.")
@click.option("--desc", "exp_desc", default=None, help="Experiment description.")
@click.option("--run-name", default=None, help="Name for the experiment run.")
@_EXPERIMENT_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def start_experiment(
    ctx: click.Context,
    design_file: str | None,
    exp_name: str | None,
    exp_desc: str | None,
    run_name: str | None,
    experiment_url: str | None,
    timeout: float,
) -> None:
    """Start a new experiment.

    Provide an ExperimentDesign YAML file via --design, or create a minimal
    design using --name and --desc.

    \b
    Examples:
        madsci experiment start --design ./my_design.yaml
        madsci experiment start --name "My Experiment"
        madsci experiment start --name "Test" --run-name "run_1"
    """
    from madsci.common.types.experiment_types import ExperimentDesign

    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_experiment_url(ctx, experiment_url)
    client = _make_client(url, timeout)

    if design_file:
        design = ExperimentDesign.from_yaml(Path(design_file).resolve())
    elif exp_name:
        design = ExperimentDesign(
            experiment_name=exp_name,
            experiment_description=exp_desc,
        )
    else:
        raise click.ClickException(
            "Provide --design <file> or --name <name> to start an experiment."
        )

    exp = client.start_experiment(
        experiment_design=design,
        run_name=run_name,
    )

    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        output_result(console, exp, format=fmt.value)
    elif fmt == OutputFormat.QUIET:
        console.print(exp.experiment_id)
    else:
        success(console, f"Experiment started -- ID: {exp.experiment_id}")


# ---------------------------------------------------------------------------
# experiment run
# ---------------------------------------------------------------------------


@experiment.command("run")
@click.argument("script_path", type=click.Path(exists=True))
@click.pass_context
def run_experiment(
    ctx: click.Context,
    script_path: str,
) -> None:
    """Execute a Python experiment script.

    The script should use the MADSci experiment application framework.

    \b
    Examples:
        madsci experiment run ./my_experiment.py
    """
    import subprocess
    import sys

    console = get_console(ctx)

    resolved = Path(script_path).resolve()
    console.print(f"Running experiment: [cyan]{resolved.name}[/cyan]")

    try:
        subprocess.run(  # noqa: S603
            [sys.executable, str(resolved)],
            check=True,
        )
        success(console, "Experiment completed.")
    except subprocess.CalledProcessError as exc:
        raise click.ClickException(
            f"Experiment exited with code {exc.returncode}."
        ) from exc
    except KeyboardInterrupt:
        console.print("\n[yellow]Experiment interrupted.[/yellow]")
        sys.exit(130)


# ---------------------------------------------------------------------------
# experiment pause
# ---------------------------------------------------------------------------


@experiment.command("pause")
@click.argument("experiment_id")
@_EXPERIMENT_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def pause_experiment(
    ctx: click.Context,
    experiment_id: str,
    experiment_url: str | None,
    timeout: float,
) -> None:
    """Pause a running experiment.

    \b
    Examples:
        madsci experiment pause 01J5ABCDEF12
    """
    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_experiment_url(ctx, experiment_url)
    client = _make_client(url, timeout)

    exp = client.pause_experiment(experiment_id)

    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        output_result(console, _experiment_to_dict(exp), format=fmt.value)
    elif fmt == OutputFormat.QUIET:
        console.print(f"{exp.experiment_id} paused")
    else:
        success(console, f"Experiment {experiment_id} paused.")


# ---------------------------------------------------------------------------
# experiment continue
# ---------------------------------------------------------------------------


@experiment.command("continue")
@click.argument("experiment_id")
@_EXPERIMENT_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def continue_experiment(
    ctx: click.Context,
    experiment_id: str,
    experiment_url: str | None,
    timeout: float,
) -> None:
    """Continue a paused experiment.

    \b
    Examples:
        madsci experiment continue 01J5ABCDEF12
    """
    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_experiment_url(ctx, experiment_url)
    client = _make_client(url, timeout)

    exp = client.continue_experiment(experiment_id)

    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        output_result(console, _experiment_to_dict(exp), format=fmt.value)
    elif fmt == OutputFormat.QUIET:
        console.print(f"{exp.experiment_id} continued")
    else:
        success(console, f"Experiment {experiment_id} continued.")


# ---------------------------------------------------------------------------
# experiment cancel
# ---------------------------------------------------------------------------


@experiment.command("cancel")
@click.argument("experiment_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt.")
@_EXPERIMENT_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def cancel_experiment(
    ctx: click.Context,
    experiment_id: str,
    yes: bool,
    experiment_url: str | None,
    timeout: float,
) -> None:
    """Cancel an experiment.

    \b
    Examples:
        madsci experiment cancel 01J5ABCDEF12
        madsci experiment cancel 01J5ABCDEF12 --yes
    """
    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_experiment_url(ctx, experiment_url)

    if not yes:
        click.confirm(f"Cancel experiment {experiment_id}?", abort=True)

    client = _make_client(url, timeout)
    exp = client.cancel_experiment(experiment_id)

    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        output_result(console, _experiment_to_dict(exp), format=fmt.value)
    elif fmt == OutputFormat.QUIET:
        console.print(f"{exp.experiment_id} cancelled")
    else:
        success(console, f"Experiment {experiment_id} cancelled.")


# ---------------------------------------------------------------------------
# experiment end
# ---------------------------------------------------------------------------


@experiment.command("end")
@click.argument("experiment_id")
@click.option(
    "--status",
    "end_status",
    type=click.Choice(["completed", "failed"], case_sensitive=False),
    default=None,
    help="Final status for the experiment.",
)
@_EXPERIMENT_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def end_experiment(
    ctx: click.Context,
    experiment_id: str,
    end_status: str | None,
    experiment_url: str | None,
    timeout: float,
) -> None:
    """End an experiment.

    \b
    Examples:
        madsci experiment end 01J5ABCDEF12
        madsci experiment end 01J5ABCDEF12 --status completed
        madsci experiment end 01J5ABCDEF12 --status failed
    """
    from madsci.common.types.experiment_types import ExperimentStatus

    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_experiment_url(ctx, experiment_url)
    client = _make_client(url, timeout)

    status = ExperimentStatus(end_status) if end_status else None
    exp = client.end_experiment(experiment_id, status=status)

    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        output_result(console, _experiment_to_dict(exp), format=fmt.value)
    elif fmt == OutputFormat.QUIET:
        console.print(f"{exp.experiment_id} ended")
    else:
        success(console, f"Experiment {experiment_id} ended.")
