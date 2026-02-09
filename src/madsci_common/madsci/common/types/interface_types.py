"""Types for MADSci Hardware Interfaces and their configuration.

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
"""

from typing import Literal, Optional

from madsci.common.types.base_types import MadsciBaseSettings
from pydantic import Field


class InterfaceSettings(
    MadsciBaseSettings,
    env_file=(".env", "interface.env"),
    toml_file=("settings.toml", "interface.settings.toml"),
    yaml_file=("settings.yaml", "interface.settings.yaml"),
    json_file=("settings.json", "interface.settings.json"),
    env_prefix="INTERFACE_",
):
    """Base settings for hardware interfaces.

    These settings are used by interface classes, independent of whether
    they're used in a MADSci node or standalone (e.g., in a Jupyter notebook).

    Interface developers should inherit from this class (or one of its
    specialized subclasses like SerialInterfaceSettings) and add
    device-specific configuration fields.
    """

    connection_timeout: float = Field(
        default=10.0,
        title="Connection Timeout",
        description="Timeout for initial connection in seconds.",
        ge=0.0,
    )
    command_timeout: float = Field(
        default=30.0,
        title="Command Timeout",
        description="Timeout for individual commands in seconds.",
        ge=0.0,
    )
    retry_count: int = Field(
        default=3,
        title="Retry Count",
        description="Number of retries on transient failures.",
        ge=0,
    )
    retry_delay: float = Field(
        default=1.0,
        title="Retry Delay",
        description="Delay between retries in seconds.",
        ge=0.0,
    )
    auto_reconnect: bool = Field(
        default=True,
        title="Auto Reconnect",
        description="Whether to automatically attempt reconnection on disconnect.",
    )
    reconnect_delay: float = Field(
        default=5.0,
        title="Reconnect Delay",
        description="Delay before attempting reconnection in seconds.",
        ge=0.0,
    )
    max_reconnect_attempts: int = Field(
        default=5,
        title="Max Reconnect Attempts",
        description="Maximum number of reconnection attempts. Set to 0 for unlimited.",
        ge=0,
    )


class SerialInterfaceSettings(
    InterfaceSettings,
    env_prefix="SERIAL_INTERFACE_",
):
    """Settings for serial port (RS-232, RS-485, USB-serial) interfaces.

    Provides configuration for pyserial-based communication with
    laboratory equipment that uses serial protocols.
    """

    port: str = Field(
        default="/dev/ttyUSB0",
        title="Serial Port",
        description="Serial port device path (e.g., '/dev/ttyUSB0' on Linux, "
        "'COM3' on Windows).",
    )
    baudrate: int = Field(
        default=9600,
        title="Baud Rate",
        description="Communication baud rate.",
    )
    bytesize: Literal[5, 6, 7, 8] = Field(
        default=8,
        title="Byte Size",
        description="Number of data bits.",
    )
    parity: Literal["N", "E", "O", "M", "S"] = Field(
        default="N",
        title="Parity",
        description="Parity checking: N=None, E=Even, O=Odd, M=Mark, S=Space.",
    )
    stopbits: Literal[1, 1.5, 2] = Field(
        default=1,
        title="Stop Bits",
        description="Number of stop bits.",
    )
    xonxoff: bool = Field(
        default=False,
        title="XON/XOFF",
        description="Enable software flow control.",
    )
    rtscts: bool = Field(
        default=False,
        title="RTS/CTS",
        description="Enable hardware (RTS/CTS) flow control.",
    )
    dsrdtr: bool = Field(
        default=False,
        title="DSR/DTR",
        description="Enable hardware (DSR/DTR) flow control.",
    )
    read_timeout: Optional[float] = Field(
        default=1.0,
        title="Read Timeout",
        description="Timeout for read operations in seconds. None for blocking.",
        ge=0.0,
    )
    write_timeout: Optional[float] = Field(
        default=1.0,
        title="Write Timeout",
        description="Timeout for write operations in seconds. None for blocking.",
        ge=0.0,
    )


