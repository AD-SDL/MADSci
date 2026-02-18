"""Tests for Phase G.5: NodeInfo.from_config() factory method."""

from madsci.common.types.node_types import (
    NodeConfig,
    NodeDefinition,
    NodeInfo,
    NodeType,
    RestNodeConfig,
)
from madsci.common.utils import new_ulid_str


class TestNodeInfoFromConfig:
    """Tests for the new from_config() factory."""

    def test_from_config_basic(self) -> None:
        """from_config creates NodeInfo from config settings."""
        config = RestNodeConfig(
            node_name="test_node",
            module_name="test_module",
            module_version="1.0.0",
        )
        info = NodeInfo.from_config(config)
        assert info.node_name == "test_node"
        assert info.module_name == "test_module"
        assert str(info.module_version) == "1.0.0"
        assert info.config_schema is not None

    def test_from_config_with_node_type(self) -> None:
        """from_config respects node_type setting."""
        config = RestNodeConfig(
            node_name="compute_node",
            module_name="compute_module",
            module_version="2.0.0",
            node_type=NodeType.COMPUTE,
        )
        info = NodeInfo.from_config(config)
        assert info.node_type == NodeType.COMPUTE

    def test_from_config_with_node_id(self) -> None:
        """from_config respects explicit node_id."""
        custom_id = new_ulid_str()
        config = RestNodeConfig(
            node_name="my_node",
            module_name="my_module",
            module_version="1.0.0",
            node_id=custom_id,
        )
        info = NodeInfo.from_config(config)
        assert info.node_id == custom_id

    def test_from_config_defaults(self) -> None:
        """from_config provides defaults for required fields."""
        config = NodeConfig()
        info = NodeInfo.from_config(config)
        assert info.node_name == "unnamed_node"
        assert info.module_name == "unknown_module"
        assert info.node_id is not None

    def test_from_config_with_definition_fallback(self) -> None:
        """from_config uses definition values as fallback."""
        config = NodeConfig()
        node_def = NodeDefinition(
            node_name="def_node",
            module_name="def_module",
        )
        info = NodeInfo.from_config(config, node_definition=node_def)
        assert info.node_name == "def_node"  # falls back to definition
        assert info.module_name == "def_module"

    def test_from_config_overrides_definition(self) -> None:
        """from_config config fields override definition values."""
        config = RestNodeConfig(
            node_name="config_node",
            module_name="config_module",
            module_version="2.0.0",
        )
        node_def = NodeDefinition(
            node_name="def_node",
            module_name="def_module",
        )
        info = NodeInfo.from_config(config, node_definition=node_def)
        assert info.node_name == "config_node"  # config overrides def
        assert info.module_name == "config_module"

    def test_from_config_kwargs_override_all(self) -> None:
        """from_config explicit kwargs override both config and definition."""
        config = RestNodeConfig(
            node_name="config_node",
            module_name="config_module",
            module_version="1.0.0",
        )
        info = NodeInfo.from_config(
            config, node_name="explicit_name", module_name="explicit_module"
        )
        assert info.node_name == "explicit_name"
        assert info.module_name == "explicit_module"


class TestNodeInfoFromNodeDefAndConfig:
    """Tests that the legacy factory still works."""

    def test_from_node_def_and_config(self) -> None:
        """Legacy factory creates NodeInfo from definition."""
        node_def = NodeDefinition(
            node_name="legacy_node",
            module_name="legacy_module",
        )
        config = RestNodeConfig()
        info = NodeInfo.from_node_def_and_config(node_def, config)
        assert info.node_name == "legacy_node"
        assert info.config_schema is not None

    def test_from_node_def_and_config_no_config(self) -> None:
        """Legacy factory works without config."""
        node_def = NodeDefinition(
            node_name="bare_node",
            module_name="bare_module",
        )
        info = NodeInfo.from_node_def_and_config(node_def)
        assert info.node_name == "bare_node"


class TestNodeConfigIdentityFields:
    """Tests for the new identity fields on NodeConfig."""

    def test_identity_fields_optional(self) -> None:
        """Identity fields default to None."""
        config = NodeConfig()
        assert config.node_name is None
        assert config.node_id is None
        assert config.node_type is None
        assert config.module_name is None
        assert config.module_version is None

    def test_identity_fields_settable(self) -> None:
        """Identity fields can be set."""
        config = NodeConfig(
            node_name="my_node",
            node_id="01ABC",
            node_type=NodeType.DEVICE,
            module_name="my_mod",
            module_version="1.2.3",
        )
        assert config.node_name == "my_node"
        assert config.node_id == "01ABC"
        assert config.node_type == NodeType.DEVICE
        assert config.module_name == "my_mod"
        assert config.module_version == "1.2.3"
