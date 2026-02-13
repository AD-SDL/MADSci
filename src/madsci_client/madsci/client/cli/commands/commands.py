"""MADSci CLI command palette using Trogon.

Launches Trogon's interactive command builder, which auto-generates
TUI forms from Click commands for building and executing CLI commands.
"""

import click


@click.command()
@click.pass_context
def commands(ctx: click.Context) -> None:
    """Launch interactive command palette.

    Opens a Trogon-powered TUI that auto-generates interactive forms
    for all MADSci CLI commands. Navigate the command tree, fill in
    parameters, and execute commands interactively.

    \b
    Examples:
        madsci commands       Launch command palette
    """
    try:
        from trogon import Trogon
    except ImportError as e:
        console = ctx.obj.get("console")
        if console:
            console.print(
                "[red]Error: Trogon not installed.[/red]\n\n"
                "Install with:\n"
                "  pip install trogon\n\n"
                f"Details: {e}"
            )
        else:
            click.echo(f"Error: Trogon not installed. Details: {e}")
        ctx.exit(1)
        return

    # Get the root command group (the `madsci` group)
    root_cmd = ctx.parent.command if ctx.parent else ctx.command
    root_ctx = ctx.parent or ctx

    Trogon(root_cmd, app_name="madsci", click_context=root_ctx).run()
