"""
Abstract base class for MADSci Managers using classy-fastapi.

This module provides a base class for all MADSci manager services,
standardizing common patterns and reducing code duplication.
"""

from abc import ABCMeta
from pathlib import Path
from typing import Any, Generic, Optional, TypeVar

import uvicorn
from classy_fastapi import Routable, get
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from madsci.client.event_client import EventClient
from madsci.common.context import get_current_madsci_context
from madsci.common.middleware import RateLimitMiddleware
from madsci.common.ownership import global_ownership_info
from madsci.common.types.base_types import MadsciBaseModel, MadsciBaseSettings
from madsci.common.types.manager_types import ManagerHealth, ManagerSettings

# Type variables for generic typing
SettingsT = TypeVar("SettingsT", bound=MadsciBaseSettings)
DefinitionT = TypeVar("DefinitionT", bound=MadsciBaseModel)


# Create a compatible metaclass for both ABC and Routable
class ManagerBaseMeta(ABCMeta, type(Routable)):
    """Metaclass that combines ABCMeta and Routable's metaclass."""


class AbstractManagerBase(
    Generic[SettingsT, DefinitionT], Routable, metaclass=ManagerBaseMeta
):
    """
    Abstract base class for MADSci manager services using classy-fastapi.

    This class provides common functionality for all managers including:
    - Settings and definition management
    - Logging setup
    - FastAPI app configuration
    - Standard endpoints (info, definition)
    - CORS middleware
    - Server lifecycle management

    Type Parameters:
        SettingsT: The manager's settings class (must inherit from MadsciBaseSettings)
        DefinitionT: The manager's definition class (must inherit from MadsciBaseModel)

    Class Attributes:
        SETTINGS_CLASS: The settings class for this manager (set by subclasses)
        DEFINITION_CLASS: The definition class for this manager (set by subclasses)
        ENABLE_ROOT_DEFINITION_ENDPOINT: Whether to enable the root definition endpoint (default: True)
    """

    # Class attributes to be set by subclasses
    SETTINGS_CLASS: Optional[type[MadsciBaseSettings]] = None
    DEFINITION_CLASS: Optional[type[MadsciBaseModel]] = None
    ENABLE_ROOT_DEFINITION_ENDPOINT: bool = True

    def __init_subclass__(cls) -> None:
        """
        Initialize subclass and collect endpoints.

        This override handles the __abstractmethods__ issue that occurs when
        combining ABC with classy-fastapi's Routable in generic classes.
        Also conditionally excludes the root endpoint based on ENABLE_ROOT_DEFINITION_ENDPOINT.
        """
        # Import here to avoid circular dependencies and to match classy-fastapi's pattern
        import inspect  # noqa: PLC0415

        from classy_fastapi.decorators import EndpointDefinition  # noqa: PLC0415

        endpoints: list[EndpointDefinition] = []
        for obj_name in dir(cls):
            # Skip __abstractmethods__ to avoid AttributeError during ABC construction
            if obj_name == "__abstractmethods__":
                continue
            try:
                obj = getattr(cls, obj_name)
                if inspect.isfunction(obj) and hasattr(obj, "_endpoint"):
                    endpoint = obj._endpoint
                    # Skip root definition endpoint if disabled
                    if (
                        not cls.ENABLE_ROOT_DEFINITION_ENDPOINT
                        and obj_name == "get_definition_root"
                        and endpoint.path == "/"
                    ):
                        continue
                    endpoints.append(endpoint)
            except AttributeError:
                # Some attributes may not be accessible during class construction
                pass
        cls._endpoints = endpoints

    def __init__(
        self,
        settings: Optional[SettingsT] = None,
        definition: Optional[DefinitionT] = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize the manager base.

        Args:
            settings: Manager settings instance
            definition: Manager definition instance
            **kwargs: Additional arguments passed to subclasses
        """
        super().__init__()

        # Initialize settings and definition
        self._settings = settings or self.create_default_settings()
        self._definition = definition or self.load_or_create_definition()

        # Setup logging
        self.setup_logging()
        self.logger.info(self._settings)
        self.logger.info(self._definition)
        self.logger.info(get_current_madsci_context())

        # Setup ownership context
        self.setup_ownership()

        # Initialize manager-specific components
        self.initialize(**kwargs)

    @property
    def settings(self) -> SettingsT:
        """Get the manager settings."""
        return self._settings

    @property
    def definition(self) -> DefinitionT:
        """Get the manager definition."""
        return self._definition

    @property
    def logger(self) -> EventClient:
        """Get the logger instance."""
        return self._logger

    def create_default_settings(self) -> SettingsT:
        """Create default settings instance for this manager."""
        if self.SETTINGS_CLASS is None:
            raise NotImplementedError(
                f"{self.__class__.__name__} must set SETTINGS_CLASS class attribute"
            )
        return self.SETTINGS_CLASS()

    def get_definition_path(self) -> Path:
        """Get the path to the definition file."""
        return Path(self.settings.manager_definition).expanduser()

    def create_default_definition(self) -> DefinitionT:
        """Create a default definition instance for this manager."""
        if self.DEFINITION_CLASS is None:
            raise NotImplementedError(
                f"{self.__class__.__name__} must set DEFINITION_CLASS class attribute"
            )
        return self.DEFINITION_CLASS(name=f"Default {self.__class__.__name__}")

    def initialize(self, **kwargs: Any) -> None:
        """
        Initialize manager-specific components.

        This method is called during __init__ and can be overridden
        to perform manager-specific initialization.

        Args:
            **kwargs: Additional arguments from __init__
        """

    def setup_logging(self) -> None:
        """Setup logging for the manager."""
        self._logger = EventClient(name=f"{self._definition.name}")

    def setup_ownership(self) -> None:
        """Setup ownership context for the manager."""
        global_ownership_info.manager_id = self._definition.manager_id

    def get_health(self) -> ManagerHealth:
        """
        Get the health status of this manager.

        This base implementation returns a healthy status.
        Subclasses should override this method to check specific
        dependencies like databases, external services, etc.

        Returns:
            ManagerHealth: The current health status
        """
        try:
            # Basic health check - if we can create a ManagerHealth object,
            # the manager is at least partially functional
            return ManagerHealth(
                healthy=True,
                description="Manager is running normally.",
            )
        except Exception as e:
            return ManagerHealth(
                healthy=False, description=f"Health check failed: {e!s}"
            )

    @get("/health")
    def health_endpoint(self) -> ManagerHealth:
        """
        Health check endpoint for the manager.

        This endpoint is automatically inherited by all manager subclasses.
        Managers that override get_health() will automatically have their
        custom health checks exposed through this endpoint.

        Returns:
            ManagerHealth: The current health status
        """
        return self.get_health()

    @get("/")
    def get_definition_root(self) -> DefinitionT:
        """
        Return the manager definition at the root endpoint.

        This endpoint is automatically inherited by all manager subclasses.

        Returns:
            DefinitionT: The manager definition
        """
        return self.definition

    @get("/definition")
    def get_definition_alt(self) -> DefinitionT:
        """
        Return the manager definition at the /definition endpoint.

        This endpoint is automatically inherited by all manager subclasses.

        Returns:
            DefinitionT: The manager definition
        """
        return self.definition

    def load_or_create_definition(self) -> DefinitionT:
        """Load definition from file or create default."""
        # Get settings first (create if not set)
        if not hasattr(self, "_settings") or self._settings is None:
            self._settings = self.create_default_settings()

        def_path = self.get_definition_path()
        if def_path.exists():
            definition = self.DEFINITION_CLASS.from_yaml(def_path)
        else:
            definition = self.create_default_definition()

        # Only log if logger is initialized
        if hasattr(self, "_logger"):
            self.logger.info(f"Writing to definition file: {def_path}")
        definition.to_yaml(def_path)
        return definition

    def configure_app(self, app: FastAPI) -> None:
        """
        Configure the FastAPI application.

        This method can be overridden to add additional middleware,
        exception handlers, or other app configuration.

        Args:
            app: The FastAPI application instance
        """
        # Add rate limiting middleware if enabled
        # Check if settings has rate limiting configuration (ManagerSettings-based)
        if (
            isinstance(self._settings, ManagerSettings)
            and self._settings.rate_limit_enabled
        ):
            app.add_middleware(
                RateLimitMiddleware,
                requests_limit=self._settings.rate_limit_requests,
                time_window=self._settings.rate_limit_window,
            )
            self.logger.info(
                f"Rate limiting enabled: {self._settings.rate_limit_requests} requests "
                f"per {self._settings.rate_limit_window} seconds"
            )

        # Add CORS middleware by default
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=False,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Server creation and lifecycle methods

    def create_server(self, **kwargs: Any) -> FastAPI:
        """
        Create the FastAPI server application.

        Args:
            **kwargs: Additional arguments for app configuration

        Returns:
            FastAPI: The configured FastAPI application
        """
        app = FastAPI(
            title=self._definition.name,
            description=self._definition.description
            or f"{self._definition.name} Manager",
            **kwargs,
        )

        # Configure the app (middleware, etc.)
        self.configure_app(app)

        # Include the router from this Routable class
        app.include_router(self.router)

        return app

    def run_server(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        **uvicorn_kwargs: Any,
    ) -> None:
        """
        Run the server using uvicorn.

        Args:
            host: Host to bind to (defaults to settings)
            port: Port to bind to (defaults to settings)
            **uvicorn_kwargs: Additional arguments for uvicorn.run()
        """
        app = self.create_server()

        # Get host and port from settings if not provided
        server_url = self._settings.server_url
        if server_url:
            default_host = getattr(server_url, "host", "localhost")
            default_port = getattr(server_url, "port", 8000)
        else:
            default_host = "localhost"
            default_port = 8000

        # Apply resource constraints from settings if available (ManagerSettings-based)
        if isinstance(self._settings, ManagerSettings):
            if self._settings.uvicorn_workers is not None:
                uvicorn_kwargs.setdefault("workers", self._settings.uvicorn_workers)
                self.logger.info(f"Uvicorn workers: {self._settings.uvicorn_workers}")

            if self._settings.uvicorn_limit_concurrency is not None:
                uvicorn_kwargs.setdefault(
                    "limit_concurrency", self._settings.uvicorn_limit_concurrency
                )
                self.logger.info(
                    f"Uvicorn concurrency limit: {self._settings.uvicorn_limit_concurrency}"
                )

            if self._settings.uvicorn_limit_max_requests is not None:
                uvicorn_kwargs.setdefault(
                    "limit_max_requests", self._settings.uvicorn_limit_max_requests
                )
                self.logger.info(
                    f"Uvicorn max requests per worker: {self._settings.uvicorn_limit_max_requests}"
                )

        uvicorn.run(
            app,
            host=host or default_host,
            port=port or default_port,
            **uvicorn_kwargs,
        )


def create_manager_server(
    manager_class: type[AbstractManagerBase], **kwargs: Any
) -> FastAPI:
    """
    Factory function to create a manager server.

    This provides a consistent interface for creating manager servers
    while maintaining the existing factory function pattern.

    Args:
        manager_class: The manager class to instantiate
        **kwargs: Arguments to pass to the manager constructor

    Returns:
        FastAPI: The configured FastAPI application
    """
    manager = manager_class(**kwargs)
    return manager.create_server()
