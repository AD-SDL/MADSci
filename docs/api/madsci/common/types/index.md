Module madsci.common.types
==========================
Common Types for the MADSci Framework.

Sub-modules
-----------
* madsci.common.types.action_types
* madsci.common.types.admin_command_types
* madsci.common.types.auth_types
* madsci.common.types.backup_types
* madsci.common.types.base_types
* madsci.common.types.client_types
* madsci.common.types.condition_types
* madsci.common.types.context_types
* madsci.common.types.datapoint_types
* madsci.common.types.docker_types
* madsci.common.types.event_types
* madsci.common.types.experiment_types
* madsci.common.types.interface_types
* madsci.common.types.lab_types
* madsci.common.types.location_types
* madsci.common.types.manager_types
* madsci.common.types.migration_types
* madsci.common.types.module_types
* madsci.common.types.mongodb_migration_types
* madsci.common.types.node_types
* madsci.common.types.parameter_types
* madsci.common.types.registry_types
* madsci.common.types.resource_types
* madsci.common.types.step_types
* madsci.common.types.template_types
* madsci.common.types.workcell_types
* madsci.common.types.workflow_types

Classes
-------

`BaseBackupSettings(**kwargs: Any)`
:   Common backup configuration settings.
    
    Initialize settings with walk-up file discovery.
    
    Configuration file paths (YAML, JSON, TOML, .env) are resolved via
    walk-up discovery from a starting directory. Each filename walks up
    independently, so ``node.settings.yaml`` can resolve in the node dir
    while ``settings.yaml`` resolves in the lab root.
    
    The starting directory is determined by (in priority order):
    1. ``_settings_dir`` keyword argument
    2. ``MADSCI_SETTINGS_DIR`` environment variable
    3. Current working directory (default)
    
    Args:
        _settings_dir: Starting directory for walk-up file discovery.
        **kwargs: Forwarded to ``BaseSettings.__init__``.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseSettings
    * pydantic_settings.main.BaseSettings
    * pydantic.main.BaseModel

    ### Descendants

    * madsci.common.types.backup_types.MongoDBBackupSettings
    * madsci.common.types.backup_types.PostgreSQLBackupSettings

    ### Class variables

    `backup_dir: pathlib.Path`
    :

    `compression: bool`
    :

    `max_backups: int`
    :

    `validate_integrity: bool`
    :

    ### Static methods

    `convert_backup_dir_to_path(v: str | pathlib.Path) ‑> pathlib.Path`
    :   Convert backup_dir to Path object.

`HTTPInterfaceSettings(**kwargs: Any)`
:   Settings for HTTP/REST API interfaces.
    
    Provides configuration for equipment that exposes HTTP APIs,
    including authentication and request configuration.
    
    Initialize settings with walk-up file discovery.
    
    Configuration file paths (YAML, JSON, TOML, .env) are resolved via
    walk-up discovery from a starting directory. Each filename walks up
    independently, so ``node.settings.yaml`` can resolve in the node dir
    while ``settings.yaml`` resolves in the lab root.
    
    The starting directory is determined by (in priority order):
    1. ``_settings_dir`` keyword argument
    2. ``MADSCI_SETTINGS_DIR`` environment variable
    3. Current working directory (default)
    
    Args:
        _settings_dir: Starting directory for walk-up file discovery.
        **kwargs: Forwarded to ``BaseSettings.__init__``.

    ### Ancestors (in MRO)

    * madsci.common.types.interface_types.InterfaceSettings
    * madsci.common.types.base_types.MadsciBaseSettings
    * pydantic_settings.main.BaseSettings
    * pydantic.main.BaseModel

    ### Class variables

    `auth_header_name: str`
    :

    `auth_password: str | None`
    :

    `auth_token: str | None`
    :

    `auth_type: Literal['none', 'basic', 'bearer', 'api_key'] | None`
    :

    `auth_username: str | None`
    :

    `base_url: str`
    :

    `default_headers: dict[str, str]`
    :

    `request_timeout: float`
    :

    `verify_ssl: bool`
    :

`InterfaceSettings(**kwargs: Any)`
:   Base settings for hardware interfaces.
    
    These settings are used by interface classes, independent of whether
    they're used in a MADSci node or standalone (e.g., in a Jupyter notebook).
    
    Interface developers should inherit from this class (or one of its
    specialized subclasses like SerialInterfaceSettings) and add
    device-specific configuration fields.
    
    Initialize settings with walk-up file discovery.
    
    Configuration file paths (YAML, JSON, TOML, .env) are resolved via
    walk-up discovery from a starting directory. Each filename walks up
    independently, so ``node.settings.yaml`` can resolve in the node dir
    while ``settings.yaml`` resolves in the lab root.
    
    The starting directory is determined by (in priority order):
    1. ``_settings_dir`` keyword argument
    2. ``MADSCI_SETTINGS_DIR`` environment variable
    3. Current working directory (default)
    
    Args:
        _settings_dir: Starting directory for walk-up file discovery.
        **kwargs: Forwarded to ``BaseSettings.__init__``.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseSettings
    * pydantic_settings.main.BaseSettings
    * pydantic.main.BaseModel

    ### Descendants

    * madsci.common.types.interface_types.HTTPInterfaceSettings
    * madsci.common.types.interface_types.SerialInterfaceSettings
    * madsci.common.types.interface_types.SocketInterfaceSettings
    * madsci.common.types.interface_types.USBInterfaceSettings

    ### Class variables

    `auto_reconnect: bool`
    :

    `command_timeout: float`
    :

    `connection_timeout: float`
    :

    `max_reconnect_attempts: int`
    :

    `reconnect_delay: float`
    :

    `retry_count: int`
    :

    `retry_delay: float`
    :

