"""MADSci CLI TUI command.

Launches the interactive terminal user interface.
"""

import click


@click.command()
@click.option(
    "--screen",
    type=click.Choice(["dashboard", "status", "logs"]),
    default="dashboard",
    help="Initial screen to display.",
)
@click.pass_context
def tui(ctx: click.Context, screen: str) -> None:  # noqa: ARG001
    """Launch interactive terminal user interface.

    The TUI provides a visual interface for managing and monitoring
    MADSci labs directly from the terminal.

    \b
    Examples:
        madsci tui                  Launch TUI on dashboard
        madsci tui --screen logs    Launch TUI on logs screen
    """
    try:
        from madsci.client.cli.tui import MadsciApp  # noqa: PLC0415
    except ImportError as e:
        console = ctx.obj.get("console")
        if console:
            console.print(
                "[red]Error: TUI dependencies not installed.[/red]\n\n"
                "Install with:\n"
                "  pip install 'madsci.client[tui]'\n\n"
                f"Details: {e}"
            )
        else:
            click.echo(f"Error: TUI dependencies not installed. Details: {e}")
        ctx.exit(1)

    # Get lab URL from context
    lab_url = ctx.obj.get("lab_url", "http://localhost:8000/")

    # Create and run the TUI app
    app = MadsciApp(lab_url=lab_url)

    app.run()
