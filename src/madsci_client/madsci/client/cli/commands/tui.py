"""MADSci CLI TUI command.

Launches the interactive terminal user interface.
"""

import click


@click.command()
@click.option(
    "--screen",
    type=click.Choice(
        [
            "dashboard",
            "status",
            "logs",
            "nodes",
            "workflows",
            "experiments",
            "resources",
            "data",
            "locations",
        ]
    ),
    default="dashboard",
    help="Initial screen to display.",
)
@click.pass_context
def tui(ctx: click.Context, screen: str) -> None:
    """Launch interactive terminal user interface.

    The TUI provides a visual interface for managing and monitoring
    MADSci labs directly from the terminal.

    \b
    Examples:
        madsci tui                      Launch TUI on dashboard
        madsci tui --screen logs        Launch TUI on logs screen
        madsci tui --screen nodes       Launch TUI on nodes screen
        madsci tui --screen workflows   Launch TUI on workflows screen
    """
    try:
        from madsci.client.cli.tui import MadsciApp
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
        return

    # Get lab URL and context
    context = ctx.obj.get("context")
    lab_url = (
        str(context.lab_server_url)
        if context and context.lab_server_url
        else ctx.obj.get("lab_url", "http://localhost:8000/")
    )

    # Create and run the TUI app, starting on the requested screen
    app = MadsciApp(lab_url=lab_url, initial_screen=screen, context=context)
    result = app.run()

    # If user pressed Ctrl+P (return code 2), launch command palette
    if result is not None and app.return_code == 2:
        _launch_command_palette(ctx)


def _launch_command_palette(ctx: click.Context) -> None:
    """Launch Trogon command palette after TUI exit.

    Args:
        ctx: Click context.
    """
    try:
        from trogon import Trogon
    except ImportError:
        click.echo(
            "Trogon not available. Run 'madsci commands' after installing trogon."
        )
        return

    root_cmd = ctx.parent.command if ctx.parent else ctx.command
    root_ctx = ctx.parent or ctx
    Trogon(root_cmd, app_name="madsci", click_context=root_ctx).run()
