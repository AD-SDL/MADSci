"""Shared constants for the MADSci TUI screens."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from madsci.common.types.context_types import MadsciContext

# Default auto-refresh interval in seconds
AUTO_REFRESH_INTERVAL = 5.0

# Fallback service URLs (used when no MadsciContext is available)
DEFAULT_SERVICES = {
    "lab_manager": "http://localhost:8000/",
    "event_manager": "http://localhost:8001/",
    "experiment_manager": "http://localhost:8002/",
    "resource_manager": "http://localhost:8003/",
    "data_manager": "http://localhost:8004/",
    "workcell_manager": "http://localhost:8005/",
    "location_manager": "http://localhost:8006/",
}


def get_default_services(context: MadsciContext | None = None) -> dict[str, str]:
    """Build the service URL mapping from a MadsciContext, falling back to defaults.

    Args:
        context: Optional MadsciContext.  When provided, URLs are read from
            the context (which in turn consults env-vars and settings files).

    Returns:
        dict mapping service names to their base URLs.
    """
    if context is None:
        return dict(DEFAULT_SERVICES)

    return {
        "lab_manager": str(context.lab_server_url)
        if context.lab_server_url
        else DEFAULT_SERVICES["lab_manager"],
        "event_manager": str(context.event_server_url)
        if context.event_server_url
        else DEFAULT_SERVICES["event_manager"],
        "experiment_manager": str(context.experiment_server_url)
        if context.experiment_server_url
        else DEFAULT_SERVICES["experiment_manager"],
        "resource_manager": str(context.resource_server_url)
        if context.resource_server_url
        else DEFAULT_SERVICES["resource_manager"],
        "data_manager": str(context.data_server_url)
        if context.data_server_url
        else DEFAULT_SERVICES["data_manager"],
        "workcell_manager": str(context.workcell_server_url)
        if context.workcell_server_url
        else DEFAULT_SERVICES["workcell_manager"],
        "location_manager": str(context.location_server_url)
        if context.location_server_url
        else DEFAULT_SERVICES["location_manager"],
    }
