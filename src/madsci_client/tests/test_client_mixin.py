"""Unit tests for MadsciClientMixin."""

from typing import ClassVar
from unittest.mock import Mock

from madsci.client.client_mixin import MadsciClientMixin
from madsci.client.data_client import DataClient
from madsci.client.event_client import EventClient
from madsci.client.experiment_client import ExperimentClient
from madsci.client.lab_client import LabClient
from madsci.client.location_client import LocationClient
from madsci.client.resource_client import ResourceClient
from madsci.client.workcell_client import WorkcellClient


class TestMixinBasicUsage:
    """Test basic usage patterns of MadsciClientMixin."""

    def test_mixin_can_be_inherited(self):
        """Test that mixin can be inherited by a class."""

        class MyComponent(MadsciClientMixin):
            pass

        component = MyComponent()
        assert isinstance(component, MadsciClientMixin)

    def test_required_clients_declaration(self):
        """Test that REQUIRED_CLIENTS can be declared."""

        class MyComponent(MadsciClientMixin):
            REQUIRED_CLIENTS: ClassVar[list[str]] = ["event", "resource"]

        assert MyComponent.REQUIRED_CLIENTS == ["event", "resource"]

    def test_lazy_initialization_does_not_create_clients_immediately(self):
        """Test that clients are not created until accessed."""

        class MyComponent(MadsciClientMixin):
            pass

        component = MyComponent()

        # No clients initialized yet
        assert component._event_client is None
        assert component._resource_client is None
        assert component._data_client is None


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

    def test_data_client_setter(self):
        """Test setting DataClient directly."""

        class MyComponent(MadsciClientMixin):
            pass

        mock_client = Mock(spec=DataClient)
        component = MyComponent()
        component.data_client = mock_client

        assert component._data_client == mock_client
        assert component.data_client == mock_client

    def test_experiment_client_setter(self):
        """Test setting ExperimentClient directly."""

        class MyComponent(MadsciClientMixin):
            pass

        mock_client = Mock(spec=ExperimentClient)
        component = MyComponent()
        component.experiment_client = mock_client

        assert component._experiment_client == mock_client
        assert component.experiment_client == mock_client

    def test_workcell_client_setter(self):
        """Test setting WorkcellClient directly."""

        class MyComponent(MadsciClientMixin):
            pass

        mock_client = Mock(spec=WorkcellClient)
        component = MyComponent()
        component.workcell_client = mock_client

        assert component._workcell_client == mock_client
        assert component.workcell_client == mock_client

    def test_location_client_setter(self):
        """Test setting LocationClient directly."""

        class MyComponent(MadsciClientMixin):
            pass

        mock_client = Mock(spec=LocationClient)
        component = MyComponent()
        component.location_client = mock_client

        assert component._location_client == mock_client
        assert component.location_client == mock_client

    def test_lab_client_setter(self):
        """Test setting LabClient directly."""

        class MyComponent(MadsciClientMixin):
            pass

        mock_client = Mock(spec=LabClient)
        component = MyComponent()
        component.lab_client = mock_client

        assert component._lab_client == mock_client
        assert component.lab_client == mock_client


class TestSetupClients:
    """Test setup_clients method."""

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

    def test_setup_clients_with_empty_required_list(self):
        """Test setup_clients with no required clients."""

        class MyComponent(MadsciClientMixin):
            REQUIRED_CLIENTS: ClassVar[list[str]] = []

        component = MyComponent()
        component.setup_clients()

        # Should not raise any errors, clients remain uninitialized
        assert component._event_client is None
        assert component._resource_client is None

    def test_setup_clients_respects_already_set_clients(self):
        """Test that setup_clients doesn't overwrite already-set clients."""

        class MyComponent(MadsciClientMixin):
            pass

        mock_event = Mock(spec=EventClient)
        component = MyComponent()

        # Set client directly
        component._event_client = mock_event

        # Setup should not overwrite
        component.setup_clients(clients=["event"])

        assert component._event_client == mock_event


