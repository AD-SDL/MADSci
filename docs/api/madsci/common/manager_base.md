Module madsci.common.manager_base
=================================
Abstract base class for MADSci Managers using classy-fastapi.

This module provides a base class for all MADSci manager services,
standardizing common patterns and reducing code duplication.

Functions
---------

`create_manager_server(manager_class: type[madsci.common.manager_base.AbstractManagerBase], **kwargs: Any) ‑> fastapi.applications.FastAPI`
:   Factory function to create a manager server.

    This provides a consistent interface for creating manager servers
    while maintaining the existing factory function pattern.

    Args:
        manager_class: The manager class to instantiate
        **kwargs: Arguments to pass to the manager constructor

    Returns:
        FastAPI: The configured FastAPI application

Classes
-------

`AbstractManagerBase(settings: ~SettingsT | None = None, definition: ~DefinitionT | None = None, **kwargs: Any)`
:   Abstract base class for MADSci manager services using classy-fastapi.

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

    Initialize the manager base.

    Args:
        settings: Manager settings instance
        definition: Manager definition instance
        **kwargs: Additional arguments passed to subclasses

    ### Ancestors (in MRO)

    * madsci.client.client_mixin.MadsciClientMixin
    * typing.Generic
    * classy_fastapi.routable.Routable

    ### Descendants

    * madsci.data_manager.data_server.DataManager
    * madsci.event_manager.event_server.EventManager
    * madsci.experiment_manager.experiment_server.ExperimentManager
    * madsci.location_manager.location_server.LocationManager
    * madsci.resource_manager.resource_server.ResourceManager
    * madsci.squid.lab_server.LabManager
    * madsci.workcell_manager.workcell_server.WorkcellManager

    ### Class variables

    `DEFINITION_CLASS: type[madsci.common.types.base_types.MadsciBaseModel] | None`
    :

    `ENABLE_ROOT_DEFINITION_ENDPOINT: bool`
    :

    `SETTINGS_CLASS: type[madsci.common.types.base_types.MadsciBaseSettings] | None`
    :

    ### Instance variables

    `definition: ~DefinitionT`
    :   Get the manager definition.

    `logger: madsci.client.event_client.EventClient`
    :   Get the logger instance.

    `settings: ~SettingsT`
    :   Get the manager settings.

    ### Methods

    `configure_app(self, app: fastapi.applications.FastAPI) ‑> None`
    :   Configure the FastAPI application.

        This method can be overridden to add additional middleware,
        exception handlers, or other app configuration.

        Args:
            app: The FastAPI application instance

    `create_default_definition(self) ‑> ~DefinitionT`
    :   Create a default definition instance for this manager.

    `create_default_settings(self) ‑> ~SettingsT`
    :   Create default settings instance for this manager.

    `create_server(self, **kwargs: Any) ‑> fastapi.applications.FastAPI`
    :   Create the FastAPI server application.

        Args:
            **kwargs: Additional arguments for app configuration

        Returns:
            FastAPI: The configured FastAPI application

    `get_definition_alt(self) ‑> ~DefinitionT`
    :   Return the manager definition at the /definition endpoint.

        This endpoint is automatically inherited by all manager subclasses.

        Returns:
            DefinitionT: The manager definition

    `get_definition_path(self) ‑> pathlib.Path`
    :   Get the path to the definition file.

    `get_definition_root(self) ‑> ~DefinitionT`
    :   Return the manager definition at the root endpoint.

        This endpoint is automatically inherited by all manager subclasses.

        Returns:
            DefinitionT: The manager definition

    `get_health(self) ‑> madsci.common.types.manager_types.ManagerHealth`
    :   Get the health status of this manager.

        This base implementation returns a healthy status.
        Subclasses should override this method to check specific
        dependencies like databases, external services, etc.

        Returns:
            ManagerHealth: The current health status

    `get_settings_endpoint(self, include_defaults: bool = True, include_schema: bool = False) ‑> dict[str, typing.Any]`
    :   Export current settings for backup/replication.

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

    `get_settings_export(self, include_defaults: bool = True, include_schema: bool = False, include_secrets: bool = False) ‑> dict[str, typing.Any]`
    :   Export current settings for backup/replication.

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

    `health_endpoint(self) ‑> madsci.common.types.manager_types.ManagerHealth`
    :   Health check endpoint for the manager.

        This endpoint is automatically inherited by all manager subclasses.
        Managers that override get_health() will automatically have their
        custom health checks exposed through this endpoint.

        Returns:
            ManagerHealth: The current health status

    `initialize(self, **kwargs: Any) ‑> None`
    :   Initialize manager-specific components.

        This method is called during __init__ and can be overridden
        to perform manager-specific initialization.

        Args:
            **kwargs: Additional arguments from __init__

    `load_definition(self) ‑> ~DefinitionT`
    :   Load definition from file or create default.

        .. deprecated:: 0.7.0
            Definition files are deprecated. Use settings-based configuration
            instead. This method will be removed in v0.8.0.

        As of v0.7.0, this method no longer auto-writes definition files
        to disk. To export a definition, use ``madsci config export``.

    `load_or_create_definition(self) ‑> ~DefinitionT`
    :   Load definition from file or create default.

        .. deprecated:: 0.7.0
            Renamed to :meth:`load_definition`. Definition files are no longer
            auto-written to disk. Use ``madsci config export`` to export
            configuration explicitly.

    `release_identity(self) ‑> None`
    :   Release the registry lock for this manager's identity.

        Should be called during shutdown to allow other instances to
        acquire the same name.

    `run_server(self, host: str | None = None, port: int | None = None, **uvicorn_kwargs: Any) ‑> None`
    :   Run the server using uvicorn.

        Args:
            host: Host to bind to (defaults to settings)
            port: Port to bind to (defaults to settings)
            **uvicorn_kwargs: Additional arguments for uvicorn.run()

    `setup_logging(self) ‑> None`
    :   Setup logging for the manager using MadsciClientMixin.

        This method initializes the EventClient for manager logging.
        The EventClient is created via the mixin's lazy initialization.

    `setup_ownership(self) ‑> None`
    :   Setup ownership context for the manager.

    `span(self, name: str, *, attributes: dict[str, typing.Any] | None = None) ‑> ContextManager[Any]`
    :   Create a best-effort span context manager.

        This is intended for higher-level manager operations (not every log line).

`ManagerBaseMeta(*args, **kwargs)`
:   Metaclass that combines ABCMeta and Routable's metaclass.

    ### Ancestors (in MRO)

    * abc.ABCMeta
    * builtins.type
