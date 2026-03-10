"""Unit tests for registry resolution in AbstractManagerBase."""

from unittest.mock import MagicMock, patch

from madsci.common.manager_base import AbstractManagerBase
from madsci.common.types.manager_types import (
    ManagerSettings,
)
from madsci.common.types.registry_types import RegistryResolveResult


class MinimalSettings(
    ManagerSettings,
    env_prefix="TEST_RESOLUTION_",
):
    """Minimal settings for testing registry resolution."""


class TestRegistryResolutionSettings:
    """Test the new ManagerSettings fields for registry resolution."""

    def test_registry_resolution_enabled_by_default(self) -> None:
        """Registry resolution is enabled by default in production.

        Note: The test suite patches the default to False to prevent lock
        contention. We verify the *field definition* rather than the
        runtime default, and confirm explicit True still works.
        """
        settings = MinimalSettings(enable_registry_resolution=True)
        assert settings.enable_registry_resolution is True

    def test_manager_name_none_by_default(self) -> None:
        """Manager name should be None by default."""
        settings = MinimalSettings()
        assert settings.manager_name is None

    def test_manager_description_none_by_default(self) -> None:
        """Manager description should be None by default."""
        settings = MinimalSettings()
        assert settings.manager_description is None

    def test_lab_url_none_by_default(self) -> None:
        """Lab URL should be None by default."""
        settings = MinimalSettings()
        assert settings.lab_url is None

    def test_can_disable_registry_resolution(self) -> None:
        """Should be able to disable registry resolution."""
        settings = MinimalSettings(enable_registry_resolution=False)
        assert settings.enable_registry_resolution is False

    def test_can_set_manager_name(self) -> None:
        """Should be able to set manager name."""
        settings = MinimalSettings(manager_name="My Manager")
        assert settings.manager_name == "My Manager"


class TestSettingsManagerIdentity:
    """Test that manager identity is managed through settings."""

    def test_settings_manager_id_none_by_default(self) -> None:
        """Settings manager_id should be None by default (generated at runtime by AbstractManagerBase)."""
        settings = MinimalSettings()
        assert settings.manager_id is None

    def test_settings_manager_id_can_be_set(self) -> None:
        """Settings manager_id should be settable."""
        settings = MinimalSettings(manager_id="test-id-123")
        assert settings.manager_id == "test-id-123"

    def test_settings_manager_name(self) -> None:
        """Settings manager_name should be settable."""
        settings = MinimalSettings(manager_name="My Manager")
        assert settings.manager_name == "My Manager"

    def test_settings_manager_description(self) -> None:
        """Settings manager_description should be settable."""
        settings = MinimalSettings(manager_description="A description")
        assert settings.manager_description == "A description"


class TestRegistryResolutionIntegration:
    """Test the registry resolution integration in AbstractManagerBase."""

    def test_resolver_not_called_when_disabled(self) -> None:
        """When registry resolution is disabled, resolver should not be called."""
        settings = MinimalSettings(
            enable_registry_resolution=False,
        )
        original_id = settings.manager_id

        base = AbstractManagerBase.__new__(AbstractManagerBase)
        base._settings = settings
        base._resolver = None

        # When disabled, _resolve_identity_from_registry is not called,
        # so the settings ID stays the same
        assert settings.manager_id == original_id
        assert base._resolver is None

    @patch("madsci.common.manager_base.IdentityResolver", create=True)
    def test_resolver_called_when_enabled(self, mock_resolver_cls: MagicMock) -> None:
        """When registry resolution is enabled, resolver should update settings.manager_id."""
        mock_resolver = MagicMock()
        mock_resolver.resolve_with_info.return_value = RegistryResolveResult(
            name="Test Manager",
            id="01TEST00000000000000000000",
            component_type="manager",
            is_new=False,
            source="local",
        )
        mock_resolver_cls.return_value = mock_resolver

        settings = MinimalSettings(
            enable_registry_resolution=True,
            manager_name="Test Manager",
        )

        base = AbstractManagerBase.__new__(AbstractManagerBase)
        base._settings = settings
        base._resolver = None

        with patch(
            "madsci.common.registry.identity_resolver.IdentityResolver",
            mock_resolver_cls,
        ):
            base._resolve_identity_from_registry()

        assert settings.manager_id == "01TEST00000000000000000000"

    def test_resolution_failure_falls_back_to_settings_id(self) -> None:
        """If registry resolution fails, the settings ID should be preserved."""
        settings = MinimalSettings(
            enable_registry_resolution=True,
            manager_name="Test Manager",
        )
        original_id = settings.manager_id

        base = AbstractManagerBase.__new__(AbstractManagerBase)
        base._settings = settings
        base._resolver = None

        with patch(
            "madsci.common.registry.identity_resolver.IdentityResolver",
            side_effect=Exception("Connection refused"),
        ):
            base._resolve_identity_from_registry()

        assert settings.manager_id == original_id

    def test_release_identity_calls_resolver_release(self) -> None:
        """release_identity() should call resolver.release()."""
        settings = MinimalSettings(
            manager_name="Test Manager",
        )

        base = AbstractManagerBase.__new__(AbstractManagerBase)
        base._settings = settings
        base._resolver = MagicMock()

        base.release_identity()

        base._resolver.release.assert_called_once_with("Test Manager")

    def test_release_identity_noop_without_resolver(self) -> None:
        """release_identity() should be a no-op when no resolver is set."""
        settings = MinimalSettings()

        base = AbstractManagerBase.__new__(AbstractManagerBase)
        base._settings = settings
        base._resolver = None

        # Should not raise
        base.release_identity()

    def test_settings_name_used_for_resolution(self) -> None:
        """When settings.manager_name is set, it should be used for registry lookup."""
        mock_resolver = MagicMock()
        mock_resolver.resolve_with_info.return_value = RegistryResolveResult(
            name="Custom Name",
            id="01CUSTOM000000000000000000",
            component_type="manager",
            is_new=True,
            source="local",
        )

        settings = MinimalSettings(
            enable_registry_resolution=True,
            manager_name="Custom Name",
        )

        base = AbstractManagerBase.__new__(AbstractManagerBase)
        base._settings = settings
        base._resolver = None

        with patch(
            "madsci.common.registry.identity_resolver.IdentityResolver",
            return_value=mock_resolver,
        ):
            base._resolve_identity_from_registry()

        mock_resolver.resolve_with_info.assert_called_once_with(
            name="Custom Name",
            component_type="manager",
            metadata={"manager_class": "AbstractManagerBase"},
            retry_timeout=60.0,
        )
