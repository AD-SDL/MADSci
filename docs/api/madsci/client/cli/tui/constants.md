Module madsci.client.cli.tui.constants
======================================
Shared constants for the MADSci TUI screens.

Functions
---------

`get_default_services(context: MadsciContext | None = None) ‑> dict[str, str]`
:   Build the service URL mapping from a MadsciContext, falling back to defaults.
    
    Args:
        context: Optional MadsciContext.  When provided, URLs are read from
            the context (which in turn consults env-vars and settings files).
    
    Returns:
        dict mapping service names to their base URLs.