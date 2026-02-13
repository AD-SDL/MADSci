"""Shared constants for the MADSci TUI screens."""

# Default auto-refresh interval in seconds
AUTO_REFRESH_INTERVAL = 5.0

# Default service URLs
DEFAULT_SERVICES = {
    "lab_manager": "http://localhost:8000/",
    "event_manager": "http://localhost:8001/",
    "experiment_manager": "http://localhost:8002/",
    "resource_manager": "http://localhost:8003/",
    "data_manager": "http://localhost:8004/",
    "workcell_manager": "http://localhost:8005/",
    "location_manager": "http://localhost:8006/",
}

# Default workcell manager URL
WORKCELL_MANAGER_URL = DEFAULT_SERVICES["workcell_manager"]

# Default event manager URL
EVENT_MANAGER_URL = DEFAULT_SERVICES["event_manager"]
