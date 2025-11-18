"""Unit tests for MadsciClientMixin."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from madsci.client.client_mixin import MadsciClientMixin
from madsci.client.data_client import DataClient
from madsci.client.event_client import EventClient
from madsci.client.experiment_client import ExperimentClient
from madsci.client.lab_client import LabClient
from madsci.client.location_client import LocationClient
from madsci.client.resource_client import ResourceClient
from madsci.client.workcell_client import WorkcellClient
from madsci.common.types.context_types import MadsciContext
from madsci.common.types.event_types import EventClientConfig
from pydantic import AnyUrl


@pytest.fixture
def temp_log_dir():
    """Create a temporary directory for log files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def mock_context():
    """Create a mock MADSci context."""
    return MadsciContext(
        event_server_url=AnyUrl("http://localhost:8001"),
        experiment_server_url=AnyUrl("http://localhost:8002"),
        resource_server_url=AnyUrl("http://localhost:8003"),
        data_server_url=AnyUrl("http://localhost:8004"),
        workcell_server_url=AnyUrl("http://localhost:8005"),
        location_server_url=AnyUrl("http://localhost:8006"),
        lab_server_url=AnyUrl("http://localhost:8000"),
    )


class TestMixinBasicUsage:
    """Test basic usage patterns of MadsciClientMixin."""

    def test_mixin_can_be_inherited(self):
        """Test that mixin can be inherited by a class."""

        class MyComponent(MadsciClientMixin):
            pass

        component = MyComponent()
        assert isinstance(component, MadsciClientMixin)

    def test_mixin_with_required_clients(self, temp_log_dir, mock_context):
        """Test mixin with REQUIRED_CLIENTS class attribute."""

        class MyComponent(MadsciClientMixin):
            REQUIRED_CLIENTS = ["event", "resource"]

        with patch(
            "madsci.client.client_mixin.get_current_madsci_context",
            return_value=mock_context,
        ):
            with patch("madsci.client.event_client.EventClientConfig") as mock_config:
                mock_config.return_value.name = None
                mock_config.return_value.log_dir = temp_log_dir
                mock_config.return_value.log_level = "INFO"
                mock_config.return_value.event_server_url = None

                with patch(
                    "madsci.client.event_client.get_current_madsci_context",
                    return_value=mock_context,
                ):
                    with patch("madsci.client.resource_client.requests.get"):
                        component = MyComponent()
                        component.setup_clients()

                        assert component._event_client is not None
                        assert component._resource_client is not None
                        assert component._data_client is None

    def test_lazy_initialization(self, temp_log_dir, mock_context):
        """Test that clients are lazily initialized."""

        class MyComponent(MadsciClientMixin):
            pass

        with patch(
            "madsci.client.client_mixin.get_current_madsci_context",
            return_value=mock_context,
        ):
            with patch("madsci.client.event_client.EventClientConfig") as mock_config:
                mock_config.return_value.name = None
                mock_config.return_value.log_dir = temp_log_dir
                mock_config.return_value.log_level = "INFO"
                mock_config.return_value.event_server_url = None

                with patch(
                    "madsci.client.event_client.get_current_madsci_context",
                    return_value=mock_context,
                ):
                    component = MyComponent()

                    # No clients initialized yet
                    assert component._event_client is None

                    # Access property triggers lazy initialization
                    event_client = component.event_client
                    assert component._event_client is not None
                    assert isinstance(event_client, EventClient)


class TestEventClientCreation:
    """Test EventClient creation and configuration."""

    def test_create_event_client_default(self, temp_log_dir, mock_context):
        """Test default EventClient creation."""

        class MyComponent(MadsciClientMixin):
            pass

        with patch(
            "madsci.client.client_mixin.get_current_madsci_context",
            return_value=mock_context,
        ):
            with patch("madsci.client.event_client.EventClientConfig") as mock_config:
                mock_config.return_value.name = None
                mock_config.return_value.log_dir = temp_log_dir
                mock_config.return_value.log_level = "INFO"
                mock_config.return_value.event_server_url = None

                with patch(
                    "madsci.client.event_client.get_current_madsci_context",
                    return_value=mock_context,
                ):
                    component = MyComponent()
                    client = component.event_client

                    assert isinstance(client, EventClient)

    def test_create_event_client_with_config(self, temp_log_dir, mock_context):
        """Test EventClient creation with explicit config."""

        class MyComponent(MadsciClientMixin):
            pass

        config = EventClientConfig(
            name="test_component",
            log_dir=temp_log_dir,
            event_server_url="http://localhost:8001",
        )

        with patch(
            "madsci.client.client_mixin.get_current_madsci_context",
            return_value=mock_context,
        ):
            component = MyComponent()
            component.event_client_config = config
            client = component.event_client

            assert isinstance(client, EventClient)
            assert client.config == config

    def test_create_event_client_with_url_override(self, temp_log_dir, mock_context):
        """Test EventClient creation with URL override."""

        class MyComponent(MadsciClientMixin):
            pass

        with patch(
            "madsci.client.client_mixin.get_current_madsci_context",
            return_value=mock_context,
        ):
            with patch("madsci.client.event_client.EventClientConfig") as mock_config:
                mock_config.return_value.name = None
                mock_config.return_value.log_dir = temp_log_dir
                mock_config.return_value.log_level = "INFO"
                mock_config.return_value.event_server_url = "http://custom:9001"

                with patch(
                    "madsci.client.event_client.get_current_madsci_context",
                    return_value=mock_context,
                ):
                    component = MyComponent()
                    component.event_server_url = "http://custom:9001"
                    client = component.event_client

                    assert isinstance(client, EventClient)


