"""Unit tests for madsci.workcell_manager.workcell_utils module."""

from unittest.mock import MagicMock, patch

from madsci.client.node import AbstractNodeClient
from madsci.workcell_manager.workcell_utils import find_node_client


class MockNodeClient(AbstractNodeClient):
    """Mock node client for testing."""

    def __init__(self, url: str):
        self.url = url

    @classmethod
    def validate_url(cls, url: str) -> bool:
        return url.startswith("mock://")

    def get_status(self):
        return {"status": "ok"}

    def execute_action(self, action: str, **kwargs):  # noqa: ARG002
        return {"result": f"executed {action}"}


class AnotherMockNodeClient(AbstractNodeClient):
    """Another mock node client for testing."""

    def __init__(self, url: str):
        self.url = url

    @classmethod
    def validate_url(cls, url: str) -> bool:
        return url.startswith("another://")

    def get_status(self):
        return {"status": "ok"}

    def execute_action(self, action: str, **kwargs):  # noqa: ARG002
        return {"result": f"executed {action}"}


def test_find_node_client_from_node_client_map():
    """Test finding node client from NODE_CLIENT_MAP."""
    mock_client_class = MagicMock()
    mock_client_class.validate_url.return_value = True
    mock_client_instance = MagicMock()
    mock_client_class.return_value = mock_client_instance

    with patch(
        "madsci.workcell_manager.workcell_utils.NODE_CLIENT_MAP",
        {"test": mock_client_class},
    ):
        result = find_node_client("http://test.com")

        assert result == mock_client_instance
        mock_client_class.validate_url.assert_called_once_with("http://test.com")
        mock_client_class.assert_called_once_with("http://test.com")


def test_find_node_client_from_subclasses():
    """Test finding node client from AbstractNodeClient subclasses."""
    # Mock the NODE_CLIENT_MAP to be empty
    with (
        patch("madsci.workcell_manager.workcell_utils.NODE_CLIENT_MAP", {}),
        patch.object(
            AbstractNodeClient, "__subclasses__", return_value=[MockNodeClient]
        ),
    ):
        result = find_node_client("mock://test.com")

        assert isinstance(result, MockNodeClient)
        assert result.url == "mock://test.com"


def test_find_node_client_no_match():
    """Test find_node_client returns None when no client matches."""
    # Mock both NODE_CLIENT_MAP and subclasses to be empty/non-matching
    with (
        patch("madsci.workcell_manager.workcell_utils.NODE_CLIENT_MAP", {}),
        patch.object(AbstractNodeClient, "__subclasses__", return_value=[]),
    ):
        result = find_node_client("unsupported://test.com")

        assert result is None


def test_find_node_client_multiple_subclasses():
    """Test find_node_client with multiple subclasses."""
    with (
        patch("madsci.workcell_manager.workcell_utils.NODE_CLIENT_MAP", {}),
        patch.object(
            AbstractNodeClient,
            "__subclasses__",
            return_value=[MockNodeClient, AnotherMockNodeClient],
        ),
    ):
        # Test first client matches
        result1 = find_node_client("mock://test.com")
        assert isinstance(result1, MockNodeClient)

        # Test second client matches
        result2 = find_node_client("another://test.com")
        assert isinstance(result2, AnotherMockNodeClient)


def test_find_node_client_node_client_map_priority():
    """Test that NODE_CLIENT_MAP takes priority over subclasses."""
    mock_client_from_map = MagicMock()
    mock_client_from_map.validate_url.return_value = True
    mock_instance_from_map = MagicMock()
    mock_client_from_map.return_value = mock_instance_from_map

    with (
        patch(
            "madsci.workcell_manager.workcell_utils.NODE_CLIENT_MAP",
            {"priority": mock_client_from_map},
        ),
        patch.object(
            AbstractNodeClient, "__subclasses__", return_value=[MockNodeClient]
        ),
    ):
        result = find_node_client(
            "mock://test.com"
        )  # MockNodeClient would normally handle this

        # Should use the NODE_CLIENT_MAP client instead
        assert result == mock_instance_from_map
        mock_client_from_map.validate_url.assert_called_once()


def test_find_node_client_validation_fails():
    """Test find_node_client when validation fails for all clients."""
    mock_client = MagicMock()
    mock_client.validate_url.return_value = False

    with (
        patch(
            "madsci.workcell_manager.workcell_utils.NODE_CLIENT_MAP",
            {"test": mock_client},
        ),
        patch.object(AbstractNodeClient, "__subclasses__", return_value=[]),
    ):
        result = find_node_client("http://test.com")

        assert result is None
        mock_client.validate_url.assert_called_once_with("http://test.com")