class TestClientConfiguration:
    """Test client configuration options."""

    def test_event_client_config_attribute(self):
        """Test that event_client_config attribute is respected."""

        class MyComponent(MadsciClientMixin):
            pass

        component = MyComponent()
        # The mixin should have this attribute available
        assert hasattr(component, "event_client_config")

    def test_server_url_attributes_exist(self):
        """Test that server URL attributes can be set."""

        class MyComponent(MadsciClientMixin):
            pass

        component = MyComponent()

        # Should be able to set these attributes
        component.event_server_url = "http://localhost:8001"
        component.resource_server_url = "http://localhost:8003"
        component.data_server_url = "http://localhost:8004"
        component.experiment_server_url = "http://localhost:8002"
        component.workcell_server_url = "http://localhost:8005"
        component.location_server_url = "http://localhost:8006"
        component.lab_server_url = "http://localhost:8000"

        assert component.event_server_url == "http://localhost:8001"
        assert component.resource_server_url == "http://localhost:8003"

    def test_retry_configuration_attributes(self):
        """Test that retry configuration attributes exist."""

        class MyComponent(MadsciClientMixin):
            pass

        component = MyComponent()

        # Should have retry configuration attributes
        assert hasattr(component, "client_retry_enabled")
        assert hasattr(component, "client_retry_total")
        assert hasattr(component, "client_retry_backoff_factor")
        assert hasattr(component, "client_retry_status_forcelist")


class TestTeardownClients:
    """Test teardown_clients method."""

    def test_teardown_clients(self):
        """Test teardown_clients method (currently a no-op)."""

        class MyComponent(MadsciClientMixin):
            pass

        component = MyComponent()
        # Should not raise any exceptions
        component.teardown_clients()

    def test_teardown_clients_with_initialized_clients(self):
        """Test teardown_clients with initialized clients."""

        class MyComponent(MadsciClientMixin):
            pass

        mock_event = Mock(spec=EventClient)
        component = MyComponent()
        component.event_client = mock_event

        # Should not raise any exceptions
        component.teardown_clients()


class TestMixinIntegration:
    """Integration tests for the mixin."""

    def test_mixin_with_multiple_inheritance(self):
        """Test that mixin works with multiple inheritance."""

        class BaseClass:
            def __init__(self):
                self.base_value = "base"

        class MyComponent(BaseClass, MadsciClientMixin):
            def __init__(self):
                super().__init__()

        component = MyComponent()
        assert component.base_value == "base"
        assert isinstance(component, MadsciClientMixin)

    def test_client_injection_in_setup_clients(self):
        """Test that clients can be injected via setup_clients."""

        class MyComponent(MadsciClientMixin):
            REQUIRED_CLIENTS: ClassVar[list[str]] = ["event", "resource", "data"]

        mock_event = Mock(spec=EventClient)
        mock_resource = Mock(spec=ResourceClient)
        mock_data = Mock(spec=DataClient)

        component = MyComponent()
        component.setup_clients(
            event_client=mock_event,
            resource_client=mock_resource,
            data_client=mock_data,
        )

        # All required clients should be set
        assert component.event_client == mock_event
        assert component.resource_client == mock_resource
        assert component.data_client == mock_data


class TestPropertyAccessors:
    """Test that property accessors exist and work."""

    def test_all_client_properties_exist(self):
        """Test that all client properties are defined."""

        class MyComponent(MadsciClientMixin):
            pass

        # All client properties should exist as properties
        assert hasattr(MyComponent, "event_client")
        assert hasattr(MyComponent, "resource_client")
        assert hasattr(MyComponent, "data_client")
        assert hasattr(MyComponent, "experiment_client")
        assert hasattr(MyComponent, "workcell_client")
        assert hasattr(MyComponent, "location_client")
        assert hasattr(MyComponent, "lab_client")

        # They should be property objects
        assert isinstance(MyComponent.event_client, property)
        assert isinstance(MyComponent.resource_client, property)
