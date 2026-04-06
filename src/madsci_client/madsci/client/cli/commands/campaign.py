"""MADSci CLI campaign command group.

Provides subcommands for managing experimental campaigns: creating and
viewing campaigns that group related experiments together.
"""

from __future__ import annotations

import click
from madsci.client.cli.utils.cli_decorators import (
    timeout_option,
    with_service_error_handling,
)
from madsci.client.cli.utils.output import (
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


# ---------------------------------------------------------------------------
# Top-level group
# ---------------------------------------------------------------------------


@click.group()
def campaign() -> None:
    """Manage experimental campaigns.

    \b
    Examples:
        madsci campaign create --name "My Campaign"
        madsci campaign get <campaign_id>
    """


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
    client = _make_client(url, timeout)

    camp = ExperimentalCampaign(
        campaign_name=campaign_name,
        campaign_description=campaign_desc,
        experiment_ids=[],
    )
    result = client.register_campaign(camp)

    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        output_result(console, result, format=fmt.value)
    elif fmt == OutputFormat.QUIET:
        # result may be a dict or model; handle both
        cid = (
            result.get("campaign_id", result)
            if isinstance(result, dict)
            else getattr(result, "campaign_id", result)
        )
        console.print(str(cid))
    else:
        cid = (
            result.get("campaign_id", "")
            if isinstance(result, dict)
            else getattr(result, "campaign_id", "")
        )
        success(console, f"Campaign created -- ID: {str(cid)[:12]}")


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
    client = _make_client(url, timeout)

    result = client.get_campaign(campaign_id)

    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        output_result(console, result, format=fmt.value)
    elif fmt == OutputFormat.QUIET:
        cid = (
            result.get("campaign_id", result)
            if isinstance(result, dict)
            else getattr(result, "campaign_id", result)
        )
        console.print(str(cid))
    else:
        output_result(console, result, format="text", title="Campaign")
