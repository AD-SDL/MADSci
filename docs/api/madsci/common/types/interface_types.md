Module madsci.common.types.interface_types
==========================================
Types for MADSci Hardware Interfaces and their configuration.

This module provides base settings classes for hardware interfaces. Interfaces
are the low-level drivers that communicate directly with laboratory equipment.
They are designed to be usable both within MADSci nodes and standalone (e.g.,
in Jupyter notebooks for testing).

The settings hierarchy is:
    InterfaceSettings (base interface settings)
        ├── SerialInterfaceSettings (serial port interfaces)
        ├── SocketInterfaceSettings (TCP/IP socket interfaces)
        └── USBInterfaceSettings (USB device interfaces)

Usage:
    ```python
    # In your module's foo_types.py
    from madsci.common.types.interface_types import SerialInterfaceSettings

    class FooInterfaceSettings(SerialInterfaceSettings):
        model_config = SettingsConfigDict(env_prefix="FOO_INTERFACE_")
        port: str = "/dev/ttyUSB0"
        baudrate: int = 115200

    # In your interface implementation
    class FooInterface:
        def __init__(self, settings: FooInterfaceSettings = None):
            self.settings = settings or FooInterfaceSettings()
    ```

Classes
-------

`HTTPInterfaceSettings(**kwargs: Any)`
:   Settings for HTTP/REST API interfaces.

    Provides configuration for equipment that exposes HTTP APIs,
    including authentication and request configuration.

    Initialize settings, optionally with a settings directory.

    When ``_settings_dir`` is provided (or ``MADSCI_SETTINGS_DIR`` is set),
    configuration file paths are resolved via walk-up discovery from that
    directory instead of the current working directory. Each filename walks
    up independently, so ``node.settings.yaml`` can resolve in the node dir
    while ``settings.yaml`` resolves in the lab root.

    Without either, existing CWD-relative behavior is preserved exactly.

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

    Initialize settings, optionally with a settings directory.

    When ``_settings_dir`` is provided (or ``MADSCI_SETTINGS_DIR`` is set),
    configuration file paths are resolved via walk-up discovery from that
    directory instead of the current working directory. Each filename walks
    up independently, so ``node.settings.yaml`` can resolve in the node dir
    while ``settings.yaml`` resolves in the lab root.

    Without either, existing CWD-relative behavior is preserved exactly.

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

`SerialInterfaceSettings(**kwargs: Any)`
:   Settings for serial port (RS-232, RS-485, USB-serial) interfaces.

    Provides configuration for pyserial-based communication with
    laboratory equipment that uses serial protocols.

    Initialize settings, optionally with a settings directory.

    When ``_settings_dir`` is provided (or ``MADSCI_SETTINGS_DIR`` is set),
    configuration file paths are resolved via walk-up discovery from that
    directory instead of the current working directory. Each filename walks
    up independently, so ``node.settings.yaml`` can resolve in the node dir
    while ``settings.yaml`` resolves in the lab root.

    Without either, existing CWD-relative behavior is preserved exactly.

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

    Initialize settings, optionally with a settings directory.

    When ``_settings_dir`` is provided (or ``MADSCI_SETTINGS_DIR`` is set),
    configuration file paths are resolved via walk-up discovery from that
    directory instead of the current working directory. Each filename walks
    up independently, so ``node.settings.yaml`` can resolve in the node dir
    while ``settings.yaml`` resolves in the lab root.

    Without either, existing CWD-relative behavior is preserved exactly.

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

    Initialize settings, optionally with a settings directory.

    When ``_settings_dir`` is provided (or ``MADSCI_SETTINGS_DIR`` is set),
    configuration file paths are resolved via walk-up discovery from that
    directory instead of the current working directory. Each filename walks
    up independently, so ``node.settings.yaml`` can resolve in the node dir
    while ``settings.yaml`` resolves in the lab root.

    Without either, existing CWD-relative behavior is preserved exactly.

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