class SocketInterfaceSettings(
    InterfaceSettings,
    env_prefix="SOCKET_INTERFACE_",
):
    """Settings for TCP/IP socket interfaces.

    Provides configuration for network-based communication with
    laboratory equipment that uses TCP/IP protocols.
    """

    host: str = Field(
        default="localhost",
        title="Host",
        description="Hostname or IP address to connect to.",
    )
    port: int = Field(
        title="Port",
        description="TCP port number to connect to.",
        ge=1,
        le=65535,
    )
    use_ssl: bool = Field(
        default=False,
        title="Use SSL/TLS",
        description="Enable SSL/TLS encryption for the connection.",
    )
    ssl_verify: bool = Field(
        default=True,
        title="SSL Verify",
        description="Verify SSL certificates. Set to False for self-signed certs.",
    )
    ssl_cert_file: Optional[str] = Field(
        default=None,
        title="SSL Certificate File",
        description="Path to SSL certificate file for client authentication.",
    )
    ssl_key_file: Optional[str] = Field(
        default=None,
        title="SSL Key File",
        description="Path to SSL key file for client authentication.",
    )
    buffer_size: int = Field(
        default=4096,
        title="Buffer Size",
        description="Size of the receive buffer in bytes.",
        ge=1,
    )
    keepalive: bool = Field(
        default=True,
        title="Keep Alive",
        description="Enable TCP keepalive to detect dead connections.",
    )
    keepalive_interval: int = Field(
        default=60,
        title="Keep Alive Interval",
        description="Interval between keepalive probes in seconds.",
        ge=1,
    )


class USBInterfaceSettings(
    InterfaceSettings,
    env_prefix="USB_INTERFACE_",
):
    """Settings for direct USB device interfaces.

    Provides configuration for USB-based communication using
    libraries like pyusb. This is for devices that don't use
    USB-serial bridges but communicate directly via USB.
    """

    vendor_id: Optional[int] = Field(
        default=None,
        title="Vendor ID",
        description="USB Vendor ID (VID) in decimal. Use with product_id to "
        "identify a specific device.",
    )
    product_id: Optional[int] = Field(
        default=None,
        title="Product ID",
        description="USB Product ID (PID) in decimal. Use with vendor_id to "
        "identify a specific device.",
    )
    serial_number: Optional[str] = Field(
        default=None,
        title="Serial Number",
        description="USB device serial number for identifying a specific device "
        "when multiple devices with the same VID/PID are connected.",
    )
    interface_number: int = Field(
        default=0,
        title="Interface Number",
        description="USB interface number to use on the device.",
        ge=0,
    )
    endpoint_in: Optional[int] = Field(
        default=None,
        title="Endpoint In",
        description="USB IN endpoint address. If None, auto-detected.",
    )
    endpoint_out: Optional[int] = Field(
        default=None,
        title="Endpoint Out",
        description="USB OUT endpoint address. If None, auto-detected.",
    )
    detach_kernel_driver: bool = Field(
        default=True,
        title="Detach Kernel Driver",
        description="Detach kernel driver if attached (Linux only).",
    )


class HTTPInterfaceSettings(
    InterfaceSettings,
    env_prefix="HTTP_INTERFACE_",
):
    """Settings for HTTP/REST API interfaces.

    Provides configuration for equipment that exposes HTTP APIs,
    including authentication and request configuration.
    """

    base_url: str = Field(
        title="Base URL",
        description="Base URL for the API (e.g., 'http://device.local:8080/api/v1').",
    )
    auth_type: Optional[Literal["none", "basic", "bearer", "api_key"]] = Field(
        default=None,
        title="Authentication Type",
        description="Type of authentication to use.",
    )
    auth_username: Optional[str] = Field(
        default=None,
        title="Username",
        description="Username for basic authentication.",
    )
    auth_password: Optional[str] = Field(
        default=None,
        title="Password",
        description="Password for basic or API key authentication.",
    )
    auth_token: Optional[str] = Field(
        default=None,
        title="Bearer Token",
        description="Bearer token for token-based authentication.",
    )
    auth_header_name: str = Field(
        default="Authorization",
        title="Auth Header Name",
        description="Header name for API key authentication.",
    )
    verify_ssl: bool = Field(
        default=True,
        title="Verify SSL",
        description="Verify SSL certificates.",
    )
    default_headers: dict[str, str] = Field(
        default_factory=dict,
        title="Default Headers",
        description="Default headers to include in all requests.",
    )
    request_timeout: float = Field(
        default=30.0,
        title="Request Timeout",
        description="Default timeout for HTTP requests in seconds.",
        ge=0.0,
    )
