"""Output formatting utilities for MADSci CLI.

Provides consistent output formatting helpers for CLI commands.
"""

import json
from typing import Any

import click
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.table import Table


def get_console(ctx: click.Context) -> Console:
    """Get Rich Console from Click context, with fallback.

    All CLI commands should use this function instead of
    creating their own Console or inlining ``ctx.obj.get(...)``.

    Args:
        ctx: Click context.

    Returns:
        Console instance from context, or a new default Console.
    """
    if ctx.obj and "console" in ctx.obj:
        return ctx.obj["console"]
    return Console()


def output_result(
    console: Console,
    data: Any,
    format: str = "text",
    title: str | None = None,
) -> None:
    """Output data in the requested format.

    Args:
        console: Rich console instance.
        data: Data to output.
        format: Output format (text, json, yaml).
        title: Optional title for formatted output.
    """
    if format == "json":
        console.print_json(json.dumps(data, default=str))
    elif format == "yaml":
        console.print(yaml.dump(data, default_flow_style=False))
    # Rich formatted output
    elif isinstance(data, dict):
        table = Table(title=title, show_header=False)
        table.add_column("Key", style="cyan")
        table.add_column("Value")
        for key, value in data.items():
            table.add_row(str(key), str(value))
        console.print(table)
    elif isinstance(data, list):
        for item in data:
            console.print(f"  \u2022 {item}")
    else:
        console.print(data)


def success(console: Console, message: str) -> None:
    """Print success message with green checkmark.

    Args:
        console: Rich console instance.
        message: Message to print.
    """
    console.print(f"[green]\u2713[/green] {message}")


def error(console: Console, message: str, details: str | None = None) -> None:
    """Print error message with red X.

    Args:
        console: Rich console instance.
        message: Error message.
        details: Optional additional details.
    """
    console.print(f"[red]\u2717[/red] {message}", style="red")
    if details:
        console.print(f"    [dim]{details}[/dim]")


def warning(console: Console, message: str, details: str | None = None) -> None:
    """Print warning message with yellow warning sign.

    Args:
        console: Rich console instance.
        message: Warning message.
        details: Optional additional details.
    """
    console.print(f"[yellow]\u26a0[/yellow] {message}", style="yellow")
    if details:
        console.print(f"    [dim]{details}[/dim]")


def info(console: Console, message: str) -> None:
    """Print info message with blue info icon.

    Args:
        console: Rich console instance.
        message: Info message.
    """
    console.print(f"[blue]\u2139[/blue] {message}")


def print_panel(
    console: Console,
    content: str,
    title: str | None = None,
    border_style: str = "blue",
) -> None:
    """Print content in a panel.

    Args:
        console: Rich console instance.
        content: Panel content.
        title: Optional panel title.
        border_style: Border color/style.
    """
    console.print(Panel(content, title=title, border_style=border_style))


def format_url(url: str) -> str:
    """Format a URL for display.

    Args:
        url: URL to format.

    Returns:
        Formatted URL string.
    """
    return f"[link={url}]{url}[/link]"
