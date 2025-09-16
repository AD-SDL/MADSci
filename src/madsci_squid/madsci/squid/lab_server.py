"""Lab Manager implementation using the new AbstractManagerBase class."""

from pathlib import Path
from typing import Any, Optional

from classy_fastapi import get
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from madsci.common.context import get_current_madsci_context
from madsci.common.manager_base import AbstractManagerBase
from madsci.common.ownership import global_ownership_info
from madsci.common.types.context_types import MadsciContext
from madsci.common.types.lab_types import LabManagerDefinition, LabManagerSettings


class LabManager(AbstractManagerBase[LabManagerSettings, LabManagerDefinition]):
    """Lab Manager REST Server."""

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

    def create_default_settings(self) -> LabManagerSettings:
        """Create default settings instance for this manager."""
        return LabManagerSettings()

    def get_definition_path(self) -> Path:
        """Get the path to the definition file."""
        return Path(self.settings.manager_definition).expanduser()

    def create_default_definition(self) -> LabManagerDefinition:
        """Create a default definition instance for this manager."""
        return LabManagerDefinition()

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