`ModuleSettings(**kwargs: Any)`
:   Base settings for MADSci node modules.
    
    Contains module-level metadata that applies to the entire module,
    not just a single node instance. This includes version information,
    repository URLs, and interface variant selection.
    
    Module developers should inherit from this class and customize
    the module_name and other fields as needed.
    
    Initialize settings with walk-up file discovery.
    
    Configuration file paths (YAML, JSON, TOML, .env) are resolved via
    walk-up discovery from a starting directory. Each filename walks up
    independently, so ``node.settings.yaml`` can resolve in the node dir
    while ``settings.yaml`` resolves in the lab root.
    
    The starting directory is determined by (in priority order):
    1. ``_settings_dir`` keyword argument
    2. ``MADSCI_SETTINGS_DIR`` environment variable
    3. Current working directory (default)
    
    Args:
        _settings_dir: Starting directory for walk-up file discovery.
        **kwargs: Forwarded to ``BaseSettings.__init__``.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseSettings
    * pydantic_settings.main.BaseSettings
    * pydantic.main.BaseModel

    ### Descendants

    * madsci.common.types.module_types.NodeModuleSettings

    ### Class variables

    `documentation_url: str | None`
    :

    `interface_variant: Literal['real', 'fake', 'sim']`
    :

    `module_name: str`
    :

    `module_version: str`
    :

    `repository_url: str | None`
    :

`MongoDBBackupSettings(**kwargs: Any)`
:   MongoDB-specific backup settings.
    
    Initialize settings with walk-up file discovery.
    
    Configuration file paths (YAML, JSON, TOML, .env) are resolved via
    walk-up discovery from a starting directory. Each filename walks up
    independently, so ``node.settings.yaml`` can resolve in the node dir
    while ``settings.yaml`` resolves in the lab root.
    
    The starting directory is determined by (in priority order):
    1. ``_settings_dir`` keyword argument
    2. ``MADSCI_SETTINGS_DIR`` environment variable
    3. Current working directory (default)
    
    Args:
        _settings_dir: Starting directory for walk-up file discovery.
        **kwargs: Forwarded to ``BaseSettings.__init__``.

    ### Ancestors (in MRO)

    * madsci.common.types.backup_types.BaseBackupSettings
    * madsci.common.types.base_types.MadsciBaseSettings
    * pydantic_settings.main.BaseSettings
    * pydantic.main.BaseModel

    ### Class variables

    `collections: List[str] | None`
    :

    `database: str | None`
    :

    `mongo_db_url: pydantic.networks.AnyUrl`
    :

`NodeModuleSettings(**kwargs: Any)`
:   Settings for a node instance within a module.
    
    Combines module-level settings with node-specific runtime configuration.
    This class bridges the gap between ModuleSettings and NodeConfig,
    providing a unified configuration surface for node modules.
    
    Node developers typically don't use this directly; instead, they
    create a custom settings class that inherits from RestNodeConfig
    or NodeConfig and adds module-specific fields.
    
    Initialize settings with walk-up file discovery.
    
    Configuration file paths (YAML, JSON, TOML, .env) are resolved via
    walk-up discovery from a starting directory. Each filename walks up
    independently, so ``node.settings.yaml`` can resolve in the node dir
    while ``settings.yaml`` resolves in the lab root.
    
    The starting directory is determined by (in priority order):
    1. ``_settings_dir`` keyword argument
    2. ``MADSCI_SETTINGS_DIR`` environment variable
    3. Current working directory (default)
    
    Args:
        _settings_dir: Starting directory for walk-up file discovery.
        **kwargs: Forwarded to ``BaseSettings.__init__``.

    ### Ancestors (in MRO)

    * madsci.common.types.module_types.ModuleSettings
    * madsci.common.types.base_types.MadsciBaseSettings
    * pydantic_settings.main.BaseSettings
    * pydantic.main.BaseModel

    ### Class variables

    `description: str | None`
    :

    `lab_url: str | None`
    :

    `name: str`
    :

    `simulate: bool`
    :

    `workcell_url: str | None`
    :

