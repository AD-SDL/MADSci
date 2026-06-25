"""MADSci CLI campaign command group.

Provides subcommands for managing experimental campaigns: creating and
viewing campaigns that group related experiments together.
"""

from __future__ import annotations

import contextlib
from collections.abc import Iterator
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from madsci.client.experiment_client import ExperimentClient

import click
from madsci.client.cli.utils.cli_decorators import (
    resolve_service_url,
    timeout_option,
    with_service_error_handling,
)
from madsci.client.cli.utils.output import (
    ColumnDef,
    OutputFormat,
    determine_output_format,
    get_console,
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
    return resolve_service_url(ctx, experiment_url, "experiment_server_url", 8002)


@contextlib.contextmanager
def _make_client(experiment_url: str, timeout: float) -> Iterator[ExperimentClient]:
    from madsci.client.experiment_client import ExperimentClient
    from madsci.common.types.client_types import ExperimentClientConfig

    config = ExperimentClientConfig(timeout_default=timeout)
    client = ExperimentClient(experiment_server_url=experiment_url, config=config)
    try:
        yield client
    finally:
        client.close()


# ---------------------------------------------------------------------------
# Top-level group
# ---------------------------------------------------------------------------


_LIST_COLUMNS = [
    ColumnDef("ID", "id", style="dim"),
    ColumnDef("Name", "name", style="cyan"),
]


@click.group()
def campaign() -> None:
    """Manage experimental campaigns.

    \b
    Examples:
        madsci campaign list
        madsci campaign create --name "My Campaign"
        madsci campaign get <campaign_id>
    """


# ---------------------------------------------------------------------------
# campaign list
# ---------------------------------------------------------------------------


@campaign.command("list")
@_EXPERIMENT_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def list_campaigns(
    ctx: click.Context,
    experiment_url: str | None,
    timeout: float,
) -> None:
    """List all campaigns.

    \b
    Examples:
        madsci campaign list
        madsci campaign list --json
        madsci campaign list --quiet
    """
    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_experiment_url(ctx, experiment_url)

    with _make_client(url, timeout) as client:
        campaigns = client.get_campaigns(timeout=timeout)

        if fmt in (OutputFormat.JSON, OutputFormat.YAML):
            output_result(console, campaigns, format=fmt.value)
            return

        if fmt == OutputFormat.QUIET:
            for camp in campaigns:
                console.print(str(getattr(camp, "campaign_id", "")))
            return

        if not campaigns:
            console.print("[dim]No campaigns found.[/dim]")
            return

        rows = []
        for camp in campaigns:
            rows.append(
                {
                    "id": getattr(camp, "campaign_id", "-"),
                    "name": getattr(camp, "campaign_name", "-"),
                }
            )
        output_result(
            console, rows, format="text", title="Campaigns", columns=_LIST_COLUMNS
        )


# ---------------------------------------------------------------------------
# campaign create
# ---------------------------------------------------------------------------


@campaign.command("create")
@click.option("--name", "campaign_name", required=True, help="Campaign name.")
@click.option("--desc", "campaign_desc", default=None, help="Campaign description.")
@_EXPERIMENT_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def create_campaign(
    ctx: click.Context,
    campaign_name: str,
    campaign_desc: str | None,
    experiment_url: str | None,
    timeout: float,
) -> None:
    """Create a new experimental campaign.

    \b
    Examples:
        madsci campaign create --name "pH Optimization"
        madsci campaign create --name "Catalyst Screen" --desc "Screening 50 catalysts"
    """
    from madsci.common.types.experiment_types import ExperimentalCampaign

    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_experiment_url(ctx, experiment_url)

    with _make_client(url, timeout) as client:
        camp = ExperimentalCampaign(
            campaign_name=campaign_name,
            campaign_description=campaign_desc,
            experiment_ids=[],
        )
        result = client.register_campaign(camp)

        if fmt in (OutputFormat.JSON, OutputFormat.YAML):
            output_result(console, result, format=fmt.value)
        elif fmt == OutputFormat.QUIET:
            console.print(str(getattr(result, "campaign_id", result)))
        else:
            success(
                console,
                f"Campaign created -- ID: {getattr(result, 'campaign_id', '')!s}",
            )


# ---------------------------------------------------------------------------
# campaign get
# ---------------------------------------------------------------------------


@campaign.command("get")
@click.argument("campaign_id")
@_EXPERIMENT_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def get_campaign(
    ctx: click.Context,
    campaign_id: str,
    experiment_url: str | None,
    timeout: float,
) -> None:
    """Show details of a campaign.

    \b
    Examples:
        madsci campaign get 01J5ABCDEF12
        madsci campaign get 01J5ABCDEF12 --json
    """
    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_experiment_url(ctx, experiment_url)

    with _make_client(url, timeout) as client:
        result = client.get_campaign(campaign_id)

        if fmt in (OutputFormat.JSON, OutputFormat.YAML):
            output_result(console, result, format=fmt.value)
        elif fmt == OutputFormat.QUIET:
            console.print(str(getattr(result, "campaign_id", result)))
        else:
            output_result(console, result, format="text", title="Campaign")
