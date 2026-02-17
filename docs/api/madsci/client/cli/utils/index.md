Module madsci.client.cli.utils
==============================
CLI utilities for MADSci.

This module provides common utilities for CLI commands.

Sub-modules
-----------
* madsci.client.cli.utils.output

Functions
---------

`error(console: rich.console.Console, message: str, details: str | None = None) ‑> None`
:   Print error message with red X.

    Args:
        console: Rich console instance.
        message: Error message.
        details: Optional additional details.

`get_console(ctx: click.core.Context) ‑> rich.console.Console`
:   Get Rich Console from Click context, with fallback.

    All CLI commands should use this function instead of
    creating their own Console or inlining ``ctx.obj.get(...)``.

    Args:
        ctx: Click context.

    Returns:
        Console instance from context, or a new default Console.

`info(console: rich.console.Console, message: str) ‑> None`
:   Print info message with blue info icon.

    Args:
        console: Rich console instance.
        message: Info message.

`success(console: rich.console.Console, message: str) ‑> None`
:   Print success message with green checkmark.

    Args:
        console: Rich console instance.
        message: Message to print.

`warning(console: rich.console.Console, message: str, details: str | None = None) ‑> None`
:   Print warning message with yellow warning sign.

    Args:
        console: Rich console instance.
        message: Warning message.
        details: Optional additional details.