class TestResourceClientCreation:
    """Test ResourceClient creation and configuration."""

    def test_create_resource_client_default(self, mock_context):
        """Test default ResourceClient creation."""

        class MyComponent(MadsciClientMixin):
            pass

        with patch(
            "madsci.client.client_mixin.get_current_madsci_context",
            return_value=mock_context,
        ):
            with patch("madsci.client.resource_client.requests.get"):
                with patch(
                    "madsci.client.resource_client.get_current_madsci_context",
                    return_value=mock_context,
                ):
                    with patch("madsci.client.resource_client.EventClient"):
                        component = MyComponent()
                        client = component.resource_client

                        assert isinstance(client, ResourceClient)

    def test_create_resource_client_with_shared_event_client(
        self, temp_log_dir, mock_context
    ):
        """Test ResourceClient creation with shared EventClient."""

        class MyComponent(MadsciClientMixin):
            REQUIRED_CLIENTS = ["event"]

        with patch(
            "madsci.client.client_mixin.get_current_madsci_context",
            return_value=mock_context,
        ):
            with patch("madsci.client.event_client.EventClientConfig") as mock_config:
                mock_config.return_value.name = None
                mock_config.return_value.log_dir = temp_log_dir
                mock_config.return_value.log_level = "INFO"
                mock_config.return_value.event_server_url = None

                with patch(
                    "madsci.client.event_client.get_current_madsci_context",
                    return_value=mock_context,
                ):
                    with patch("madsci.client.resource_client.requests.get"):
                        with patch(
                            "madsci.client.resource_client.get_current_madsci_context",
                            return_value=mock_context,
                        ):
                            component = MyComponent()
                            component.setup_clients()

                            # Get EventClient first
                            event_client = component.event_client

                            # ResourceClient should use the shared EventClient
                            resource_client = component.resource_client
                            assert isinstance(resource_client, ResourceClient)
                            # The EventClient should have been passed to ResourceClient
                            assert resource_client.logger == event_client


class TestDataClientCreation:
    """Test DataClient creation and configuration."""

    def test_create_data_client_default(self, mock_context):
        """Test default DataClient creation."""

        class MyComponent(MadsciClientMixin):
            pass

        with patch(
            "madsci.client.client_mixin.get_current_madsci_context",
            return_value=mock_context,
        ):
            with patch(
                "madsci.client.data_client.get_current_madsci_context",
                return_value=mock_context,
            ):
                with patch("madsci.client.data_client.create_minio_client"):
                    with patch("madsci.client.data_client.EventClient"):
                        component = MyComponent()
                        client = component.data_client

                        assert isinstance(client, DataClient)


class TestExperimentClientCreation:
    """Test ExperimentClient creation and configuration."""

    def test_create_experiment_client_default(self, mock_context):
        """Test default ExperimentClient creation."""

        class MyComponent(MadsciClientMixin):
            pass

        with patch(
            "madsci.client.client_mixin.get_current_madsci_context",
            return_value=mock_context,
        ):
            with patch(
                "madsci.client.experiment_client.get_current_madsci_context",
                return_value=mock_context,
            ):
                component = MyComponent()
                client = component.experiment_client

                assert isinstance(client, ExperimentClient)


