Module madsci.client.cli.utils.formatting
=========================================
Shared formatting utilities for MADSci CLI and TUI.

Provides centralised status styling, timestamp/duration formatting, and
text truncation helpers.  Used by both CLI commands and TUI screens to
ensure consistent visual presentation.

Functions
---------

`format_duration(seconds: float | None) ‑> str`
:   Format a duration in seconds as a human-readable string.
    
    Output forms:
    * ``Xh XXm XXs`` when hours > 0
    * ``XXm XXs`` otherwise
    * ``"-"`` for ``None`` or negative values
    
    Args:
        seconds: Duration in seconds.
    
    Returns:
        Formatted duration string.

`format_status_colored(status: str, text: str | None = None) ‑> str`
:   Return Rich markup for coloured status text.
    
    If *text* is ``None``, the *status* string itself is used as the
    display text.
    
    Args:
        status: Status string used for colour lookup.
        text: Optional override text to colour.
    
    Returns:
        Rich markup string.

`format_status_icon(status: str) ‑> str`
:   Return Rich markup for a status icon.
    
    Example output: ``"[green]\u25cf[/green]"``.
    
    Args:
        status: Status string.
    
    Returns:
        Rich markup string.

`format_timestamp(ts: Any, short: bool = False) ‑> str`
:   Format a timestamp for display.
    
    Handles ``datetime`` objects, ISO-format strings (with optional
    ``Z`` suffix), and arbitrary objects (via ``str()`` fallback).
    
    Args:
        ts: Timestamp value.
        short: If ``True``, use ``HH:MM:SS.mmm`` format.
    
    Returns:
        Formatted timestamp string or ``"-"`` for ``None`` inputs.

`get_status_style(status: str) ‑> tuple[str, str]`
:   Get the ``(icon, colour)`` tuple for a status string.
    
    Performs a case-insensitive lookup against :data:`STATUS_STYLES`.
    Returns the ``unknown`` entry for unrecognised statuses.
    
    Args:
        status: Status string (e.g. ``"healthy"``, ``"running"``).
    
    Returns:
        ``(icon_char, rich_colour_name)`` tuple.

`truncate(text: str, max_len: int = 50) ‑> str`
:   Truncate *text* with an ellipsis if it exceeds *max_len*.
    
    Args:
        text: Input text.
        max_len: Maximum allowed length (including the ellipsis).
    
    Returns:
        Truncated string.