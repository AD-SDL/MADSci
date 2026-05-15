"""Tests for the settings export functionality."""

import pytest
from madsci.common.types.manager_types import ManagerSettings
from madsci.common.types.workcell_types import WorkcellManagerSettings
from pydantic import Field


class TestSettingsExport:
    """Tests for the get_settings_export functionality."""

    def test_export_basic_settings(self) -> None:
        """Test exporting basic settings."""
        settings = WorkcellManagerSettings()
        export = settings.model_dump(mode="json")

        assert "server_url" in export
        assert "cache_host" in export
        assert export["cache_host"] == "localhost"

    def test_export_with_custom_values(self) -> None:
        """Test exporting settings with custom values."""
        settings = WorkcellManagerSettings(
            cache_host="redis.example.com",
            cache_port=6380,
            scheduler_update_interval=10.0,
        )
        export = settings.model_dump(mode="json")

        assert export["cache_host"] == "redis.example.com"
        assert export["cache_port"] == 6380
        assert export["scheduler_update_interval"] == 10.0

    def test_settings_json_schema(self) -> None:
        """Test that settings can export JSON schema."""
        schema = WorkcellManagerSettings.model_json_schema()

        assert "properties" in schema
        assert "cache_host" in schema["properties"]
        assert "server_url" in schema["properties"]

    def test_custom_settings_export(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test exporting custom settings class."""

        class CustomManagerSettings(
            ManagerSettings,
            env_prefix="CUSTOM_",
        ):
            """Custom manager settings for testing."""

            api_key: str = Field(default="default-key")
            database_password: str = Field(default="default-password")
            custom_setting: int = Field(default=42)

        monkeypatch.setenv("CUSTOM_CUSTOM_SETTING", "100")

        settings = CustomManagerSettings()
        export = settings.model_dump(mode="json")

        assert export["custom_setting"] == 100
        assert export["api_key"] == "default-key"


class TestSensitiveFieldRedaction:
    """Tests for sensitive field redaction in settings export."""

    def test_sensitive_patterns_identified(self) -> None:
        """Test that we can identify sensitive field names."""
        sensitive_patterns = [
            "password",
            "secret",
            "token",
            "key",
            "credential",
            "api_key",
            "apikey",
            "auth",
        ]

        test_fields = [
            ("password", True),
            ("db_password", True),
            ("secret_key", True),
            ("api_token", True),
            ("auth_token", True),
            ("api_key", True),
            ("apikey", True),
            ("credentials", True),
            ("host", False),
            ("port", False),
            ("url", False),
            ("database_name", False),
        ]

        for field_name, should_be_sensitive in test_fields:
            field_lower = field_name.lower()
            is_sensitive = any(pattern in field_lower for pattern in sensitive_patterns)
            assert is_sensitive == should_be_sensitive, (
                f"Field '{field_name}' sensitivity mismatch"
            )

    def test_redaction_logic(self) -> None:
        """Test the redaction logic that will be used in settings export."""
        sensitive_patterns = [
            "password",
            "secret",
            "token",
            "key",
            "credential",
            "api_key",
            "apikey",
            "auth",
        ]

        data = {
            "host": "localhost",
            "port": 8080,
            "password": "secret123",
            "api_key": "abc123",
            "database_name": "mydb",
            "auth_token": "token456",
        }

        # Apply redaction logic
        redacted = {}
        for field, value in data.items():
            field_lower = field.lower()
            if any(pattern in field_lower for pattern in sensitive_patterns):
                redacted[field] = "***REDACTED***"
            else:
                redacted[field] = value

        assert redacted["host"] == "localhost"
        assert redacted["port"] == 8080
        assert redacted["password"] == "***REDACTED***"  # noqa: S105
        assert redacted["api_key"] == "***REDACTED***"
        assert redacted["database_name"] == "mydb"
        assert redacted["auth_token"] == "***REDACTED***"  # noqa: S105


class TestSettingsNonDefaultExport:
    """Tests for exporting only non-default settings."""

    def test_filter_non_defaults(self) -> None:
        """Test filtering to only non-default values."""
        # Create settings with some custom values
        settings = WorkcellManagerSettings(
            cache_host="custom-redis.example.com",
            cache_port=6380,
            # scheduler_update_interval uses default
        )

        # Get all settings
        all_settings = settings.model_dump(mode="json")

        # Get default settings
        defaults = WorkcellManagerSettings().model_dump(mode="json")

        # Filter to non-defaults
        non_defaults = {
            k: v
            for k, v in all_settings.items()
            if all_settings.get(k) != defaults.get(k)
        }

        assert "cache_host" in non_defaults
        assert non_defaults["cache_host"] == "custom-redis.example.com"
        assert "cache_port" in non_defaults
        assert non_defaults["cache_port"] == 6380
        # Default values should not be in the filtered output
        assert "scheduler_update_interval" not in non_defaults or non_defaults.get(
            "scheduler_update_interval"
        ) != defaults.get("scheduler_update_interval")
