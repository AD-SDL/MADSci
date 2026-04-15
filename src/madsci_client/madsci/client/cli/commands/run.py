"""MADSci CLI run command.

Convenience commands for running workflows and experiments, using the shared
utility layer for error handling and common CLI options.
"""

from __future__ import annotations

from pathlib import Path

import click
from madsci.client.cli.utils.cli_decorators import (
    timeout_option,
    with_service_error_handling,
)


@click.group()
def run() -> None:
    """Run workflows or experiments.

    \b
    Examples:
        madsci run workflow ./workflows/my.workflow.yaml
        madsci run experiment ./my_experiment.py
    """


@run.command()
@click.argument("path", type=click.Path(exists=True))
@click.option(
    "--workcell",
    "workcell_url",
    envvar="MADSCI_WORKCELL_URL",
    default=None,
    help="Workcell manager URL (default: from config or http://localhost:8005/).",
)
@click.option(
    "--parameters",
    "parameters_json",
    help="Workflow parameters as a JSON string.",
)
@click.option(
    "--no-wait",
    is_flag=True,
    help="Submit the workflow and return immediately.",
)
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def workflow(
    ctx: click.Context,
    path: str,
    workcell_url: str,
    parameters_json: str | None,
    no_wait: bool,
    timeout: float,
) -> None:
    """Submit a workflow to the workcell manager.

    \b
    Examples:
        madsci run workflow ./workflows/example.workflow.yaml
        madsci run workflow ./workflows/example.workflow.yaml --no-wait
        madsci run workflow ./wf.yaml --parameters '{"source": "plate_1"}'
        madsci run workflow ./wf.yaml --timeout 30
    """
    import json

    from madsci.client.cli.utils.output import get_console

    console = get_console(ctx)

    console.print(
        "[yellow]Note: 'madsci run workflow' is deprecated. "
        "Use 'madsci workflow submit' instead.[/yellow]"
    )

    if workcell_url is None:
        context = ctx.obj.get("context") if ctx.obj else None
        workcell_url = (
            str(context.workcell_server_url)
            if context and context.workcell_server_url
            else "http://localhost:8005/"
        )

    workflow_path = Path(path).resolve()
    console.print(f"Submitting workflow: [cyan]{workflow_path.name}[/cyan]")

    json_inputs = None
    if parameters_json:
        try:
            json_inputs = json.loads(parameters_json)
        except json.JSONDecodeError as exc:
            raise click.ClickException(f"Invalid JSON in --parameters: {exc}") from exc

    try:
        from madsci.client.workcell_client import WorkcellClient
        from madsci.common.types.client_types import WorkcellClientConfig

        client_config = WorkcellClientConfig(timeout_default=timeout)
        client = WorkcellClient(workcell_server_url=workcell_url, config=client_config)

        try:
            if no_wait:
                wf_id = client.submit_workflow_definition(workflow_path)
                console.print(
                    f"[green]\u2713[/green] Workflow submitted \u2014 ID: {wf_id}"
                )
            else:
                console.print("Waiting for workflow to complete...")
                result = client.start_workflow(
                    workflow_definition=workflow_path,
                    json_inputs=json_inputs,
                    await_completion=True,
                    prompt_on_error=False,
                    raise_on_failed=False,
                    raise_on_cancelled=False,
                )
                console.print(
                    f"[green]\u2713[/green] Workflow finished \u2014 status: {result.status}"
                )
        finally:
            client.close()
    except ConnectionError as exc:
        raise click.ClickException(
            f"Cannot connect to workcell manager at {workcell_url}\n"
            "  Is the lab running? Try: madsci start"
        ) from exc
    except click.ClickException:
        raise
    except Exception as exc:
        raise click.ClickException(f"Workflow execution failed: {exc}") from exc


@run.command()
@click.argument("path", type=click.Path(exists=True))
@click.pass_context
def experiment(
    ctx: click.Context,
    path: str,
) -> None:
    """Run an experiment script.

    Executes a Python experiment script. The script should use the MADSci
    experiment application framework.

    \b
    Examples:
        madsci run experiment ./my_experiment.py
    """
    import subprocess
    import sys

    from madsci.client.cli.utils.output import get_console

    console = get_console(ctx)

    console.print(
        "[yellow]Note: 'madsci run experiment' is deprecated. "
        "Use 'madsci experiment run' instead.[/yellow]"
    )

    script_path = Path(path).resolve()
    console.print(f"Running experiment: [cyan]{script_path.name}[/cyan]")

    try:
        subprocess.run(  # noqa: S603
            [sys.executable, str(script_path)],
            check=True,
        )
        console.print("[green]\u2713[/green] Experiment completed.")
    except subprocess.CalledProcessError as exc:
        raise click.ClickException(
            f"Experiment exited with code {exc.returncode}."
        ) from exc
    except KeyboardInterrupt:
        console.print("\n[yellow]Experiment interrupted.[/yellow]")
        sys.exit(130)
