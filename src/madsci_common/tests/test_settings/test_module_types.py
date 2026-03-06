"""Tests for ModuleSettings and related types."""

import pytest
from madsci.common.types.module_types import ModuleSettings, NodeModuleSettings


class TestModuleSettings:
    """Tests for the ModuleSettings class."""

    def test_default_values(self) -> None:
        """Test that ModuleSettings has correct default values."""
        settings = ModuleSettings(module_name="test_module")

        assert settings.module_name == "test_module"
        assert settings.module_version == "0.0.1"
        assert settings.repository_url is None
        assert settings.documentation_url is None
        assert settings.interface_variant == "real"

    def test_interface_variant_options(self) -> None:
        """Test that interface_variant accepts valid options."""
        for variant in ["real", "fake", "sim"]:
            settings = ModuleSettings(module_name="test", interface_variant=variant)
            assert settings.interface_variant == variant

    def test_from_env_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test loading settings from environment variables."""
        monkeypatch.setenv("MODULE_MODULE_NAME", "env_module")
        monkeypatch.setenv("MODULE_MODULE_VERSION", "1.2.3")
        monkeypatch.setenv("MODULE_INTERFACE_VARIANT", "fake")
        monkeypatch.setenv("MODULE_REPOSITORY_URL", "https://github.com/test/repo")

        settings = ModuleSettings()

        assert settings.module_name == "env_module"
        assert settings.module_version == "1.2.3"
        assert settings.interface_variant == "fake"
        assert settings.repository_url == "https://github.com/test/repo"

    def test_explicit_values_override_env(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that explicit values override environment variables."""
        monkeypatch.setenv("MODULE_MODULE_NAME", "env_module")

        settings = ModuleSettings(module_name="explicit_module")

        assert settings.module_name == "explicit_module"


class TestNodeModuleSettings:
    """Tests for the NodeModuleSettings class."""

    def test_default_values(self) -> None:
        """Test that NodeModuleSettings has correct default values."""
        settings = NodeModuleSettings(module_name="test_module", name="test_node")

        assert settings.module_name == "test_module"
        assert settings.name == "test_node"
        assert settings.description is None
        assert settings.lab_url is None
        assert settings.workcell_url is None
        assert settings.simulate is False

    def test_inherits_module_settings(self) -> None:
        """Test that NodeModuleSettings inherits from ModuleSettings."""
        settings = NodeModuleSettings(
            module_name="test_module",
            name="test_node",
            interface_variant="fake",
        )

        assert settings.interface_variant == "fake"
        assert settings.module_version == "0.0.1"

    def test_from_env_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test loading NodeModuleSettings from environment variables."""
        monkeypatch.setenv("NODE_MODULE_NAME", "env_module")
        monkeypatch.setenv("NODE_NAME", "env_node")
        monkeypatch.setenv("NODE_SIMULATE", "true")
        monkeypatch.setenv("NODE_LAB_URL", "http://localhost:8000")

        settings = NodeModuleSettings()

        assert settings.module_name == "env_module"
        assert settings.name == "env_node"
        assert settings.simulate is True
        assert settings.lab_url == "http://localhost:8000"

    def test_simulation_mode(self) -> None:
        """Test that simulation mode can be enabled."""
        settings = NodeModuleSettings(
            module_name="test_module",
            name="test_node",
            simulate=True,
        )

        assert settings.simulate is True


class TestCustomModuleSettings:
    """Tests for creating custom module settings classes."""

    def test_custom_module_settings(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test creating a custom module settings class."""
        from pydantic import Field  # noqa: PLC0415

        class FooModuleSettings(ModuleSettings, env_prefix="FOO_"):
            """Custom settings for Foo module."""

            module_name: str = "foo"
            max_speed: float = Field(default=100.0)

        monkeypatch.setenv("FOO_MAX_SPEED", "150.0")

        settings = FooModuleSettings()

        assert settings.module_name == "foo"
        assert settings.max_speed == 150.0

    def test_custom_node_settings(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test creating a custom node settings class."""
        from pydantic import Field  # noqa: PLC0415

        class FooNodeSettings(NodeModuleSettings, env_prefix="FOO_"):
            """Custom settings for Foo node."""

            module_name: str = "foo"
            max_speed: float = Field(default=100.0)
            home_on_startup: bool = Field(default=True)

        monkeypatch.setenv("FOO_NAME", "foo_1")
        monkeypatch.setenv("FOO_MAX_SPEED", "200.0")
        monkeypatch.setenv("FOO_HOME_ON_STARTUP", "false")

        settings = FooNodeSettings()

        assert settings.name == "foo_1"
        assert settings.max_speed == 200.0
        assert settings.home_on_startup is False
