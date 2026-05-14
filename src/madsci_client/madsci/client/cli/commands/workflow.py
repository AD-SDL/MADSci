"""MADSci CLI workflow command group.

Provides subcommands for full workflow lifecycle management: listing, showing,
submitting, pausing, resuming, cancelling, retrying, and resubmitting workflows.
"""

from __future__ import annotations

import contextlib
import json
import time
from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING

import click
from rich.console import Console

if TYPE_CHECKING:
    from madsci.client.workcell_client import WorkcellClient
    from madsci.common.types.workflow_types import Workflow
from madsci.client.cli.utils.cli_decorators import (
    resolve_service_url,
    timeout_option,
    with_service_error_handling,
)
from madsci.client.cli.utils.formatting import (
    format_duration,
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

_WORKCELL_URL_OPTION = click.option(
    "--workcell-url",
    envvar="MADSCI_WORKCELL_URL",
    default=None,
    help="Workcell manager URL (default: from config or http://localhost:8005/).",
)


def _get_workcell_url(ctx: click.Context, workcell_url: str | None) -> str:
    """Resolve the workcell URL from the option, context, or default."""
    return resolve_service_url(ctx, workcell_url, "workcell_server_url", 8005)


@contextlib.contextmanager
def _make_client(workcell_url: str, timeout: float) -> Iterator[WorkcellClient]:
    from madsci.client.workcell_client import WorkcellClient
    from madsci.common.types.client_types import WorkcellClientConfig

    config = WorkcellClientConfig(timeout_default=timeout)
    client = WorkcellClient(workcell_server_url=workcell_url, config=config)
    try:
        yield client
    finally:
        client.close()


def _workflow_status_label(wf: Workflow) -> str:
    """Derive a human-friendly status label from a Workflow object."""
    st = wf.status
    # Ordered by priority: terminal states first, then active states.
    checks = [
        ("completed", st.completed),
        ("failed", st.failed),
        ("cancelled", st.cancelled),
        ("paused", st.paused),
        ("running", st.running),
        ("queued", st.queued),
    ]
    return next((label for label, flag in checks if flag), "unknown")


def _workflow_progress(wf: Workflow) -> str:
    """Return a progress string like '3/5'."""
    total = len(wf.steps)
    if total == 0:
        return "-"
    done = wf.completed_steps
    return f"{done}/{total}"


def _workflow_step_label(wf: Workflow) -> str:
    """Return a label for the current step."""
    if not wf.steps:
        return "-"
    idx = wf.status.current_step_index
    if 0 <= idx < len(wf.steps):
        step = wf.steps[idx]
        return step.name or f"step {idx}"
    return "-"


def _workflow_to_row(wf: Workflow) -> dict:
    """Convert a Workflow to a dict suitable for table/output rendering."""
    status_label = _workflow_status_label(wf)
    return {
        "status": f"{format_status_icon(status_label)} {format_status_colored(status_label)}",
        "name": wf.name or "-",
        "id": wf.workflow_id,
        "progress": _workflow_progress(wf),
        "step": _workflow_step_label(wf),
        "started": format_timestamp(wf.start_time),
        "duration": format_duration(wf.duration_seconds),
    }


def _workflow_to_dict(wf: Workflow) -> dict:
    """Convert a Workflow to a serialisable dict for JSON/YAML output."""
    d = wf.model_dump(mode="json")
    d["status"] = _workflow_status_label(wf)
    d["progress"] = _workflow_progress(wf)
    d["current_step"] = _workflow_step_label(wf)
    return d


_LIST_COLUMNS = [
    ColumnDef("Status", "status"),
    ColumnDef("Name", "name", style="cyan"),
    ColumnDef("ID", "id", style="dim"),
    ColumnDef("Progress", "progress"),
    ColumnDef("Step", "step"),
    ColumnDef("Started", "started", style="dim"),
    ColumnDef("Duration", "duration"),
]


# ---------------------------------------------------------------------------
# Top-level group
# ---------------------------------------------------------------------------


@click.group()
def workflow() -> None:
    """Manage workflows.

    \b
    Examples:
        madsci workflow list                    List active workflows
        madsci workflow show <id>               Show workflow details
        madsci workflow submit ./wf.yaml        Submit a workflow
        madsci workflow pause <id>              Pause a running workflow
        madsci workflow resume <id>             Resume a paused workflow
        madsci workflow cancel <id>             Cancel a workflow
        madsci workflow retry <id>              Retry a failed workflow
        madsci workflow resubmit <id>           Resubmit a workflow
    """


# ---------------------------------------------------------------------------
# workflow list
# ---------------------------------------------------------------------------


@workflow.command("list")
@click.option("--active", "show_active", is_flag=True, help="Show active workflows.")
@click.option(
    "--archived", "show_archived", is_flag=True, help="Show archived workflows."
)
@click.option("--queued", "show_queued", is_flag=True, help="Show queued workflows.")
@click.option(
    "--all", "show_all", is_flag=True, help="Show all workflows (active + archived)."
)
@click.option(
    "--limit",
    type=int,
    default=20,
    show_default=True,
    help="Limit number of archived workflows returned.",
)
@_WORKCELL_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def list_workflows(
    ctx: click.Context,
    show_active: bool,
    show_archived: bool,
    show_queued: bool,
    show_all: bool,
    limit: int,
    workcell_url: str | None,
    timeout: float,
) -> None:
    """List workflows.

    By default shows active and queued workflows. Use --archived or --all
    to include completed/failed/cancelled workflows.

    \b
    Examples:
        madsci workflow list
        madsci workflow list --all
        madsci workflow list --archived --limit 50
        madsci workflow list --json
    """
    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_workcell_url(ctx, workcell_url)

    with _make_client(url, timeout) as client:
        workflows: list = []

        # Determine what to fetch.  Default (no flags) = active + queued.
        fetch_active = (
            show_all or show_active or (not show_archived and not show_queued)
        )
        fetch_queued = (
            show_all or show_queued or (not show_archived and not show_active)
        )
        fetch_archived = show_all or show_archived

        if fetch_active:
            active = client.get_active_workflows()
            workflows.extend(active.values())

        if fetch_queued:
            queued = client.get_workflow_queue()
            # Avoid duplicates if a queued workflow was already returned as active
            existing_ids = {wf.workflow_id for wf in workflows}
            workflows.extend(wf for wf in queued if wf.workflow_id not in existing_ids)

        if fetch_archived:
            archived = client.get_archived_workflows(number=limit)
            existing_ids = {wf.workflow_id for wf in workflows}
            workflows.extend(
                wf for wf in archived.values() if wf.workflow_id not in existing_ids
            )

        if fmt in (OutputFormat.JSON, OutputFormat.YAML):
            data = [_workflow_to_dict(wf) for wf in workflows]
            output_result(console, data, format=fmt.value)
            return

        if fmt == OutputFormat.QUIET:
            for wf in workflows:
                console.print(f"{wf.workflow_id} {_workflow_status_label(wf)}")
            return

        if not workflows:
            info(console, "No workflows found.")
            return

        rows = [_workflow_to_row(wf) for wf in workflows]
        output_result(
            console, rows, format="text", title="Workflows", columns=_LIST_COLUMNS
        )


# ---------------------------------------------------------------------------
# workflow show -- rendering helpers
# ---------------------------------------------------------------------------


def _render_workflow_table(console: Console, wf: Workflow, show_steps: bool) -> None:
    """Render a workflow's details as a Rich table to the console."""
    status_label = _workflow_status_label(wf)
    console.print()
    console.print(f"[bold]{wf.name or 'Unnamed Workflow'}[/bold]")
    console.print(f"  ID:       {wf.workflow_id}")
    console.print(
        f"  Status:   {format_status_icon(status_label)} {format_status_colored(status_label)}"
    )
    if wf.label:
        console.print(f"  Label:    {wf.label}")
    console.print(f"  Started:  {format_timestamp(wf.start_time)}")
    console.print(f"  Ended:    {format_timestamp(wf.end_time)}")
    console.print(f"  Duration: {format_duration(wf.duration_seconds)}")
    console.print(
        f"  Progress: {_workflow_progress(wf)} steps ({wf.status.description})"
    )

    if wf.parameter_values:
        console.print("  Parameters:")
        for k, v in wf.parameter_values.items():
            console.print(f"    {k}: {v}")

    if show_steps and wf.steps:
        _render_workflow_steps(console, wf)
    console.print()


def _render_workflow_steps(console: Console, wf: Workflow) -> None:
    """Render the expanded step details section."""
    console.print()
    console.print("[bold]Steps:[/bold]")
    for i, step in enumerate(wf.steps):
        step_status = step.status.value if step.status else "unknown"
        console.print(f"  [{i}] {format_status_icon(step_status)} {step.name or '-'}")
        console.print(f"      Action: {step.action or '-'}")
        console.print(f"      Node:   {step.node or '-'}")
        console.print(f"      Status: {format_status_colored(step_status)}")
        if step.result:
            console.print(f"      Result: {step.result.status}")
        if step.start_time:
            console.print(
                f"      Time:   {format_timestamp(step.start_time)} -> {format_timestamp(step.end_time)}"
            )


def _render_workflow(
    console: Console, wf: Workflow, fmt: OutputFormat, show_steps: bool
) -> None:
    """Render a single workflow in the requested output format."""
    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        output_result(console, wf, format=fmt.value)
    elif fmt == OutputFormat.QUIET:
        console.print(f"{wf.workflow_id} {_workflow_status_label(wf)}")
    else:
        _render_workflow_table(console, wf, show_steps)


# ---------------------------------------------------------------------------
# workflow show
# ---------------------------------------------------------------------------


@workflow.command("show")
@click.argument("workflow_id")
@click.option("--steps", is_flag=True, help="Show expanded step details.")
@click.option(
    "--follow", is_flag=True, help="Poll until workflow completes (every 2s)."
)
@_WORKCELL_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def show_workflow(
    ctx: click.Context,
    workflow_id: str,
    steps: bool,
    follow: bool,
    workcell_url: str | None,
    timeout: float,
) -> None:
    """Show details of a workflow.

    \b
    Examples:
        madsci workflow show 01J5ABCDEF12
        madsci workflow show 01J5ABCDEF12 --steps
        madsci workflow show 01J5ABCDEF12 --follow
        madsci workflow show 01J5ABCDEF12 --json
    """
    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_workcell_url(ctx, workcell_url)

    with _make_client(url, timeout) as client:
        wf = client.query_workflow(workflow_id)
        if wf is None:
            raise click.ClickException(f"Workflow {workflow_id} not found.")

        if not follow:
            _render_workflow(console, wf, fmt, steps)
            return

        # Follow mode: poll until terminal
        try:
            while True:
                _render_workflow(console, wf, fmt, steps)
                if wf.status.terminal:
                    break
                info(console, "Waiting for workflow to complete... (Ctrl+C to stop)")
                time.sleep(2)
                wf = client.query_workflow(workflow_id)
                if wf is None:
                    raise click.ClickException(
                        f"Workflow {workflow_id} disappeared while following."
                    )
        except KeyboardInterrupt:
            console.print("\n[dim]Stopped following.[/dim]")


# ---------------------------------------------------------------------------
# workflow submit
# ---------------------------------------------------------------------------


@workflow.command("submit")
@click.argument("path", type=click.Path(exists=True))
@click.option(
    "--parameters",
    "parameters_json",
    help="Workflow parameters as a JSON string.",
)
@click.option(
    "--no-wait",
    is_flag=True,
    help="Submit and return immediately (just print the workflow ID).",
)
@click.option("--name", "label", default=None, help="Optional label for the run.")
@_WORKCELL_URL_OPTION
@timeout_option(default=30.0)
@click.pass_context
@with_service_error_handling
def submit_workflow(
    ctx: click.Context,
    path: str,
    parameters_json: str | None,
    no_wait: bool,
    label: str | None,
    workcell_url: str | None,
    timeout: float,
) -> None:
    """Submit a workflow from a YAML file.

    This replaces 'madsci run workflow'.

    \b
    Examples:
        madsci workflow submit ./workflows/example.workflow.yaml
        madsci workflow submit ./wf.yaml --no-wait
        madsci workflow submit ./wf.yaml --parameters '{"source": "plate_1"}'
        madsci workflow submit ./wf.yaml --name "nightly run"
    """
    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_workcell_url(ctx, workcell_url)

    with _make_client(url, timeout) as client:
        workflow_path = Path(path).resolve()
        json_inputs = None
        if parameters_json:
            try:
                json_inputs = json.loads(parameters_json)
            except json.JSONDecodeError as exc:
                raise click.ClickException(
                    f"Invalid JSON in --parameters: {exc}"
                ) from exc

        if no_wait:
            from madsci.common.types.workflow_types import WorkflowDefinition

            wf_def = WorkflowDefinition.from_yaml(workflow_path)
            if label:
                wf_def.name = f"{wf_def.name} ({label})"
            wf_id = client.submit_workflow_definition(wf_def)

            if fmt in (OutputFormat.JSON, OutputFormat.YAML):
                output_result(console, {"workflow_id": wf_id}, format=fmt.value)
            elif fmt == OutputFormat.QUIET:
                console.print(wf_id)
            else:
                success(console, f"Workflow submitted -- ID: {wf_id}")
            return

        console.print(f"Submitting workflow: [cyan]{workflow_path.name}[/cyan]")
        console.print("Waiting for workflow to complete...")

        result = client.start_workflow(
            workflow_definition=workflow_path,
            json_inputs=json_inputs,
            await_completion=True,
            prompt_on_error=False,
            raise_on_failed=False,
            raise_on_cancelled=False,
        )

        status_label = _workflow_status_label(result)
        if fmt in (OutputFormat.JSON, OutputFormat.YAML):
            output_result(console, result, format=fmt.value)
        elif fmt == OutputFormat.QUIET:
            console.print(f"{result.workflow_id} {status_label}")
        else:
            success(
                console,
                f"Workflow finished -- status: {format_status_colored(status_label)}",
            )


# ---------------------------------------------------------------------------
# workflow pause
# ---------------------------------------------------------------------------


@workflow.command("pause")
@click.argument("workflow_id")
@_WORKCELL_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def pause_workflow(
    ctx: click.Context,
    workflow_id: str,
    workcell_url: str | None,
    timeout: float,
) -> None:
    """Pause a running workflow.

    \b
    Examples:
        madsci workflow pause 01J5ABCDEF12
    """
    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_workcell_url(ctx, workcell_url)

    with _make_client(url, timeout) as client:
        wf = client.pause_workflow(workflow_id)

        if fmt in (OutputFormat.JSON, OutputFormat.YAML):
            output_result(console, _workflow_to_dict(wf), format=fmt.value)
        elif fmt == OutputFormat.QUIET:
            console.print(f"{wf.workflow_id} paused")
        else:
            success(console, f"Workflow {workflow_id} paused.")


# ---------------------------------------------------------------------------
# workflow resume
# ---------------------------------------------------------------------------


@workflow.command("resume")
@click.argument("workflow_id")
@_WORKCELL_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def resume_workflow(
    ctx: click.Context,
    workflow_id: str,
    workcell_url: str | None,
    timeout: float,
) -> None:
    """Resume a paused workflow.

    \b
    Examples:
        madsci workflow resume 01J5ABCDEF12
    """
    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_workcell_url(ctx, workcell_url)

    with _make_client(url, timeout) as client:
        wf = client.resume_workflow(workflow_id)

        if fmt in (OutputFormat.JSON, OutputFormat.YAML):
            output_result(console, _workflow_to_dict(wf), format=fmt.value)
        elif fmt == OutputFormat.QUIET:
            console.print(f"{wf.workflow_id} resumed")
        else:
            success(console, f"Workflow {workflow_id} resumed.")


# ---------------------------------------------------------------------------
# workflow cancel
# ---------------------------------------------------------------------------


@workflow.command("cancel")
@click.argument("workflow_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt.")
@_WORKCELL_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def cancel_workflow(
    ctx: click.Context,
    workflow_id: str,
    yes: bool,
    workcell_url: str | None,
    timeout: float,
) -> None:
    """Cancel a workflow.

    \b
    Examples:
        madsci workflow cancel 01J5ABCDEF12
        madsci workflow cancel 01J5ABCDEF12 --yes
    """
    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_workcell_url(ctx, workcell_url)

    if not yes:
        click.confirm(f"Cancel workflow {workflow_id}?", abort=True)

    with _make_client(url, timeout) as client:
        wf = client.cancel_workflow(workflow_id)

        if fmt in (OutputFormat.JSON, OutputFormat.YAML):
            output_result(console, _workflow_to_dict(wf), format=fmt.value)
        elif fmt == OutputFormat.QUIET:
            console.print(f"{wf.workflow_id} cancelled")
        else:
            success(console, f"Workflow {workflow_id} cancelled.")


# ---------------------------------------------------------------------------
# workflow retry
# ---------------------------------------------------------------------------


@workflow.command("retry")
@click.argument("workflow_id")
@click.option(
    "--from-step",
    type=int,
    default=-1,
    show_default=True,
    help="Step index to retry from (-1 = last failed step).",
)
@click.option(
    "--no-wait",
    is_flag=True,
    help="Don't wait for the retried workflow to complete.",
)
@_WORKCELL_URL_OPTION
@timeout_option(default=30.0)
@click.pass_context
@with_service_error_handling
def retry_workflow(
    ctx: click.Context,
    workflow_id: str,
    from_step: int,
    no_wait: bool,
    workcell_url: str | None,
    timeout: float,
) -> None:
    """Retry a failed workflow.

    \b
    Examples:
        madsci workflow retry 01J5ABCDEF12
        madsci workflow retry 01J5ABCDEF12 --from-step 2
        madsci workflow retry 01J5ABCDEF12 --no-wait
    """
    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_workcell_url(ctx, workcell_url)

    with _make_client(url, timeout) as client:
        # Resolve -1 to the current_step_index of the workflow
        index = from_step
        if index == -1:
            wf = client.query_workflow(workflow_id)
            if wf is None:
                raise click.ClickException(f"Workflow {workflow_id} not found.")
            index = wf.status.current_step_index

        if not no_wait:
            console.print(f"Retrying workflow {workflow_id} from step {index}...")

        wf = client.retry_workflow(
            workflow_id,
            index=index,
            await_completion=not no_wait,
            prompt_on_error=False,
            raise_on_failed=False,
            raise_on_cancelled=False,
        )

        status_label = _workflow_status_label(wf)
        if fmt in (OutputFormat.JSON, OutputFormat.YAML):
            output_result(console, _workflow_to_dict(wf), format=fmt.value)
        elif fmt == OutputFormat.QUIET:
            console.print(f"{wf.workflow_id} {status_label}")
        else:
            success(
                console,
                f"Workflow {workflow_id} retried -- status: {format_status_colored(status_label)}",
            )


# ---------------------------------------------------------------------------
# workflow resubmit
# ---------------------------------------------------------------------------


@workflow.command("resubmit")
@click.argument("workflow_id")
@click.option(
    "--no-wait",
    is_flag=True,
    help="Don't wait for the new workflow to complete.",
)
@_WORKCELL_URL_OPTION
@timeout_option(default=30.0)
@click.pass_context
@with_service_error_handling
def resubmit_workflow(
    ctx: click.Context,
    workflow_id: str,
    no_wait: bool,
    workcell_url: str | None,
    timeout: float,
) -> None:
    """Resubmit a workflow as a new run with the same parameters.

    \b
    Examples:
        madsci workflow resubmit 01J5ABCDEF12
        madsci workflow resubmit 01J5ABCDEF12 --no-wait
    """
    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_workcell_url(ctx, workcell_url)

    with _make_client(url, timeout) as client:
        if not no_wait:
            console.print(f"Resubmitting workflow {workflow_id}...")

        wf = client.resubmit_workflow(
            workflow_id,
            await_completion=not no_wait,
            prompt_on_error=False,
            raise_on_failed=False,
            raise_on_cancelled=False,
        )

        status_label = _workflow_status_label(wf)
        if fmt in (OutputFormat.JSON, OutputFormat.YAML):
            output_result(console, _workflow_to_dict(wf), format=fmt.value)
        elif fmt == OutputFormat.QUIET:
            console.print(f"{wf.workflow_id} {status_label}")
        else:
            success(
                console,
                f"Workflow resubmitted -- new ID: {wf.workflow_id}, status: {format_status_colored(status_label)}",
            )
