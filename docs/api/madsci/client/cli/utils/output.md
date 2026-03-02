Module madsci.client.cli.utils.output
=====================================
Output formatting utilities for MADSci CLI.

Provides consistent output formatting helpers for CLI commands.

Functions
---------

`error(console: rich.console.Console, message: str, details: str | None = None) ‑> None`
:   Print error message with red X.
    
    Args:
        console: Rich console instance.
        message: Error message.
        details: Optional additional details.

`format_url(url: str) ‑> str`
:   Format a URL for display.
    
    Args:
        url: URL to format.
    
    Returns:
        Formatted URL string.

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

`output_result(console: rich.console.Console, data: Any, format: str = 'text', title: str | None = None) ‑> None`
:   Output data in the requested format.
    
    Args:
        console: Rich console instance.
        data: Data to output.
        format: Output format (text, json, yaml).
        title: Optional title for formatted output.

`print_panel(console: rich.console.Console, content: str, title: str | None = None, border_style: str = 'blue') ‑> None`
:   Print content in a panel.
    
    Args:
        console: Rich console instance.
        content: Panel content.
        title: Optional panel title.
        border_style: Border color/style.

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