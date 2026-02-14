Module madsci.client.cli.tui.constants
======================================
Shared constants for the MADSci TUI screens.

Functions
---------

`get_default_services(config: MadsciCLIConfig | None = None) ‑> dict[str, str]`
:   Build the service URL mapping from a CLI config, falling back to defaults.

    Args:
        config: Optional CLI configuration.  When provided, URLs are read from
            the config (which in turn consults env-vars and config files).

    Returns:
        dict mapping service names to their base URLs.