class TestWorkcellClientCreation:
    """Test WorkcellClient creation and configuration."""

    def test_create_workcell_client_default(self, temp_log_dir, mock_context):
        """Test default WorkcellClient creation."""

        class MyComponent(MadsciClientMixin):
            pass

        with patch(
            "madsci.client.client_mixin.get_current_madsci_context",
            return_value=mock_context,
        ):
            with patch(
                "madsci.client.workcell_client.get_current_madsci_context",
                return_value=mock_context,
            ):
                with patch("madsci.client.workcell_client.EventClient"):
                    component = MyComponent()
                    client = component.workcell_client

                    assert isinstance(client, WorkcellClient)

    def test_create_workcell_client_with_retry_config(self, temp_log_dir, mock_context):
        """Test WorkcellClient creation with retry configuration."""

        class MyComponent(MadsciClientMixin):
            pass

        with patch(
            "madsci.client.client_mixin.get_current_madsci_context",
            return_value=mock_context,
        ):
            with patch(
                "madsci.client.workcell_client.get_current_madsci_context",
                return_value=mock_context,
            ):
                with patch("madsci.client.workcell_client.EventClient"):
                    component = MyComponent()
                    component.client_retry_enabled = True
                    component.client_retry_total = 5

                    client = component.workcell_client

                    assert isinstance(client, WorkcellClient)
                    assert client.retry is True


class TestLocationClientCreation:
    """Test LocationClient creation and configuration."""

    def test_create_location_client_default(self, mock_context):
        """Test default LocationClient creation."""

        class MyComponent(MadsciClientMixin):
            pass

        with patch(
            "madsci.client.client_mixin.get_current_madsci_context",
            return_value=mock_context,
        ):
            with patch(
                "madsci.client.location_client.get_current_madsci_context",
                return_value=mock_context,
            ):
                with patch("madsci.client.location_client.EventClient"):
                    component = MyComponent()
                    client = component.location_client

                    assert isinstance(client, LocationClient)


class TestLabClientCreation:
    """Test LabClient creation and configuration."""

    def test_create_lab_client_default(self, mock_context):
        """Test default LabClient creation."""

        class MyComponent(MadsciClientMixin):
            pass

        with patch(
            "madsci.client.client_mixin.get_current_madsci_context",
            return_value=mock_context,
        ):
            with patch(
                "madsci.client.lab_client.get_current_madsci_context",
                return_value=mock_context,
            ):
                component = MyComponent()
                client = component.lab_client

                assert isinstance(client, LabClient)


class TestSetupClients:
    """Test setup_clients method."""

    def test_setup_specific_clients(self, temp_log_dir, mock_context):
        """Test setup_clients with specific client list."""

        class MyComponent(MadsciClientMixin):
            pass

        with patch(
            "madsci.client.client_mixin.get_current_madsci_context",
            return_value=mock_context,
        ):
            with patch("madsci.client.event_client.EventClientConfig") as mock_config:
                mock_config.return_value.name = None
                mock_config.return_value.log_dir = temp_log_dir
                mock_config.return_value.log_level = "INFO"
                mock_config.return_value.event_server_url = None

                with patch(
                    "madsci.client.event_client.get_current_madsci_context",
                    return_value=mock_context,
                ):
                    with patch(
                        "madsci.client.experiment_client.get_current_madsci_context",
                        return_value=mock_context,
                    ):
                        component = MyComponent()
                        component.setup_clients(clients=["event", "experiment"])

                        assert component._event_client is not None
                        assert component._experiment_client is not None
                        assert component._resource_client is None

    def test_setup_with_injected_client(self):
        """Test setup_clients with pre-initialized client."""

        class MyComponent(MadsciClientMixin):
            pass

        mock_event_client = Mock(spec=EventClient)
        component = MyComponent()
        component.setup_clients(event_client=mock_event_client)

        assert component._event_client == mock_event_client

    def test_setup_multiple_injected_clients(self):
        """Test setup_clients with multiple pre-initialized clients."""

        class MyComponent(MadsciClientMixin):
            pass

        mock_event = Mock(spec=EventClient)
        mock_resource = Mock(spec=ResourceClient)
        mock_data = Mock(spec=DataClient)

        component = MyComponent()
        component.setup_clients(
            event_client=mock_event,
            resource_client=mock_resource,
            data_client=mock_data,
        )

        assert component._event_client == mock_event
        assert component._resource_client == mock_resource
        assert component._data_client == mock_data


class TestClientSetters:
    """Test client property setters."""

    def test_event_client_setter(self):
        """Test setting EventClient directly."""

        class MyComponent(MadsciClientMixin):
            pass

        mock_client = Mock(spec=EventClient)
        component = MyComponent()
        component.event_client = mock_client

        assert component._event_client == mock_client
        assert component.event_client == mock_client

    def test_resource_client_setter(self):
        """Test setting ResourceClient directly."""

        class MyComponent(MadsciClientMixin):
            pass

        mock_client = Mock(spec=ResourceClient)
        component = MyComponent()
        component.resource_client = mock_client

        assert component._resource_client == mock_client
        assert component.resource_client == mock_client


class TestTeardownClients:
    """Test teardown_clients method."""

    def test_teardown_clients(self):
        """Test teardown_clients method (currently a no-op)."""

        class MyComponent(MadsciClientMixin):
            pass

        component = MyComponent()
        # Should not raise any exceptions
        component.teardown_clients()
