"""Lab Manager implementation using the new AbstractManagerBase class."""

from pathlib import Path
from typing import Any, Optional

import httpx
from classy_fastapi import get
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from madsci.common.context import get_current_madsci_context
from madsci.common.manager_base import AbstractManagerBase
from madsci.common.ownership import global_ownership_info
from madsci.common.types.context_types import MadsciContext
from madsci.common.types.lab_types import (
    LabHealth,
    LabManagerDefinition,
    LabManagerSettings,
)
from madsci.common.types.manager_types import ManagerHealth


class LabManager(AbstractManagerBase[LabManagerSettings, LabManagerDefinition]):
    """Lab Manager REST Server."""

    SETTINGS_CLASS = LabManagerSettings
    DEFINITION_CLASS = LabManagerDefinition

    def __init__(
        self,
        settings: Optional[LabManagerSettings] = None,
        definition: Optional[LabManagerDefinition] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the Lab Manager."""
        super().__init__(settings=settings, definition=definition, **kwargs)

        # Set up additional ownership context for lab
        self._setup_lab_ownership()

    def _setup_lab_ownership(self) -> None:
        """Setup lab-specific ownership information."""
        # Lab Manager also sets the lab_id in global ownership
        global_ownership_info.lab_id = self.definition.manager_id

    def create_server(self, **kwargs: Any) -> FastAPI:
        """Create the FastAPI server application with proper route order."""
        # Call parent method to get the basic app with routes registered
        app = super().create_server(**kwargs)

        # Mount static files AFTER API routes to ensure API routes take precedence
        if self.settings.dashboard_files_path:
            dashboard_path = Path(self.settings.dashboard_files_path).expanduser()
            if dashboard_path.exists():
                app.mount(
                    "/",
                    StaticFiles(directory=dashboard_path, html=True),
                )

        return app

    # Lab-specific endpoints

    @get("/health")
    def health_endpoint(self) -> ManagerHealth:
        """Health check endpoint for the Lab Manager."""
        return self.get_health()

    async def get_lab_health(self) -> LabHealth:
        """Get the health status of the entire lab, including all managers."""
        lab_health = LabHealth()
        manager_healths = {}

        # Initialize fields to ensure they're never None
        lab_health.managers = {}
        lab_health.total_managers = 0
        lab_health.healthy_managers = 0

        try:
            # Get the current context to find configured managers
            context = get_current_madsci_context()

            # Define manager URLs based on context settings
            manager_urls = {}

            if context.event_server_url:
                manager_urls["event_manager"] = str(context.event_server_url)

            if context.data_server_url:
                manager_urls["data_manager"] = str(context.data_server_url)

            if context.experiment_server_url:
                manager_urls["experiment_manager"] = str(context.experiment_server_url)

            if context.resource_server_url:
                manager_urls["resource_manager"] = str(context.resource_server_url)

            if context.workcell_server_url:
                manager_urls["workcell_manager"] = str(context.workcell_server_url)

            if context.location_server_url:
                manager_urls["location_manager"] = str(context.location_server_url)

            # Check each manager's health
            healthy_count, total_count = await self.check_each_managers_health(
                manager_healths, manager_urls
            )

            lab_health.managers = manager_healths
            lab_health.total_managers = total_count
            lab_health.healthy_managers = healthy_count

            # Overall lab health is healthy if more than half the managers are healthy
            lab_health.healthy = healthy_count > total_count / 2
            lab_health.description = (
                f"{healthy_count}/{total_count} managers are healthy"
            )

        except Exception as e:
            lab_health.healthy = False
            lab_health.description = f"Lab health check failed: {e!s}"

        return lab_health

    async def check_each_managers_health(
        self, manager_healths: dict, manager_urls: dict
    ) -> tuple[int, int]:
        """Checks the health of each manager given their URLs."""

        healthy_count = 0
        total_count = 0

        async with httpx.AsyncClient(timeout=5.0) as client:
            for manager_name, url in manager_urls.items():
                total_count += 1
                try:
                    # Remove trailing slash and add /health
                    health_url = url.rstrip("/") + "/health"
                    response = await client.get(health_url)
                    if response.status_code == 200:
                        health_data = response.json()
                        manager_healths[manager_name] = ManagerHealth.model_validate(
                            health_data
                        )
                        if health_data.get("healthy", False):
                            healthy_count += 1
                    else:
                        manager_healths[manager_name] = ManagerHealth(
                            healthy=False, description=f"HTTP {response.status_code}"
                        )
                except Exception as e:
                    manager_healths[manager_name] = ManagerHealth(
                        healthy=False, description=f"Failed to connect: {e!s}"
                    )

        return healthy_count, total_count

    @get("/lab_health")
    async def lab_health_endpoint(self) -> LabHealth:
        """Health check endpoint for the entire lab."""
        return await self.get_lab_health()

    @get("/context")
    async def get_context(self) -> MadsciContext:
        """Get the context of the lab server."""
        return get_current_madsci_context()

    @get("/definition")
    def get_definition(self) -> LabManagerDefinition:
        """Return the manager definition."""
        return self._definition


# Main entry point for running the server
if __name__ == "__main__":
    manager = LabManager()
    manager.run_server()
