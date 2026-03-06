"""Tests for InterfaceSettings and related types."""

import pytest
from madsci.common.types.interface_types import (
    HTTPInterfaceSettings,
    InterfaceSettings,
    SerialInterfaceSettings,
    SocketInterfaceSettings,
    USBInterfaceSettings,
)


class TestInterfaceSettings:
    """Tests for the base InterfaceSettings class."""

    def test_default_values(self) -> None:
        """Test that InterfaceSettings has correct default values."""
        settings = InterfaceSettings()

        assert settings.connection_timeout == 10.0
        assert settings.command_timeout == 30.0
        assert settings.retry_count == 3
        assert settings.retry_delay == 1.0
        assert settings.auto_reconnect is True
        assert settings.reconnect_delay == 5.0
        assert settings.max_reconnect_attempts == 5

    def test_from_env_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test loading settings from environment variables."""
        monkeypatch.setenv("INTERFACE_CONNECTION_TIMEOUT", "20.0")
        monkeypatch.setenv("INTERFACE_COMMAND_TIMEOUT", "60.0")
        monkeypatch.setenv("INTERFACE_RETRY_COUNT", "5")
        monkeypatch.setenv("INTERFACE_AUTO_RECONNECT", "false")

        settings = InterfaceSettings()

        assert settings.connection_timeout == 20.0
        assert settings.command_timeout == 60.0
        assert settings.retry_count == 5
        assert settings.auto_reconnect is False

    def test_validation_constraints(self) -> None:
        """Test that validation constraints are enforced."""
        # Negative timeout should fail
        with pytest.raises(ValueError):
            InterfaceSettings(connection_timeout=-1.0)

        # Negative retry count should fail
        with pytest.raises(ValueError):
            InterfaceSettings(retry_count=-1)


class TestSerialInterfaceSettings:
    """Tests for the SerialInterfaceSettings class."""

    def test_default_values(self) -> None:
        """Test that SerialInterfaceSettings has correct default values."""
        settings = SerialInterfaceSettings()

        assert settings.port == "/dev/ttyUSB0"
        assert settings.baudrate == 9600
        assert settings.bytesize == 8
        assert settings.parity == "N"
        assert settings.stopbits == 1
        assert settings.xonxoff is False
        assert settings.rtscts is False
        assert settings.dsrdtr is False
        assert settings.read_timeout == 1.0
        assert settings.write_timeout == 1.0

    def test_inherits_base_settings(self) -> None:
        """Test that SerialInterfaceSettings inherits from InterfaceSettings."""
        settings = SerialInterfaceSettings()

        # Should have base class fields
        assert settings.connection_timeout == 10.0
        assert settings.retry_count == 3

    def test_from_env_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test loading settings from environment variables."""
        monkeypatch.setenv("SERIAL_INTERFACE_PORT", "/dev/ttyUSB1")
        monkeypatch.setenv("SERIAL_INTERFACE_BAUDRATE", "115200")
        monkeypatch.setenv("SERIAL_INTERFACE_PARITY", "E")

        settings = SerialInterfaceSettings()

        assert settings.port == "/dev/ttyUSB1"
        assert settings.baudrate == 115200
        assert settings.parity == "E"

    def test_parity_options(self) -> None:
        """Test that parity accepts valid options."""
        for parity in ["N", "E", "O", "M", "S"]:
            settings = SerialInterfaceSettings(parity=parity)
            assert settings.parity == parity

    def test_stopbits_options(self) -> None:
        """Test that stopbits accepts valid options."""
        for stopbits in [1, 1.5, 2]:
            settings = SerialInterfaceSettings(stopbits=stopbits)
            assert settings.stopbits == stopbits