`PostgreSQLBackupSettings(**kwargs: Any)`
:   PostgreSQL-specific backup settings.
    
    Initialize settings with walk-up file discovery.
    
    Configuration file paths (YAML, JSON, TOML, .env) are resolved via
    walk-up discovery from a starting directory. Each filename walks up
    independently, so ``node.settings.yaml`` can resolve in the node dir
    while ``settings.yaml`` resolves in the lab root.
    
    The starting directory is determined by (in priority order):
    1. ``_settings_dir`` keyword argument
    2. ``MADSCI_SETTINGS_DIR`` environment variable
    3. Current working directory (default)
    
    Args:
        _settings_dir: Starting directory for walk-up file discovery.
        **kwargs: Forwarded to ``BaseSettings.__init__``.

    ### Ancestors (in MRO)

    * madsci.common.types.backup_types.BaseBackupSettings
    * madsci.common.types.base_types.MadsciBaseSettings
    * pydantic_settings.main.BaseSettings
    * pydantic.main.BaseModel

    ### Class variables

    `backup_format: str`
    :

    `db_url: str`
    :

`SerialInterfaceSettings(**kwargs: Any)`
:   Settings for serial port (RS-232, RS-485, USB-serial) interfaces.
    
    Provides configuration for pyserial-based communication with
    laboratory equipment that uses serial protocols.
    
    Initialize settings with walk-up file discovery.
    
    Configuration file paths (YAML, JSON, TOML, .env) are resolved via
    walk-up discovery from a starting directory. Each filename walks up
    independently, so ``node.settings.yaml`` can resolve in the node dir
    while ``settings.yaml`` resolves in the lab root.
    
    The starting directory is determined by (in priority order):
    1. ``_settings_dir`` keyword argument
    2. ``MADSCI_SETTINGS_DIR`` environment variable
    3. Current working directory (default)
    
    Args:
        _settings_dir: Starting directory for walk-up file discovery.
        **kwargs: Forwarded to ``BaseSettings.__init__``.

    ### Ancestors (in MRO)

    * madsci.common.types.interface_types.InterfaceSettings
    * madsci.common.types.base_types.MadsciBaseSettings
    * pydantic_settings.main.BaseSettings
    * pydantic.main.BaseModel

    ### Class variables

    `baudrate: int`
    :

    `bytesize: Literal[5, 6, 7, 8]`
    :

    `dsrdtr: bool`
    :

    `parity: Literal['N', 'E', 'O', 'M', 'S']`
    :

    `port: str`
    :

    `read_timeout: float | None`
    :

    `rtscts: bool`
    :

    `stopbits: Literal[1, 1.5, 2]`
    :

    `write_timeout: float | None`
    :

    `xonxoff: bool`
    :

`SocketInterfaceSettings(**kwargs: Any)`
:   Settings for TCP/IP socket interfaces.
    
    Provides configuration for network-based communication with
    laboratory equipment that uses TCP/IP protocols.
    
    Initialize settings with walk-up file discovery.
    
    Configuration file paths (YAML, JSON, TOML, .env) are resolved via
    walk-up discovery from a starting directory. Each filename walks up
    independently, so ``node.settings.yaml`` can resolve in the node dir
    while ``settings.yaml`` resolves in the lab root.
    
    The starting directory is determined by (in priority order):
    1. ``_settings_dir`` keyword argument
    2. ``MADSCI_SETTINGS_DIR`` environment variable
    3. Current working directory (default)
    
    Args:
        _settings_dir: Starting directory for walk-up file discovery.
        **kwargs: Forwarded to ``BaseSettings.__init__``.

    ### Ancestors (in MRO)

    * madsci.common.types.interface_types.InterfaceSettings
    * madsci.common.types.base_types.MadsciBaseSettings
    * pydantic_settings.main.BaseSettings
    * pydantic.main.BaseModel

    ### Class variables

    `buffer_size: int`
    :

    `host: str`
    :

    `keepalive: bool`
    :

    `keepalive_interval: int`
    :

    `port: int`
    :

    `ssl_cert_file: str | None`
    :

    `ssl_key_file: str | None`
    :

    `ssl_verify: bool`
    :

    `use_ssl: bool`
    :

`USBInterfaceSettings(**kwargs: Any)`
:   Settings for direct USB device interfaces.
    
    Provides configuration for USB-based communication using
    libraries like pyusb. This is for devices that don't use
    USB-serial bridges but communicate directly via USB.
    
    Initialize settings with walk-up file discovery.
    
    Configuration file paths (YAML, JSON, TOML, .env) are resolved via
    walk-up discovery from a starting directory. Each filename walks up
    independently, so ``node.settings.yaml`` can resolve in the node dir
    while ``settings.yaml`` resolves in the lab root.
    
    The starting directory is determined by (in priority order):
    1. ``_settings_dir`` keyword argument
    2. ``MADSCI_SETTINGS_DIR`` environment variable
    3. Current working directory (default)
    
    Args:
        _settings_dir: Starting directory for walk-up file discovery.
        **kwargs: Forwarded to ``BaseSettings.__init__``.

    ### Ancestors (in MRO)

    * madsci.common.types.interface_types.InterfaceSettings
    * madsci.common.types.base_types.MadsciBaseSettings
    * pydantic_settings.main.BaseSettings
    * pydantic.main.BaseModel

    ### Class variables

    `detach_kernel_driver: bool`
    :

    `endpoint_in: int | None`
    :

    `endpoint_out: int | None`
    :

    `interface_number: int`
    :

    `product_id: int | None`
    :

    `serial_number: str | None`
    :

    `vendor_id: int | None`
    :