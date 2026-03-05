"""
Abstract base class for MADSci Managers using classy-fastapi.

This module provides a base class for all MADSci manager services,
standardizing common patterns and reducing code duplication.
"""

import contextlib
import sys
from abc import ABCMeta
from importlib.metadata import version as pkg_version
from typing import Any, ContextManager, Generic, Optional, TypeVar

import uvicorn
from classy_fastapi import Routable, get
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from madsci.client.client_mixin import MadsciClientMixin
from madsci.client.event_client import EventClient
from madsci.common.context import get_current_madsci_context
from madsci.common.middleware import EventClientContextMiddleware, RateLimitMiddleware
from madsci.common.openapi_utils import deduplicate_discriminated_unions
from madsci.common.otel import (
    OtelBootstrapConfig,
    configure_otel,
    get_otel_runtime,
    instrument_fastapi,
    instrument_requests,
)
from madsci.common.ownership import global_ownership_info
from madsci.common.types.base_types import MadsciBaseSettings
from madsci.common.types.event_types import EventClientConfig, EventType
from madsci.common.types.manager_types import ManagerHealth, ManagerSettings
from madsci.common.utils import new_ulid_str

# Type variables for generic typing
SettingsT = TypeVar("SettingsT", bound=MadsciBaseSettings)


# Create a compatible metaclass for both ABC and Routable
class ManagerBaseMeta(ABCMeta, type(Routable)):
    """Metaclass that combines ABCMeta and Routable's metaclass."""


