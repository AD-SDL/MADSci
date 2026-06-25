Module madsci.client.cli.utils.output
=====================================
Output formatting utilities for MADSci CLI.

Provides consistent output formatting helpers for CLI commands,
including multi-format output (text / JSON / YAML / quiet) and
typed table column definitions.

Functions
---------

`determine_output_format(ctx: click.Context) ‑> madsci.client.cli.utils.output.OutputFormat`
:   Determine the output format from Click context flags.
    
    Precedence: ``--json`` > ``--yaml`` > ``-q``/``--quiet`` > table (default).
    
    Args:
        ctx: Click context populated by the top-level ``madsci`` group.
    
    Returns:
        The :class:`OutputFormat` to use.

`error(console: Console, message: str, details: str | None = None) ‑> None`
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

`get_console(ctx: click.Context) ‑> rich.console.Console`
:   Get Rich Console from Click context, with fallback.
    
    All CLI commands should use this function instead of
    creating their own Console or inlining ``ctx.obj.get(...)``.
    
    Args:
        ctx: Click context.
    
    Returns:
        Console instance from context, or a new default Console.

`info(console: Console, message: str) ‑> None`
:   Print info message with blue info icon.
    
    Args:
        console: Rich console instance.
        message: Info message.

`output_result(console: Console, data: Any, format: str = 'text', title: str | None = None, columns: Sequence[ColumnDef] | None = None, quiet_key: str | None = None) ‑> None`
:   Output data in the requested format.
    
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

`print_panel(console: Console, content: str, title: str | None = None, border_style: str = 'blue') ‑> None`
:   Print content in a panel.
    
    Args:
        console: Rich console instance.
        content: Panel content.
        title: Optional panel title.
        border_style: Border color/style.

`success(console: Console, message: str) ‑> None`
:   Print success message with green checkmark.
    
    Args:
        console: Rich console instance.
        message: Message to print.

`warning(console: Console, message: str, details: str | None = None) ‑> None`
:   Print warning message with yellow warning sign.
    
    Args:
        console: Rich console instance.
        message: Warning message.
        details: Optional additional details.

Classes
-------

`ColumnDef(header: ForwardRef('str'), key: ForwardRef('str'), style: ForwardRef('str | None') = None, max_width: ForwardRef('int | None') = None)`
:   Definition of a single table column.
    
    Attributes:
        header: Column header text.
        key: Attribute / dictionary key to extract the value from each row.
        style: Optional Rich style for the column (e.g. ``"cyan"``).
        max_width: Optional maximum character width.

    ### Ancestors (in MRO)

    * builtins.tuple

    ### Instance variables

    `header: str`
    :   Alias for field number 0

    `key: str`
    :   Alias for field number 1

    `max_width: int | None`
    :   Alias for field number 3

    `style: str | None`
    :   Alias for field number 2

`OutputFormat(value, names=None, *, module=None, qualname=None, type=None, start=1)`
:   Supported CLI output formats.

    ### Ancestors (in MRO)

    * builtins.str
    * enum.Enum

    ### Class variables

    `JSON`
    :

    `QUIET`
    :

    `TABLE`
    :

    `YAML`
    :