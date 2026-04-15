Module madsci.client.cli.tui.widgets.log_viewer
===============================================
LogViewer widget for MADSci TUI.

Rich log viewer with follow mode, deduplication, and pluggable
formatting. Extracts the log display pattern from the Logs screen.

Classes
-------

`LogViewer(*, max_seen: int = 10000, **kwargs: Any)`
:   Rich log viewer with follow mode and deduplication.
    
    Features:
    - Level-based colouring via a pluggable formatter.
    - Follow mode: auto-scroll to the latest entry.
    - Deduplication: bounded ``OrderedDict`` of seen IDs (default 10k).
    - Pluggable formatter via :meth:`set_formatter`.
    
    Usage::
    
        viewer = LogViewer()
        count = viewer.append_entries(entries, id_key="event_id")
        viewer.follow_mode = True
        viewer.clear()
    
    Initialize the log viewer.
    
    Args:
        max_seen: Maximum number of entry IDs to track for
            deduplication. Oldest entries are evicted when this
            limit is reached.
        **kwargs: Additional keyword arguments forwarded to ``Widget``.

    ### Ancestors (in MRO)

    * textual.widget.Widget
    * textual.dom.DOMNode
    * textual.message_pump.MessagePump

    ### Class variables

    `DEFAULT_CSS`
    :

    `can_focus`
    :

    `can_focus_children`
    :

    ### Instance variables

    `entry_count: int`
    :   Return the number of unique log entries seen so far.

    `follow_mode: Reactive[ReactiveType] | ReactiveType`
    :   Create a reactive attribute.
        
        Args:
            default: A default value or callable that returns a default.
            layout: Perform a layout on change.
            repaint: Perform a repaint on change.
            init: Call watchers on initialize (post mount).
            always_update: Call watchers even when the new value equals the old value.
            recompose: Compose the widget again when the attribute changes.
            bindings: Refresh bindings when the reactive changes.
            toggle_class: An optional TCSS classname(s) to toggle based on the truthiness of the value.

    ### Methods

    `append_entries(self, entries: list[dict[str, Any]], id_key: str = 'event_id') ‑> int`
    :   Append new log entries with deduplication.
        
        Args:
            entries: List of log entry dictionaries.
            id_key: Key used to extract unique IDs from entries. Falls
                back to ``"_id"`` then ``hash(str(entry))`` if the key
                is missing.
        
        Returns:
            Number of *new* (non-duplicate) entries that were appended.

    `clear(self) ‑> None`
    :   Clear all displayed log entries and the dedup cache.

    `compose(self) ‑> Iterable[textual.widget.Widget]`
    :   Compose the log viewer.

    `set_formatter(self, formatter: Callable[[dict[str, Any]], str]) ‑> None`
    :   Set a custom entry formatter.
        
        Args:
            formatter: Callable that takes an entry dict and returns a
                Rich-formatted string.

    `watch_follow_mode(self, value: bool) ‑> None`
    :   Scroll to end when follow mode is enabled.