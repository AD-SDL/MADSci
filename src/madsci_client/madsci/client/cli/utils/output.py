"""Output formatting utilities for MADSci CLI.

Provides consistent output formatting helpers for CLI commands,
including multi-format output (text / JSON / YAML / quiet) and
typed table column definitions.
"""

from __future__ import annotations

import json
from enum import Enum
from typing import Any, NamedTuple, Sequence

import click
import yaml
from pydantic import BaseModel
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# ---------------------------------------------------------------------------
# Output format enum
# ---------------------------------------------------------------------------


class OutputFormat(str, Enum):
    """Supported CLI output formats."""

    TABLE = "table"
    JSON = "json"
    YAML = "yaml"
    QUIET = "quiet"


# ---------------------------------------------------------------------------
# Column definition for table rendering
# ---------------------------------------------------------------------------


class ColumnDef(NamedTuple):
    """Definition of a single table column.

    Attributes:
        header: Column header text.
        key: Attribute / dictionary key to extract the value from each row.
        style: Optional Rich style for the column (e.g. ``"cyan"``).
        max_width: Optional maximum character width.
    """

    header: str
    key: str
    style: str | None = None
    max_width: int | None = None


# ---------------------------------------------------------------------------
# Format determination helper
# ---------------------------------------------------------------------------


def determine_output_format(ctx: click.Context) -> OutputFormat:
    """Determine the output format from Click context flags.

    Precedence: ``--json`` > ``--yaml`` > ``-q``/``--quiet`` > table (default).

    Args:
        ctx: Click context populated by the top-level ``madsci`` group.

    Returns:
        The :class:`OutputFormat` to use.
    """
    obj = ctx.obj or {}
    if obj.get("json"):
        return OutputFormat.JSON
    if obj.get("yaml"):
        return OutputFormat.YAML
    if obj.get("quiet"):
        return OutputFormat.QUIET
    return OutputFormat.TABLE


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------


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


def _serialize(data: Any) -> Any:
    """Convert *data* to a JSON-safe Python structure.

    Handles Pydantic models, lists of models, and plain dicts/values.
    """
    if isinstance(data, BaseModel):
        return data.model_dump(mode="json")
    if isinstance(data, list):
        return [_serialize(item) for item in data]
    return data


def _output_quiet(console: Console, data: Any, quiet_key: str | None) -> None:
    """Render data in quiet mode (minimal output)."""
    serialised = _serialize(data)
    if quiet_key and isinstance(serialised, dict):
        console.print(str(serialised.get(quiet_key, "")))
    elif isinstance(serialised, list) and quiet_key:
        for item in serialised:
            val = item.get(quiet_key, item) if isinstance(item, dict) else item
            console.print(str(val))
    else:
        console.print(str(serialised))


def _output_table(
    console: Console,
    data: Any,
    title: str | None,
    columns: Sequence[ColumnDef] | None,
) -> None:
    """Render data as a Rich table or fallback format."""
    # List with column definitions -> proper table
    if columns and isinstance(data, (list, tuple)) and data:
        _print_column_table(console, data, title, columns)
        return

    # Single Pydantic model or dict -> key/value table
    mapping = data.model_dump(mode="json") if isinstance(data, BaseModel) else data
    if isinstance(mapping, dict):
        _print_kv_table(console, mapping, title)
        return

    # Plain list (no column defs) -> bullet list
    if isinstance(data, list):
        for item in data:
            console.print(f"  \u2022 {item}")
        return

    # Scalar fallback
    console.print(data)


def _print_column_table(
    console: Console,
    data: Sequence[Any],
    title: str | None,
    columns: Sequence[ColumnDef],
) -> None:
    """Render a list of items as a table with column definitions."""
    table = Table(title=title)
    for col in columns:
        table.add_column(col.header, style=col.style or "", max_width=col.max_width)

    for item in data:
        row_dict = _serialize(item) if isinstance(item, BaseModel) else item
        if isinstance(row_dict, dict):
            table.add_row(*(str(row_dict.get(col.key, "")) for col in columns))
        else:
            table.add_row(str(row_dict))
    console.print(table)


def _print_kv_table(
    console: Console,
    mapping: dict[str, Any],
    title: str | None,
) -> None:
    """Render a dict as a two-column key/value table."""
    table = Table(title=title, show_header=False)
    table.add_column("Key", style="cyan")
    table.add_column("Value")
    for key, value in mapping.items():
        table.add_row(str(key), str(value))
    console.print(table)


def output_result(
    console: Console,
    data: Any,
    format: str = "text",
    title: str | None = None,
    columns: Sequence[ColumnDef] | None = None,
    quiet_key: str | None = None,
) -> None:
    """Output data in the requested format.

    Enhanced to support:
    * Pydantic model auto-serialisation
    * :class:`ColumnDef`-based table rendering
    * ``quiet`` mode (prints only the *quiet_key* value)
    * Lists of Pydantic models

    Args:
        console: Rich console instance.
        data: Data to output (dict, list, Pydantic model, or scalar).
        format: Output format (``"text"``, ``"json"``, ``"yaml"``, ``"quiet"``).
        title: Optional title for formatted output.
        columns: Optional column definitions for table rendering.
        quiet_key: Key whose value is printed in ``quiet`` mode.
    """
    if format == "quiet":
        _output_quiet(console, data, quiet_key)
    elif format == "json":
        console.print_json(json.dumps(_serialize(data), default=str))
    elif format == "yaml":
        console.print(yaml.dump(_serialize(data), default_flow_style=False))
    else:
        _output_table(console, data, title, columns)


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