class AbstractManagerBase(
    MadsciClientMixin,
    Generic[SettingsT],
    Routable,
    metaclass=ManagerBaseMeta,
):
    """
    Abstract base class for MADSci manager services using classy-fastapi.

    This class provides common functionality for all managers including:
    - Settings management
    - Logging setup
    - FastAPI app configuration
    - Standard endpoints (health, settings)
    - CORS middleware
    - Server lifecycle management

    Type Parameters:
        SettingsT: The manager's settings class (must inherit from MadsciBaseSettings)

    Class Attributes:
        SETTINGS_CLASS: The settings class for this manager (set by subclasses)
    """

    # Class attributes to be set by subclasses
    SETTINGS_CLASS: Optional[type[MadsciBaseSettings]] = None

    def __init_subclass__(cls) -> None:
        """
        Initialize subclass and collect endpoints.

        This override handles the __abstractmethods__ issue that occurs when
        combining ABC with classy-fastapi's Routable in generic classes.
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
                    endpoints.append(endpoint)
            except AttributeError:
                # Some attributes may not be accessible during class construction
                pass
        cls._endpoints = endpoints

    def __init__(
        self,
        settings: Optional[SettingsT] = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize the manager base.

        Args:
            settings: Manager settings instance
            **kwargs: Additional arguments passed to subclasses
        """
        super().__init__()

        # Initialize settings
        self._settings = settings or self.create_default_settings()

        # Generate a manager_id if not provided
        if (
            isinstance(self._settings, ManagerSettings)
            and not self._settings.manager_id
        ):
            self._settings.manager_id = new_ulid_str()

        # Resolve identity from registry if enabled
        self._resolver = None
        if (
            isinstance(self._settings, ManagerSettings)
            and self._settings.enable_registry_resolution
        ):
            self._resolve_identity_from_registry()

        # Setup logging
        self.setup_logging()
        self.logger.info(
            "Manager settings loaded",
            event_type=EventType.MANAGER_START,
            settings=self._settings.model_dump_safe()
            if hasattr(self._settings, "model_dump_safe")
            else self._settings.model_dump(mode="json"),
        )
        self.logger.info(
            "MADSci context initialized",
            event_type=EventType.MANAGER_START,
            context=get_current_madsci_context().model_dump(mode="json"),
        )

        self._otel_runtime = None
        if getattr(self._settings, "otel_enabled", False):
            self._setup_otel()
        else:
            # If OTEL was configured elsewhere in the process (e.g., a shared
            # bootstrap in a multi-service runtime), keep access to the runtime
            # so spans can still be created.
            self._otel_runtime = get_otel_runtime()

        self._tracer = self._otel_runtime.tracer if self._otel_runtime else None

        # Setup ownership context
        self.setup_ownership()

        # Initialize manager-specific components
        self.initialize(**kwargs)

    def span(
        self, name: str, *, attributes: Optional[dict[str, Any]] = None
    ) -> ContextManager[Any]:
        """Create a best-effort span context manager.

        This is intended for higher-level manager operations (not every log line).
        """

        if self._tracer is None:
            return contextlib.nullcontext()
        return self._tracer.start_as_current_span(name, attributes=attributes)

    @property
    def settings(self) -> SettingsT:
        """Get the manager settings."""
        return self._settings

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

    def initialize(self, **kwargs: Any) -> None:
        """
        Initialize manager-specific components.

        This method is called during __init__ and can be overridden
        to perform manager-specific initialization.

        Args:
            **kwargs: Additional arguments from __init__
        """

    def setup_logging(self) -> None:
        """
        Setup logging for the manager using MadsciClientMixin.

        This method initializes the EventClient for manager logging.
        The EventClient is created via the mixin's lazy initialization.
        """
        # Set the name for the EventClient
        self.name = self._resolve_name()

        # Propagate manager's OTEL settings to the EventClient config
        # so that the EventClient will also export logs via OTLP
        if getattr(self._settings, "otel_enabled", False):
            self.event_client_config = EventClientConfig(
                name=self.name,
                otel_enabled=True,
                otel_service_name=getattr(self._settings, "otel_service_name", None),
                otel_exporter=getattr(self._settings, "otel_exporter", "console"),
                otel_endpoint=getattr(self._settings, "otel_endpoint", None),
                otel_protocol=getattr(self._settings, "otel_protocol", "grpc"),
            )

        # Use the mixin's event_client property (lazy initialization)
        # This creates the EventClient if it doesn't exist
        self._logger = self.event_client

    def _setup_otel(self) -> None:
        """Best-effort OTEL bootstrap for manager processes."""

        try:
            service_name = getattr(self._settings, "otel_service_name", None) or (
                f"madsci.{self.__class__.__name__.lower()}"
            )
            self._otel_runtime = configure_otel(
                OtelBootstrapConfig(
                    enabled=True,
                    service_name=service_name,
                    service_version="unknown",
                    exporter=getattr(self._settings, "otel_exporter", "console"),
                    otlp_endpoint=getattr(self._settings, "otel_endpoint", None),
                    otlp_protocol=getattr(self._settings, "otel_protocol", "grpc"),
                )
            )

            # Instrument outbound HTTP (requests) if optional deps are installed.
            instrument_requests(enabled=True)
        except Exception:
            self._otel_runtime = None
            self.logger.warning(
                "OpenTelemetry setup failed; continuing without OTEL",
                event_type=EventType.MANAGER_ERROR,
                exc_info=True,
            )

    def _resolve_name(self) -> str:
        """Resolve the manager name from settings.

        Checks settings.manager_name first, then falls back to the class name.
        """
        if isinstance(self._settings, ManagerSettings) and self._settings.manager_name:
            return self._settings.manager_name
        return self.__class__.__name__

    def _resolve_identity_from_registry(self) -> None:
        """Resolve manager identity from the ID Registry.

        Uses IdentityResolver to look up or create a stable ID for this
        manager. The resolved ID is written back to settings.manager_id.
        Resolution failures are non-fatal: a warning is logged and the
        settings' existing ID is kept.
        """
        try:
            # Lazy import to avoid circular dependencies
            from madsci.common.registry.identity_resolver import (  # noqa: PLC0415
                IdentityResolver,
            )

            lab_url = (
                self._settings.lab_url
                if isinstance(self._settings, ManagerSettings)
                else None
            )
            self._resolver = IdentityResolver(lab_url=lab_url)

            name = self._resolve_name()

            result = self._resolver.resolve_with_info(
                name=name,
                component_type="manager",
                metadata={"manager_class": self.__class__.__name__},
            )

            # Update the settings' ID field
            if isinstance(self._settings, ManagerSettings):
                self._settings.manager_id = result.id

        except Exception:
            import logging  # noqa: PLC0415

            logging.getLogger(__name__).warning(
                "Registry identity resolution failed; using settings ID",
                exc_info=True,
            )

    def release_identity(self) -> None:
        """Release the registry lock for this manager's identity.

        Should be called during shutdown to allow other instances to
        acquire the same name.
        """
        if self._resolver is None:
            return

        try:
            self._resolver.release(self._resolve_name())
        except Exception:
            import logging  # noqa: PLC0415

            logging.getLogger(__name__).warning(
                "Failed to release registry identity",
                exc_info=True,
            )

    def setup_ownership(self) -> None:
        """Setup ownership context for the manager."""
        if isinstance(self._settings, ManagerSettings):
            global_ownership_info.manager_id = self._settings.manager_id

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
            otel_enabled = bool(
                getattr(self._settings, "otel_enabled", False)
                and self._otel_runtime
                and self._otel_runtime.enabled
            )

            extras: dict[str, Any] = {}
            if getattr(self._settings, "otel_enabled", False):
                extras.update(
                    {
                        "otel.enabled": otel_enabled,
                        "otel.exporter_type": getattr(
                            self._settings, "otel_exporter", None
                        ),
                        "otel.endpoint": getattr(self._settings, "otel_endpoint", None),
                    }
                )

            # Basic health check - if we can create a ManagerHealth object,
            # the manager is at least partially functional
            return ManagerHealth(
                healthy=True,
                description="Manager is running normally.",
                **extras,
            )
        except Exception as e:
            return ManagerHealth(
                healthy=False, description=f"Health check failed: {e!s}"
            )

    def _resolve_package_version(self) -> str | None:
        """Resolve the installed package version for this manager."""
        try:
            # Use the class's qualname-derived module. When run as __main__,
            # type(self).__module__ is '__main__', so we fall back to the
            # actual module spec or the class's declared module path.
            module = type(self).__module__
            if module == "__main__":
                # Recover the real module name from the __spec__
                spec = sys.modules["__main__"].__spec__
                if spec and spec.name:
                    module = spec.name

            module_parts = module.split(".")
            if len(module_parts) >= 2:
                package_name = ".".join(module_parts[:2])
                return pkg_version(package_name)
        except Exception:
            return None

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
        health = self.get_health()
        if health.version is None:
            health.version = self._resolve_package_version()
        return health

    @get("/settings")
    def get_settings_endpoint(
        self,
        include_defaults: bool = True,
        include_schema: bool = False,
    ) -> dict[str, Any]:
        """
        Export current settings for backup/replication.

        This endpoint allows exporting the current manager settings in a format
        suitable for backup, documentation, or replicating the configuration
        to another environment. Secrets are always redacted from the API
        endpoint for safety.

        Args:
            include_defaults: If True, include fields with default values.
                             If False, only include non-default settings.
            include_schema: If True, include JSON schema for documentation.

        Returns:
            dict: Settings as a dictionary with sensitive fields redacted.
        """
        return self.get_settings_export(
            include_defaults=include_defaults,
            include_schema=include_schema,
            include_secrets=False,
        )

    def get_settings_export(
        self,
        include_defaults: bool = True,
        include_schema: bool = False,
        include_secrets: bool = False,
    ) -> dict[str, Any]:
        """
        Export current settings for backup/replication.

        This method allows programmatic access to the current manager settings
        in a format suitable for backup, documentation, or replicating the
        configuration to another environment.

        Sensitive fields are identified via field-level metadata:
        - Fields with ``json_schema_extra={"secret": True}``
        - Fields typed as ``SecretStr`` / ``SecretBytes``

        Args:
            include_defaults: If True, include fields with default values.
                             If False, only include non-default settings.
            include_schema: If True, include JSON schema for documentation.
            include_secrets: If True, include actual secret values.
                            Defaults to False (secrets are redacted).

        Returns:
            dict: Settings as a dictionary with the following structure:
                - "settings": The settings values (secrets redacted by default)
                - "schema" (optional): JSON schema if include_schema is True
                - "schema_title" (optional): Settings class name if include_schema is True
        """
        if hasattr(self._settings, "model_dump_safe"):
            data = self._settings.model_dump_safe(include_secrets=include_secrets)
        else:
            data = self._settings.model_dump(mode="json")

        if not include_defaults:
            # Only include fields that differ from defaults
            try:
                defaults = type(self._settings)().model_dump(mode="json")
                data = {k: v for k, v in data.items() if data.get(k) != defaults.get(k)}
            except Exception:
                import logging  # noqa: PLC0415

                logging.getLogger(__name__).debug(
                    "Could not create default settings instance for comparison",
                    exc_info=True,
                )

        result: dict[str, Any] = {"settings": data}

        if include_schema:
            # Include JSON schema for documentation purposes
            result["schema"] = type(self._settings).model_json_schema()
            result["schema_title"] = type(self._settings).__name__

        return result

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
            # Convert exempt IPs list to set, or use None to get defaults
            # Note: empty list [] should create empty set, not None
            exempt_ips = (
                set(self._settings.rate_limit_exempt_ips)
                if self._settings.rate_limit_exempt_ips is not None
                else None
            )

            app.add_middleware(
                RateLimitMiddleware,
                requests_limit=self._settings.rate_limit_requests,
                time_window=self._settings.rate_limit_window,
                short_requests_limit=self._settings.rate_limit_short_requests,
                short_time_window=self._settings.rate_limit_short_window,
                cleanup_interval=self._settings.rate_limit_cleanup_interval,
                exempt_ips=exempt_ips,
            )
            # Add exempt IPs info to log message
            actual_exempt_ips = (
                exempt_ips if exempt_ips is not None else {"127.0.0.1", "::1"}
            )
            self.logger.info(
                "Rate limiting enabled",
                event_type=EventType.MANAGER_START,
                rate_limit_requests=self._settings.rate_limit_requests,
                rate_limit_window_seconds=self._settings.rate_limit_window,
                short_requests_limit=self._settings.rate_limit_short_requests,
                short_time_window_seconds=self._settings.rate_limit_short_window,
                exempt_ips=sorted(actual_exempt_ips) if actual_exempt_ips else [],
            )

        # Add CORS middleware by default
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=False,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Add EventClient context middleware for hierarchical logging
        # This establishes per-request context that includes request_id, path, etc.
        manager_name = self._resolve_name()
        app.add_middleware(
            EventClientContextMiddleware,
            manager_name=manager_name,
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
        manager_name = self._resolve_name()
        manager_description = (
            self._settings.manager_description
            if isinstance(self._settings, ManagerSettings)
            and self._settings.manager_description
            else f"{manager_name} Manager"
        )

        app = FastAPI(
            title=manager_name,
            description=manager_description,
            **kwargs,
        )

        # Configure the app (middleware, etc.)
        self.configure_app(app)

        # Instrument inbound HTTP (FastAPI) if OTEL is enabled.
        if self._otel_runtime and self._otel_runtime.enabled:
            instrument_fastapi(app, enabled=True)

        # Include the router from this Routable class
        app.include_router(self.router)

        # Wrap the OpenAPI schema generator so that the /docs and /redoc
        # endpoints serve a deduplicated spec.  Pydantic inlines discriminated
        # unions at every usage site; for recursive types this creates circular
        # schemas that crash Swagger UI and Redoc.
        _original_openapi = app.openapi

        def _patched_openapi() -> dict:
            schema = _original_openapi()
            deduplicate_discriminated_unions(schema)
            return schema

        app.openapi = _patched_openapi  # type: ignore[method-assign]

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
                self.logger.info(
                    "Uvicorn workers configured",
                    event_type=EventType.MANAGER_START,
                    uvicorn_workers=self._settings.uvicorn_workers,
                )

            if self._settings.uvicorn_limit_concurrency is not None:
                uvicorn_kwargs.setdefault(
                    "limit_concurrency", self._settings.uvicorn_limit_concurrency
                )
                self.logger.info(
                    "Uvicorn concurrency limit configured",
                    event_type=EventType.MANAGER_START,
                    uvicorn_limit_concurrency=self._settings.uvicorn_limit_concurrency,
                )

            if self._settings.uvicorn_limit_max_requests is not None:
                uvicorn_kwargs.setdefault(
                    "limit_max_requests", self._settings.uvicorn_limit_max_requests
                )
                self.logger.info(
                    "Uvicorn max requests configured",
                    event_type=EventType.MANAGER_START,
                    uvicorn_limit_max_requests=self._settings.uvicorn_limit_max_requests,
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
