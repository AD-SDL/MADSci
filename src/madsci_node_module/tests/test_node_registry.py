"""Unit tests for registry resolution in AbstractNode."""

from unittest.mock import MagicMock, patch

from madsci.common.types.node_types import NodeConfig
from madsci.common.types.registry_types import RegistryResolveResult
from madsci.common.utils import new_ulid_str

from madsci_node_module.tests.test_node import TestNode, TestNodeConfig


class TestNodeRegistrySettings:
    """Test the registry-related fields on NodeConfig."""

    def test_registry_resolution_enabled_by_default(self) -> None:
        """Registry resolution should be enabled by default."""
        config = NodeConfig()
        assert config.enable_registry_resolution is True

    def test_lab_url_none_by_default(self) -> None:
        """Lab URL should be None by default."""
        config = NodeConfig()
        assert config.lab_url is None

    def test_registry_lock_timeout_default(self) -> None:
        """Registry lock timeout should default to 60 seconds."""
        config = NodeConfig()
        assert config.registry_lock_timeout == 60.0

    def test_can_disable_registry_resolution(self) -> None:
        """Should be able to disable registry resolution."""
        config = NodeConfig(enable_registry_resolution=False)
        assert config.enable_registry_resolution is False


class TestNodeRegistryResolution:
    """Test the registry resolution integration in AbstractNode."""

    def test_resolver_not_called_when_disabled(self) -> None:
        """When registry resolution is disabled, resolver should not be called."""
        config = TestNodeConfig(
            test_required_param=1,
            node_name="test_node",
            enable_registry_resolution=False,
        )
        node = TestNode(node_config=config)

        assert node._resolver is None

    def test_resolver_called_when_enabled(self) -> None:
        """When registry resolution is enabled, resolver should update node_info.node_id."""
        resolved_id = new_ulid_str()
        mock_resolver = MagicMock()
        mock_resolver.resolve_with_info.return_value = RegistryResolveResult(
            name="test_node",
            id=resolved_id,
            component_type="node",
            is_new=False,
            source="local",
        )
        mock_resolver_cls = MagicMock(return_value=mock_resolver)

        config = TestNodeConfig(
            test_required_param=1,
            node_name="test_node",
            enable_registry_resolution=True,
        )

        with patch(
            "madsci.common.registry.identity_resolver.IdentityResolver",
            mock_resolver_cls,
        ):
            node = TestNode(node_config=config)

        assert node.node_info.node_id == resolved_id

    def test_resolution_failure_falls_back_to_generated_id(self) -> None:
        """If registry resolution fails, the generated ID should be preserved."""
        config = TestNodeConfig(
            test_required_param=1,
            node_name="test_node",
            enable_registry_resolution=True,
        )

        with patch(
            "madsci.common.registry.identity_resolver.IdentityResolver",
            side_effect=Exception("Connection refused"),
        ):
            node = TestNode(node_config=config)

        # The node should still have a valid node_id (the originally generated one)
        assert node.node_info.node_id is not None
        assert len(node.node_info.node_id) > 0

    def test_stable_id_across_restarts(self) -> None:
        """Two sequential node instances with the same name should get the same ID."""
        stable_id = new_ulid_str()
        mock_resolver = MagicMock()
        mock_resolver.resolve_with_info.return_value = RegistryResolveResult(
            name="stable_node",
            id=stable_id,
            component_type="node",
            is_new=False,
            source="local",
        )
        mock_resolver_cls = MagicMock(return_value=mock_resolver)

        with patch(
            "madsci.common.registry.identity_resolver.IdentityResolver",
            mock_resolver_cls,
        ):
            node1 = TestNode(
                node_config=TestNodeConfig(
                    test_required_param=1,
                    node_name="stable_node",
                    enable_registry_resolution=True,
                )
            )
            node1._release_registry_identity()

            node2 = TestNode(
                node_config=TestNodeConfig(
                    test_required_param=1,
                    node_name="stable_node",
                    enable_registry_resolution=True,
                )
            )

        assert node1.node_info.node_id == stable_id
        assert node2.node_info.node_id == stable_id

    def test_registry_disabled_generates_ulid(self) -> None:
        """With enable_registry_resolution=False, a fresh ULID should be generated."""
        node1 = TestNode(
            node_config=TestNodeConfig(
                test_required_param=1,
                node_name="ulid_node",
                enable_registry_resolution=False,
            )
        )
        node2 = TestNode(
            node_config=TestNodeConfig(
                test_required_param=1,
                node_name="ulid_node",
                enable_registry_resolution=False,
            )
        )

        # Both should have IDs, but they should be different (fresh ULIDs)
        assert node1.node_info.node_id is not None
        assert node2.node_info.node_id is not None
        assert node1.node_info.node_id != node2.node_info.node_id

    def test_release_identity_calls_resolver_release(self) -> None:
        """_release_registry_identity() should call resolver.release()."""
        config = TestNodeConfig(
            test_required_param=1,
            node_name="release_test_node",
            enable_registry_resolution=False,
        )
        node = TestNode(node_config=config)
        node._resolver = MagicMock()

        node._release_registry_identity()

        node._resolver.release.assert_called_once_with("release_test_node")

    def test_release_identity_noop_without_resolver(self) -> None:
        """_release_registry_identity() should be a no-op when no resolver is set."""
        config = TestNodeConfig(
            test_required_param=1,
            node_name="noop_node",
            enable_registry_resolution=False,
        )
        node = TestNode(node_config=config)

        # Should not raise
        node._release_registry_identity()

    def test_node_name_used_for_resolution(self) -> None:
        """The node name should be used for registry lookup."""
        resolved_id = new_ulid_str()
        mock_resolver = MagicMock()
        mock_resolver.resolve_with_info.return_value = RegistryResolveResult(
            name="custom_node",
            id=resolved_id,
            component_type="node",
            is_new=True,
            source="local",
        )
        mock_resolver_cls = MagicMock(return_value=mock_resolver)

        config = TestNodeConfig(
            test_required_param=1,
            node_name="custom_node",
            module_name="custom_module",
            enable_registry_resolution=True,
        )

        with patch(
            "madsci.common.registry.identity_resolver.IdentityResolver",
            mock_resolver_cls,
        ):
            TestNode(node_config=config)

        mock_resolver.resolve_with_info.assert_called_once_with(
            name="custom_node",
            component_type="node",
            metadata={"module_name": "custom_module"},
            retry_timeout=60.0,
        )
