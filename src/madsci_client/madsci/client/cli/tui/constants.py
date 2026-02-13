"""Shared constants for the MADSci TUI screens."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from madsci.client.cli.utils.config import MadsciCLIConfig

# Default auto-refresh interval in seconds
AUTO_REFRESH_INTERVAL = 5.0

# Fallback service URLs (used when no MadsciCLIConfig is available)
DEFAULT_SERVICES = {
    "lab_manager": "http://localhost:8000/",
    "event_manager": "http://localhost:8001/",
    "experiment_manager": "http://localhost:8002/",
    "resource_manager": "http://localhost:8003/",
    "data_manager": "http://localhost:8004/",
    "workcell_manager": "http://localhost:8005/",
    "location_manager": "http://localhost:8006/",
}


def get_default_services(config: MadsciCLIConfig | None = None) -> dict[str, str]:
    """Build the service URL mapping from a CLI config, falling back to defaults.

    Args:
        config: Optional CLI configuration.  When provided, URLs are read from
            the config (which in turn consults env-vars and config files).

    Returns:
        dict mapping service names to their base URLs.
    """
    if config is None:
        return dict(DEFAULT_SERVICES)

    return {
        "lab_manager": str(config.lab_url),
        "event_manager": str(config.event_manager_url),
        "experiment_manager": str(config.experiment_manager_url),
        "resource_manager": str(config.resource_manager_url),
        "data_manager": str(config.data_manager_url),
        "workcell_manager": str(config.workcell_manager_url),
        "location_manager": str(config.location_manager_url),
    }