class TestSocketInterfaceSettings:
    """Tests for the SocketInterfaceSettings class."""

    def test_default_values(self) -> None:
        """Test that SocketInterfaceSettings has correct default values."""
        settings = SocketInterfaceSettings(port=8080)

        assert settings.host == "localhost"
        assert settings.port == 8080
        assert settings.use_ssl is False
        assert settings.ssl_verify is True
        assert settings.buffer_size == 4096
        assert settings.keepalive is True
        assert settings.keepalive_interval == 60

    def test_port_is_required(self) -> None:
        """Test that port is a required field."""
        with pytest.raises(ValueError):
            SocketInterfaceSettings()  # port is required

    def test_port_validation(self) -> None:
        """Test port number validation."""
        # Valid ports
        settings = SocketInterfaceSettings(port=1)
        assert settings.port == 1

        settings = SocketInterfaceSettings(port=65535)
        assert settings.port == 65535

        # Invalid ports
        with pytest.raises(ValueError):
            SocketInterfaceSettings(port=0)

        with pytest.raises(ValueError):
            SocketInterfaceSettings(port=65536)

    def test_from_env_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test loading settings from environment variables."""
        monkeypatch.setenv("SOCKET_INTERFACE_HOST", "192.168.1.100")
        monkeypatch.setenv("SOCKET_INTERFACE_PORT", "9090")
        monkeypatch.setenv("SOCKET_INTERFACE_USE_SSL", "true")

        settings = SocketInterfaceSettings()

        assert settings.host == "192.168.1.100"
        assert settings.port == 9090
        assert settings.use_ssl is True


class TestUSBInterfaceSettings:
    """Tests for the USBInterfaceSettings class."""

    def test_default_values(self) -> None:
        """Test that USBInterfaceSettings has correct default values."""
        settings = USBInterfaceSettings()

        assert settings.vendor_id is None
        assert settings.product_id is None
        assert settings.serial_number is None
        assert settings.interface_number == 0
        assert settings.endpoint_in is None
        assert settings.endpoint_out is None
        assert settings.detach_kernel_driver is True

    def test_device_identification(self) -> None:
        """Test setting device identification fields."""
        settings = USBInterfaceSettings(
            vendor_id=0x1234,
            product_id=0x5678,
            serial_number="ABC123",
        )

        assert settings.vendor_id == 0x1234
        assert settings.product_id == 0x5678
        assert settings.serial_number == "ABC123"

    def test_from_env_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test loading settings from environment variables."""
        monkeypatch.setenv("USB_INTERFACE_VENDOR_ID", "4660")  # 0x1234
        monkeypatch.setenv("USB_INTERFACE_PRODUCT_ID", "22136")  # 0x5678
        monkeypatch.setenv("USB_INTERFACE_INTERFACE_NUMBER", "1")

        settings = USBInterfaceSettings()

        assert settings.vendor_id == 4660
        assert settings.product_id == 22136
        assert settings.interface_number == 1


class TestHTTPInterfaceSettings:
    """Tests for the HTTPInterfaceSettings class."""

    def test_default_values(self) -> None:
        """Test that HTTPInterfaceSettings has correct default values."""
        settings = HTTPInterfaceSettings(base_url="http://device.local/api")

        assert settings.base_url == "http://device.local/api"
        assert settings.auth_type is None
        assert settings.verify_ssl is True
        assert settings.request_timeout == 30.0
        assert settings.default_headers == {}

    def test_base_url_is_required(self) -> None:
        """Test that base_url is a required field."""
        with pytest.raises(ValueError):
            HTTPInterfaceSettings()  # base_url is required

    def test_auth_types(self) -> None:
        """Test different authentication types."""
        # No auth
        settings = HTTPInterfaceSettings(
            base_url="http://device.local/api",
            auth_type=None,
        )
        assert settings.auth_type is None

        # Basic auth
        settings = HTTPInterfaceSettings(
            base_url="http://device.local/api",
            auth_type="basic",
            auth_username="user",
            auth_password="pass",  # noqa: S106
        )
        assert settings.auth_type == "basic"
        assert settings.auth_username == "user"
        assert settings.auth_password == "pass"  # noqa: S105

        # Bearer token
        settings = HTTPInterfaceSettings(
            base_url="http://device.local/api",
            auth_type="bearer",
            auth_token="my-token",  # noqa: S106
        )
        assert settings.auth_type == "bearer"
        assert settings.auth_token == "my-token"  # noqa: S105

        # API key
        settings = HTTPInterfaceSettings(
            base_url="http://device.local/api",
            auth_type="api_key",
            auth_password="my-api-key",  # noqa: S106
            auth_header_name="X-API-Key",
        )
        assert settings.auth_type == "api_key"
        assert settings.auth_header_name == "X-API-Key"

    def test_from_env_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test loading settings from environment variables."""
        monkeypatch.setenv("HTTP_INTERFACE_BASE_URL", "https://api.example.com")
        monkeypatch.setenv("HTTP_INTERFACE_AUTH_TYPE", "bearer")
        monkeypatch.setenv("HTTP_INTERFACE_AUTH_TOKEN", "secret-token")
        monkeypatch.setenv("HTTP_INTERFACE_VERIFY_SSL", "false")

        settings = HTTPInterfaceSettings()

        assert settings.base_url == "https://api.example.com"
        assert settings.auth_type == "bearer"
        assert settings.auth_token == "secret-token"  # noqa: S105
        assert settings.verify_ssl is False


class TestCustomInterfaceSettings:
    """Tests for creating custom interface settings classes."""

    def test_custom_serial_interface(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test creating a custom serial interface settings class."""
        from pydantic import Field  # noqa: PLC0415

        class FooInterfaceSettings(
            SerialInterfaceSettings, env_prefix="FOO_INTERFACE_"
        ):
            """Custom settings for Foo interface."""

            port: str = "/dev/ttyUSB0"
            baudrate: int = 115200
            custom_protocol_version: int = Field(default=2)

        monkeypatch.setenv("FOO_INTERFACE_PORT", "/dev/ttyACM0")
        monkeypatch.setenv("FOO_INTERFACE_CUSTOM_PROTOCOL_VERSION", "3")

        settings = FooInterfaceSettings()

        assert settings.port == "/dev/ttyACM0"
        assert settings.baudrate == 115200  # Default from class
        assert settings.custom_protocol_version == 3
        # Inherits base interface settings
        assert settings.retry_count == 3
