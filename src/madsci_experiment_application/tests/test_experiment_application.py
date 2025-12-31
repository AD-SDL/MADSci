"""Unit tests for ExperimentApplication class."""

from contextlib import contextmanager
from typing import Any
from unittest.mock import Mock, patch

import pytest
from madsci.common.exceptions import ExperimentCancelledError, ExperimentFailedError
from madsci.common.types.condition_types import (
    NoResourceInLocationCondition,
    ResourceChildFieldCheckCondition,
    ResourceFieldCheckCondition,
    ResourceInLocationCondition,
)
from madsci.common.types.experiment_types import (
    Experiment,
    ExperimentDesign,
    ExperimentStatus,
)
from madsci.common.types.location_types import Location
from madsci.common.types.node_types import NodeDefinition
from madsci.common.types.resource_types import Resource
from madsci.common.utils import new_ulid_str
from madsci.experiment_application import (
    ExperimentApplication,
    ExperimentApplicationConfig,
)
from pydantic import AnyUrl


@contextmanager
def mock_all_clients():
    """Context manager to mock all MADSci clients at the module level."""
    with (
        patch("madsci.client.event_client.EventClient") as mock_event_client,
        patch(
            "madsci.client.experiment_client.ExperimentClient"
        ) as mock_experiment_client,
        patch("madsci.client.workcell_client.WorkcellClient") as mock_workcell_client,
        patch("madsci.client.location_client.LocationClient") as mock_location_client,
        patch("madsci.client.resource_client.ResourceClient") as mock_resource_client,
        patch("madsci.client.data_client.DataClient") as mock_data_client,
    ):
        # Set up mock instances
        mock_event_client.return_value = Mock()
        mock_experiment_client.return_value = Mock()
        mock_workcell_client.return_value = Mock()
        mock_location_client.return_value = Mock()
        mock_resource_client.return_value = Mock()
        mock_data_client.return_value = Mock()

        yield


class TestExperimentApplication(ExperimentApplication):
    """Test subclass of ExperimentApplication."""

    config = ExperimentApplicationConfig(
        update_node_files=False,
    )

    experiment_design = ExperimentDesign(
        experiment_name="Test_Experiment",
        resource_conditions=[],
    )

    def run_experiment(self, *args: Any, **kwargs: Any) -> str:
        """Test experiment implementation."""
        return "test_result"


@pytest.fixture
def mock_experiment() -> Experiment:
    """Create a mock experiment object."""
    return Experiment(
        experiment_id=new_ulid_str(),
        run_name="test_run",
        experiment_design=ExperimentDesign(
            experiment_name="Test_Experiment",
            resource_conditions=[],
        ),
        status=ExperimentStatus.IN_PROGRESS,
    )


@pytest.fixture
def mock_resource() -> Resource:
    """Create a mock resource object."""
    return Resource(
        resource_id=new_ulid_str(),
        resource_name="test_resource",
        resource_class="test_class",
        children={
            "slot1": Resource(
                resource_id=new_ulid_str(),
                resource_name="child_resource",
                resource_class="child_class",
            )
        },
        field_value=10,
    )


@pytest.fixture
def mock_location() -> Location:
    """Create a mock location object."""
    return Location(
        location_id=new_ulid_str(),
        location_name="test_location",
        resource_id=new_ulid_str(),
    )


@pytest.fixture
def experiment_design() -> ExperimentDesign:
    """Create a test experiment design."""
    return ExperimentDesign(
        experiment_name="Test_Experiment",
        resource_conditions=[
            ResourceInLocationCondition(
                condition_name="test_condition",
                location_name="test_location",
                key="slot1",
                resource_class="test_class",
            )
        ],
    )


@pytest.fixture
def app_config() -> ExperimentApplicationConfig:
    """Create a test application config."""
    return ExperimentApplicationConfig(
        node_url=AnyUrl("http://localhost:6000"),
        server_mode=False,
        run_args=[1, 2],
        run_kwargs={"test_param": "value"},
        update_node_files=False,
    )


@pytest.fixture
def node_definition() -> NodeDefinition:
    """Create a test node definition."""
    return NodeDefinition(
        node_name="test_experiment_app",
        module_name="test_experiment_application",
        description="Test experiment application node",
    )


@pytest.fixture
def experiment_app(
    node_definition: NodeDefinition,
    app_config: ExperimentApplicationConfig,
    experiment_design: ExperimentDesign,
) -> TestExperimentApplication:
    """Create a test ExperimentApplication instance."""
    with mock_all_clients():
        app = TestExperimentApplication(
            node_definition=node_definition,
            node_config=app_config,
            experiment_design=experiment_design,
        )

        # Mock the clients
        app.event_client = Mock()
        app.logger = app.event_client
        app.experiment_client = Mock()
        app.workcell_client = Mock()
        app.location_client = Mock()
        app.resource_client = Mock()
        app.data_client = Mock()

        return app


@pytest.fixture
def experiment_app_with_mocks(
    experiment_app: TestExperimentApplication,
    mock_experiment: Experiment,
    mock_location: Location,
    mock_resource: Resource,
) -> TestExperimentApplication:
    """Create an ExperimentApplication with pre-configured mocks."""
    experiment_app.experiment = mock_experiment
    experiment_app.experiment_client.start_experiment.return_value = mock_experiment
    experiment_app.experiment_client.end_experiment.return_value = mock_experiment
    experiment_app.experiment_client.pause_experiment.return_value = mock_experiment
    experiment_app.experiment_client.cancel_experiment.return_value = mock_experiment
    experiment_app.experiment_client.get_experiment.return_value = mock_experiment
    experiment_app.experiment_client.continue_experiment.return_value = mock_experiment
    experiment_app.location_client.get_locations.return_value = [mock_location]
    experiment_app.location_client.get_location.return_value = mock_location
    experiment_app.resource_client.get_resource.return_value = mock_resource
    return experiment_app


class TestExperimentApplicationInit:
    """Test ExperimentApplication initialization."""

    def test_client_attributes_are_not_shadowed_by_type_annotations(
        self,
    ) -> None:
        """Test that type annotations don't shadow MadsciClientMixin properties (issue #205)."""

        # Check that ExperimentApplication class attributes don't shadow the mixin properties
        # If they do, accessing these attributes will return the class itself, not trigger the property
        assert "experiment_client" not in ExperimentApplication.__dict__, (
            "experiment_client should not be a class attribute - it should be inherited as a property from MadsciClientMixin"
        )
        assert "workcell_client" not in ExperimentApplication.__dict__, (
            "workcell_client should not be a class attribute - it should be inherited as a property from MadsciClientMixin"
        )

        # Verify that the attributes resolve to properties (inherited from the mixin or base classes)
        experiment_client_attr = getattr(
            ExperimentApplication, "experiment_client", None
        )
        workcell_client_attr = getattr(ExperimentApplication, "workcell_client", None)

        assert isinstance(
            experiment_client_attr,
            property,
        ), "experiment_client should be a property (possibly inherited)"
        assert isinstance(
            workcell_client_attr,
            property,
        ), "workcell_client should be a property (possibly inherited)"

    def test_all_client_properties_accessible_on_instances(
        self, experiment_app: TestExperimentApplication
    ) -> None:
        """Test that all client properties are accessible on instances (issue #205).

        This is an integration test that verifies the fix for issue #205 where
        ExperimentApplication instances were getting AttributeError when accessing
        experiment_client and workcell_client.
        """
        # Test that all clients are accessible and return instances (not classes)
        clients_to_test = [
            ("event_client", "info"),
            ("experiment_client", "start_experiment"),
            ("workcell_client", "submit_workflow"),
            ("resource_client", "get_resource"),
            ("data_client", "save_datapoint"),
            ("location_client", "get_location"),
        ]

        for client_name, expected_method in clients_to_test:
            # Should have the attribute
            assert hasattr(experiment_app, client_name), (
                f"App should have {client_name} attribute"
            )

            # Accessing should work without AttributeError
            client = getattr(experiment_app, client_name)

            # Should be an instance, not a class
            assert not isinstance(client, type), (
                f"{client_name} should be an instance, not a class"
            )

            # Should have expected methods (validates it's the right type)
            assert hasattr(client, expected_method), (
                f"{client_name} should have {expected_method} method"
            )

    def test_init_basic(self, node_definition: NodeDefinition) -> None:
        """Test basic initialization."""
        with mock_all_clients():
            app = TestExperimentApplication(node_definition=node_definition)

            assert app.experiment is None
            assert app.experiment_design is not None
            assert app.experiment_design.experiment_name == "Test_Experiment"
            assert app.logger is not None
            assert app.event_client is not None

    def test_init_with_experiment_design_dict(
        self, node_definition: NodeDefinition, experiment_design: ExperimentDesign
    ) -> None:
        """Test initialization with experiment design."""
        with mock_all_clients():
            app = TestExperimentApplication(
                node_definition=node_definition,
                experiment_design=experiment_design,
            )

            assert app.experiment_design == experiment_design

    def test_init_with_experiment_design_yaml_path(
        self, node_definition: NodeDefinition, tmp_path: Any
    ) -> None:
        """Test initialization with YAML file path."""
        # Create a temporary YAML file
        yaml_content = """
experiment_name: "Test_From_YAML"
resource_conditions: []
        """
        yaml_file = tmp_path / "test_experiment.yaml"
        yaml_file.write_text(yaml_content.strip())

        with (
            mock_all_clients(),
            patch(
                "madsci.common.types.experiment_types.ExperimentDesign.from_yaml"
            ) as mock_from_yaml,
        ):
            mock_design = ExperimentDesign(experiment_name="Test_From_YAML")
            mock_from_yaml.return_value = mock_design

            app = TestExperimentApplication(
                node_definition=node_definition,
                experiment_design=str(yaml_file),
            )

            mock_from_yaml.assert_called_once()
            assert app.experiment_design == mock_design

    def test_init_with_existing_experiment(
        self, node_definition: NodeDefinition, mock_experiment: Experiment
    ) -> None:
        """Test initialization with existing experiment."""
        with mock_all_clients():
            app = TestExperimentApplication(
                node_definition=node_definition,
                experiment=mock_experiment,
            )

            assert app.experiment == mock_experiment

    def test_config_initialization(self) -> None:
        """Test ExperimentApplicationConfig initialization."""
        config = ExperimentApplicationConfig(
            server_mode=True,
            run_args=[1, 2, 3],
            run_kwargs={"param1": "value1", "param2": "value2"},
            update_node_files=False,
        )

        assert config.server_mode is True
        assert config.run_args == [1, 2, 3]
        assert config.run_kwargs == {"param1": "value1", "param2": "value2"}

    def test_config_defaults(self) -> None:
        """Test ExperimentApplicationConfig default values."""
        config = ExperimentApplicationConfig(update_node_files=False)

        assert config.server_mode is False
        assert config.run_args == []
        assert config.run_kwargs == {}


class TestExperimentLifecycle:
    """Test experiment lifecycle methods."""

    @patch("builtins.input", return_value="n")
    @patch("builtins.print")
    def test_start_experiment_run(
        self,
        mock_print: Any,
        mock_input: Any,
        experiment_app_with_mocks: TestExperimentApplication,
    ) -> None:
        """Test starting an experiment run."""
        experiment_app_with_mocks.start_experiment_run(
            run_name="test_run", run_description="test description"
        )

        experiment_app_with_mocks.experiment_client.start_experiment.assert_called_once_with(
            experiment_design=experiment_app_with_mocks.experiment_design,
            run_name="test_run",
            run_description="test description",
        )
        experiment_app_with_mocks.logger.info.assert_called()

    def test_end_experiment(
        self, experiment_app_with_mocks: TestExperimentApplication
    ) -> None:
        """Test ending an experiment."""
        experiment_app_with_mocks.end_experiment(status=ExperimentStatus.COMPLETED)

        experiment_app_with_mocks.experiment_client.end_experiment.assert_called_once_with(
            experiment_id=experiment_app_with_mocks.experiment.experiment_id,
            status=ExperimentStatus.COMPLETED,
        )
        experiment_app_with_mocks.logger.info.assert_called()

    def test_end_experiment_default_status(
        self, experiment_app_with_mocks: TestExperimentApplication
    ) -> None:
        """Test ending an experiment with default status."""
        experiment_app_with_mocks.end_experiment()

        experiment_app_with_mocks.experiment_client.end_experiment.assert_called_once_with(
            experiment_id=experiment_app_with_mocks.experiment.experiment_id,
            status=None,
        )

    def test_pause_experiment(
        self, experiment_app_with_mocks: TestExperimentApplication
    ) -> None:
        """Test pausing an experiment."""
        experiment_app_with_mocks.pause_experiment()

        experiment_app_with_mocks.experiment_client.pause_experiment.assert_called_once_with(
            experiment_id=experiment_app_with_mocks.experiment.experiment_id
        )
        experiment_app_with_mocks.logger.info.assert_called()

    def test_cancel_experiment(
        self, experiment_app_with_mocks: TestExperimentApplication
    ) -> None:
        """Test cancelling an experiment."""
        experiment_app_with_mocks.cancel_experiment()

        experiment_app_with_mocks.experiment_client.cancel_experiment.assert_called_once_with(
            experiment_id=experiment_app_with_mocks.experiment.experiment_id
        )
        experiment_app_with_mocks.logger.info.assert_called()

    def test_fail_experiment(
        self, experiment_app_with_mocks: TestExperimentApplication
    ) -> None:
        """Test failing an experiment."""
        experiment_app_with_mocks.fail_experiment()

        experiment_app_with_mocks.experiment_client.end_experiment.assert_called_once_with(
            experiment_id=experiment_app_with_mocks.experiment.experiment_id,
            status=ExperimentStatus.FAILED,
        )
        experiment_app_with_mocks.logger.info.assert_called()

    def test_handle_exception(
        self, experiment_app_with_mocks: TestExperimentApplication
    ) -> None:
        """Test exception handling."""
        test_exception = ValueError("Test error")

        experiment_app_with_mocks.handle_exception(test_exception)

        experiment_app_with_mocks.logger.info.assert_called()
        experiment_app_with_mocks.experiment_client.end_experiment.assert_called_once_with(
            experiment_id=experiment_app_with_mocks.experiment.experiment_id,
            status=ExperimentStatus.FAILED,
        )

    def test_check_experiment_status_running(
        self, experiment_app_with_mocks: TestExperimentApplication
    ) -> None:
        """Test checking experiment status when running."""
        experiment_app_with_mocks.experiment.status = ExperimentStatus.IN_PROGRESS

        experiment_app_with_mocks.check_experiment_status()

        experiment_app_with_mocks.experiment_client.get_experiment.assert_called_once()

    def test_check_experiment_status_cancelled(
        self, experiment_app_with_mocks: TestExperimentApplication
    ) -> None:
        """Test checking experiment status when cancelled."""
        cancelled_experiment = experiment_app_with_mocks.experiment.model_copy()
        cancelled_experiment.status = ExperimentStatus.CANCELLED
        experiment_app_with_mocks.experiment_client.get_experiment.return_value = (
            cancelled_experiment
        )

        with pytest.raises(ExperimentCancelledError):
            experiment_app_with_mocks.check_experiment_status()

        experiment_app_with_mocks.logger.error.assert_called()

    def test_check_experiment_status_failed(
        self, experiment_app_with_mocks: TestExperimentApplication
    ) -> None:
        """Test checking experiment status when failed."""
        failed_experiment = experiment_app_with_mocks.experiment.model_copy()
        failed_experiment.status = ExperimentStatus.FAILED
        experiment_app_with_mocks.experiment_client.get_experiment.return_value = (
            failed_experiment
        )

        with pytest.raises(ExperimentFailedError):
            experiment_app_with_mocks.check_experiment_status()

        experiment_app_with_mocks.logger.error.assert_called()

    @patch("time.sleep")
    def test_check_experiment_status_paused_then_resumed(
        self, mock_sleep: Any, experiment_app_with_mocks: TestExperimentApplication
    ) -> None:
        """Test checking experiment status when paused then resumed."""
        paused_experiment = experiment_app_with_mocks.experiment.model_copy()
        paused_experiment.status = ExperimentStatus.PAUSED

        running_experiment = experiment_app_with_mocks.experiment.model_copy()
        running_experiment.status = ExperimentStatus.IN_PROGRESS

        experiment_app_with_mocks.experiment_client.get_experiment.side_effect = [
            paused_experiment,  # First call - paused
            paused_experiment,  # Second call - still paused
            running_experiment,  # Third call - running
        ]

        experiment_app_with_mocks.check_experiment_status()

        assert (
            experiment_app_with_mocks.experiment_client.get_experiment.call_count == 3
        )
        experiment_app_with_mocks.logger.warning.assert_called()
        mock_sleep.assert_called_with(5)


class TestConditionEvaluation:
    """Test condition evaluation methods."""

    def test_get_resource_from_condition_by_id(
        self,
        experiment_app_with_mocks: TestExperimentApplication,
        mock_resource: Resource,
    ) -> None:
        """Test getting resource from condition by resource_id."""
        condition = ResourceFieldCheckCondition(
            condition_name="test_condition",
            resource_id=mock_resource.resource_id,
            field="field_value",
            operator="is_equal_to",
            target_value=10,
        )
        experiment_app_with_mocks.resource_client.get_resource.return_value = (
            mock_resource
        )

        result = experiment_app_with_mocks.get_resource_from_condition(condition)

        assert result == mock_resource
        experiment_app_with_mocks.resource_client.get_resource.assert_called_once_with(
            mock_resource.resource_id
        )

    def test_get_resource_from_condition_by_name(
        self,
        experiment_app_with_mocks: TestExperimentApplication,
        mock_resource: Resource,
    ) -> None:
        """Test getting resource from condition by resource_name."""
        condition = ResourceFieldCheckCondition(
            condition_name="test_condition",
            resource_name=mock_resource.resource_name,
            field="field_value",
            operator="is_equal_to",
            target_value=10,
        )
        experiment_app_with_mocks.resource_client.query_resource.return_value = (
            mock_resource
        )

        result = experiment_app_with_mocks.get_resource_from_condition(condition)

        assert result == mock_resource
        experiment_app_with_mocks.resource_client.query_resource.assert_called_once_with(
            resource_name=mock_resource.resource_name, multiple=False
        )

    def test_get_resource_from_condition_invalid(
        self, experiment_app_with_mocks: TestExperimentApplication
    ) -> None:
        """Test getting resource from condition with invalid identifier."""
        condition = ResourceFieldCheckCondition(
            condition_name="test_condition",
            field="field_value",
            operator="is_equal_to",
            target_value=10,
        )
        experiment_app_with_mocks.resource_client.get_resource.return_value = None
        experiment_app_with_mocks.resource_client.query_resource.return_value = None

        with pytest.raises(Exception, match="Invalid Identifier for Resource"):
            experiment_app_with_mocks.get_resource_from_condition(condition)

    def test_check_resource_field_greater_than(
        self,
        experiment_app_with_mocks: TestExperimentApplication,
        mock_resource: Resource,
    ) -> None:
        """Test checking resource field with greater_than operator."""
        condition = ResourceFieldCheckCondition(
            condition_name="test_condition",
            field="field_value",
            operator="is_greater_than",
            target_value=5,
        )
        mock_resource.field_value = 10

        result = experiment_app_with_mocks.check_resource_field(
            mock_resource, condition
        )

        assert result is True

    def test_check_resource_field_less_than(
        self,
        experiment_app_with_mocks: TestExperimentApplication,
        mock_resource: Resource,
    ) -> None:
        """Test checking resource field with less_than operator."""
        condition = ResourceFieldCheckCondition(
            condition_name="test_condition",
            field="field_value",
            operator="is_less_than",
            target_value=15,
        )
        mock_resource.field_value = 10

        result = experiment_app_with_mocks.check_resource_field(
            mock_resource, condition
        )

        assert result is True

    def test_check_resource_field_equal_to(
        self,
        experiment_app_with_mocks: TestExperimentApplication,
        mock_resource: Resource,
    ) -> None:
        """Test checking resource field with equal_to operator."""
        condition = ResourceFieldCheckCondition(
            condition_name="test_condition",
            field="field_value",
            operator="is_equal_to",
            target_value=10,
        )
        mock_resource.field_value = 10

        result = experiment_app_with_mocks.check_resource_field(
            mock_resource, condition
        )

        assert result is True

    def test_check_resource_field_greater_than_or_equal(
        self,
        experiment_app_with_mocks: TestExperimentApplication,
        mock_resource: Resource,
    ) -> None:
        """Test checking resource field with greater_than_or_equal_to operator."""
        condition = ResourceFieldCheckCondition(
            condition_name="test_condition",
            field="field_value",
            operator="is_greater_than_or_equal_to",
            target_value=10,
        )
        mock_resource.field_value = 10

        result = experiment_app_with_mocks.check_resource_field(
            mock_resource, condition
        )

        assert result is True

    def test_check_resource_field_less_than_or_equal(
        self,
        experiment_app_with_mocks: TestExperimentApplication,
        mock_resource: Resource,
    ) -> None:
        """Test checking resource field with less_than_or_equal_to operator."""
        condition = ResourceFieldCheckCondition(
            condition_name="test_condition",
            field="field_value",
            operator="is_less_than_or_equal_to",
            target_value=10,
        )
        mock_resource.field_value = 10

        result = experiment_app_with_mocks.check_resource_field(
            mock_resource, condition
        )

        assert result is True

    def test_check_resource_field_invalid_operator(
        self,
        experiment_app_with_mocks: TestExperimentApplication,
        mock_resource: Resource,
    ) -> None:
        """Test checking resource field with invalid operator."""
        condition = ResourceFieldCheckCondition(
            condition_name="test_condition",
            field="field_value",
            operator="is_equal_to",  # Use valid operator first
            target_value=10,
        )
        # Test invalid operator case by bypassing Pydantic validation
        object.__setattr__(condition, "operator", "invalid_operator")

        result = experiment_app_with_mocks.check_resource_field(
            mock_resource, condition
        )

        assert result is False

    def test_get_location_from_condition_by_name(
        self,
        experiment_app_with_mocks: TestExperimentApplication,
        mock_location: Location,
    ) -> None:
        """Test getting location from condition by location_name."""
        condition = ResourceInLocationCondition(
            condition_name="test_condition",
            location_name=mock_location.location_name,
        )
        experiment_app_with_mocks.location_client.get_locations.return_value = [
            mock_location
        ]

        result = experiment_app_with_mocks.get_location_from_condition(condition)

        assert result == mock_location

    def test_get_location_from_condition_by_id(
        self,
        experiment_app_with_mocks: TestExperimentApplication,
        mock_location: Location,
    ) -> None:
        """Test getting location from condition by location_id."""
        condition = ResourceInLocationCondition(
            condition_name="test_condition",
            location_id=mock_location.location_id,
        )
        experiment_app_with_mocks.location_client.get_location.return_value = (
            mock_location
        )

        result = experiment_app_with_mocks.get_location_from_condition(condition)

        assert result == mock_location
        experiment_app_with_mocks.location_client.get_location.assert_called_once_with(
            mock_location.location_id
        )

    def test_get_location_from_condition_invalid(
        self, experiment_app_with_mocks: TestExperimentApplication
    ) -> None:
        """Test getting location from condition with invalid identifier."""
        condition = ResourceInLocationCondition(
            condition_name="test_condition",
        )
        experiment_app_with_mocks.location_client.get_locations.return_value = []
        experiment_app_with_mocks.location_client.get_location.return_value = None

        with pytest.raises(Exception, match="Invalid Identifier for Location"):
            experiment_app_with_mocks.get_location_from_condition(condition)

    def test_resource_at_key_dict_children(
        self,
        experiment_app_with_mocks: TestExperimentApplication,
        mock_resource: Resource,
    ) -> None:
        """Test resource_at_key with dict children."""
        condition = ResourceInLocationCondition(
            condition_name="test_condition",
            key="slot1",
            resource_class="child_class",
        )

        result = experiment_app_with_mocks.resource_at_key(mock_resource, condition)

        assert result is True

    def test_resource_at_key_list_children(
        self, experiment_app_with_mocks: TestExperimentApplication
    ) -> None:
        """Test resource_at_key with list children."""
        list_resource = Resource(
            resource_id=new_ulid_str(),
            resource_name="list_resource",
            resource_class="list_class",
            children=[
                Resource(
                    resource_id=new_ulid_str(),
                    resource_name="child_0",
                    resource_class="child_class",
                ),
                Resource(
                    resource_id=new_ulid_str(),
                    resource_name="child_1",
                    resource_class="other_class",
                ),
            ],
        )
        condition = ResourceInLocationCondition(
            condition_name="test_condition",
            key="0",
            resource_class="child_class",
        )

        result = experiment_app_with_mocks.resource_at_key(list_resource, condition)

        assert result is True

    def test_resource_at_key_not_found(
        self,
        experiment_app_with_mocks: TestExperimentApplication,
        mock_resource: Resource,
    ) -> None:
        """Test resource_at_key when key not found."""
        condition = ResourceInLocationCondition(
            condition_name="test_condition",
            key="nonexistent_key",
        )

        result = experiment_app_with_mocks.resource_at_key(mock_resource, condition)

        assert result is False


class TestExperimentManagement:
    """Test experiment management and context manager."""

    def test_manage_experiment_success(
        self, experiment_app_with_mocks: TestExperimentApplication
    ) -> None:
        """Test manage_experiment context manager with successful execution."""
        with (
            patch("builtins.input", return_value="n"),
            patch("builtins.print"),
            experiment_app_with_mocks.manage_experiment(
                run_name="test_run", run_description="test description"
            ),
        ):
            pass  # Simulate successful experiment execution

        experiment_app_with_mocks.experiment_client.start_experiment.assert_called_once()
        experiment_app_with_mocks.experiment_client.end_experiment.assert_called_once_with(
            experiment_id=experiment_app_with_mocks.experiment.experiment_id,
            status=None,
        )

    def test_manage_experiment_with_exception(
        self, experiment_app_with_mocks: TestExperimentApplication
    ) -> None:
        """Test manage_experiment context manager with exception."""
        test_exception = ValueError("Test error")

        with (
            patch("builtins.input", return_value="n"),
            patch("builtins.print"),
            pytest.raises(ValueError),
            experiment_app_with_mocks.manage_experiment(),
        ):
            raise test_exception

        experiment_app_with_mocks.experiment_client.start_experiment.assert_called_once()
        experiment_app_with_mocks.experiment_client.end_experiment.assert_called_once_with(
            experiment_id=experiment_app_with_mocks.experiment.experiment_id,
            status=ExperimentStatus.FAILED,
        )

    def test_add_experiment_management_decorator(
        self, experiment_app_with_mocks: TestExperimentApplication
    ) -> None:
        """Test add_experiment_management decorator."""

        def test_function(param1: str, param2: str = "default") -> str:
            return f"{param1}_{param2}"

        test_function = experiment_app_with_mocks.add_experiment_management(
            test_function
        )

        with patch("builtins.input", return_value="n"), patch("builtins.print"):
            result = test_function("test", param2="value")

        assert result == "test_value"
        experiment_app_with_mocks.experiment_client.start_experiment.assert_called_once()
        experiment_app_with_mocks.experiment_client.end_experiment.assert_called_once()

    def test_add_experiment_management_decorator_with_exception(
        self, experiment_app_with_mocks: TestExperimentApplication
    ) -> None:
        """Test add_experiment_management decorator with exception."""

        def test_function() -> None:
            raise ValueError("Test error")

        test_function = experiment_app_with_mocks.add_experiment_management(
            test_function
        )

        with (
            patch("builtins.input", return_value="n"),
            patch("builtins.print"),
            pytest.raises(ValueError),
        ):
            test_function()

        experiment_app_with_mocks.experiment_client.start_experiment.assert_called_once()
        experiment_app_with_mocks.experiment_client.end_experiment.assert_called_once_with(
            experiment_id=experiment_app_with_mocks.experiment.experiment_id,
            status=ExperimentStatus.FAILED,
        )


class TestClassMethods:
    """Test ExperimentApplication class methods."""

    def test_start_new(self, experiment_design: ExperimentDesign) -> None:
        """Test start_new class method."""

        # Mock the experiment client to return a mock experiment
        mock_experiment_client = Mock()
        mock_experiment = Mock()
        mock_experiment_client.start_experiment.return_value = mock_experiment

        mock_location = Location(
            location_id=new_ulid_str(),
            location_name="test_location",
            resource_id=new_ulid_str(),
        )
        mock_resource = Resource(
            resource_id=new_ulid_str(),
            resource_name="test_resource",
            resource_class="test_class",
            children={
                "slot1": Resource(
                    resource_id=new_ulid_str(),
                    resource_name="child_resource",
                    resource_class="child_class",
                )
            },
            field_value=10,
        )

        with (
            patch("madsci.client.client_mixin.EventClient") as mock_event_client_class,
            patch(
                "madsci.client.client_mixin.ExperimentClient"
            ) as mock_experiment_client_class,
            patch(
                "madsci.client.client_mixin.WorkcellClient"
            ) as mock_workcell_client_class,
            patch(
                "madsci.client.client_mixin.LocationClient"
            ) as mock_location_client_class,
            patch(
                "madsci.client.client_mixin.ResourceClient"
            ) as mock_resource_client_class,
            patch("madsci.client.client_mixin.DataClient") as mock_data_client_class,
            patch("builtins.input", return_value="n"),
            patch("builtins.print"),
        ):
            # Set up client class mocks to return configured instances
            mock_experiment_client_class.return_value = mock_experiment_client
            mock_workcell_client_class.return_value = Mock()
            mock_location_client_class.return_value = Mock()
            mock_location_client_class.return_value.get_locations.return_value = [
                mock_location
            ]
            mock_resource_client_class.return_value = Mock()
            mock_resource_client_class.return_value.get_resource.return_value = (
                mock_resource
            )
            mock_event_client_class.return_value = Mock()
            mock_data_client_class.return_value = Mock()

            app = TestExperimentApplication.start_new(
                experiment_design=experiment_design,
            )

        # Verify the experiment client was instantiated with the correct URL
        mock_experiment_client_class.assert_called_once_with()

        # Verify the experiment was started and the app has the right state
        assert app.experiment == mock_experiment
        mock_experiment_client.start_experiment.assert_called_once()

    def test_continue_experiment(self, mock_experiment: Experiment) -> None:
        """Test continue_experiment class method."""

        # Mock the experiment client
        mock_experiment_client = Mock()

        with (
            patch("madsci.client.client_mixin.EventClient") as mock_event_client_class,
            patch(
                "madsci.client.client_mixin.ExperimentClient"
            ) as mock_experiment_client_class,
            patch(
                "madsci.client.client_mixin.WorkcellClient"
            ) as mock_workcell_client_class,
            patch(
                "madsci.client.client_mixin.LocationClient"
            ) as mock_location_client_class,
            patch(
                "madsci.client.client_mixin.ResourceClient"
            ) as mock_resource_client_class,
            patch("madsci.client.client_mixin.DataClient") as mock_data_client_class,
        ):
            # Set up client class mocks to return configured instances
            mock_experiment_client_class.return_value = mock_experiment_client
            mock_workcell_client_class.return_value = Mock()
            mock_location_client_class.return_value = Mock()
            mock_resource_client_class.return_value = Mock()
            mock_event_client_class.return_value = Mock()
            mock_data_client_class.return_value = Mock()

            app = TestExperimentApplication.continue_experiment(
                experiment=mock_experiment,
            )

        # Verify the experiment client was instantiated with the correct URL
        mock_experiment_client_class.assert_called_once_with()

        # Verify the experiment was continued and the app has the right state
        assert app.experiment == mock_experiment
        mock_experiment_client.continue_experiment.assert_called_once_with(
            experiment_id=mock_experiment.experiment_id
        )


class TestServerModeAndStartup:
    """Test server mode and application startup."""

    def test_start_app_server_mode(
        self, experiment_app: TestExperimentApplication
    ) -> None:
        """Test start_app in server mode."""
        experiment_app.config.server_mode = True

        with (
            patch.object(experiment_app, "start_node") as mock_start_node,
            patch.object(experiment_app, "_add_action") as mock_add_action,
        ):
            experiment_app.start_app()

        mock_add_action.assert_called_once()
        mock_start_node.assert_called_once()

        # Verify the action was added correctly
        call_args = mock_add_action.call_args
        assert call_args[0][1] == "run_experiment"  # action name
        assert call_args[0][2] == "Run the Experiment"  # description
        assert call_args[1]["blocking"] is False

    def test_start_app_single_run_mode(
        self, experiment_app: TestExperimentApplication
    ) -> None:
        """Test start_app in single run mode."""
        experiment_app.config.server_mode = False
        experiment_app.config.run_args = [1, 2, 3]
        experiment_app.config.run_kwargs = {"param": "value"}

        with patch.object(experiment_app, "run_experiment") as mock_run_experiment:
            experiment_app.start_app()

        mock_run_experiment.assert_called_once_with(1, 2, 3, param="value")

    def test_run_experiment_default_implementation(
        self, experiment_app: TestExperimentApplication
    ) -> None:
        """Test default run_experiment implementation."""
        result = experiment_app.run_experiment("test_arg")
        assert result == "test_result"

    def test_loop_not_implemented(
        self, experiment_app: TestExperimentApplication
    ) -> None:
        """Test that loop method raises NotImplementedError."""
        # Note: The loop method is decorated with @threaded_daemon, so we need to
        # test the underlying function
        with pytest.raises(NotImplementedError):
            experiment_app.loop.__wrapped__(
                experiment_app
            )  # Access the wrapped function


class TestConditionEvaluationIntegration:
    """Test full condition evaluation integration."""

    def test_evaluate_condition_resource_present(
        self,
        experiment_app_with_mocks: TestExperimentApplication,
        mock_location: Location,
        mock_resource: Resource,
    ) -> None:
        """Test evaluate_condition for resource_present."""
        condition = ResourceInLocationCondition(
            condition_name="test_condition",
            location_name="test_location",
            key="slot1",
            resource_class="child_class",
        )

        experiment_app_with_mocks.location_client.get_locations.return_value = [
            mock_location
        ]
        experiment_app_with_mocks.resource_client.get_resource.return_value = (
            mock_resource
        )

        result = experiment_app_with_mocks.evaluate_condition(condition)

        assert result is True
        experiment_app_with_mocks.location_client.get_locations.assert_called_once()
        experiment_app_with_mocks.resource_client.get_resource.assert_called_once_with(
            mock_location.resource_id
        )

    def test_evaluate_condition_no_resource_present(
        self,
        experiment_app_with_mocks: TestExperimentApplication,
        mock_location: Location,
        mock_resource: Resource,
    ) -> None:
        """Test evaluate_condition for no_resource_present."""
        condition = NoResourceInLocationCondition(
            condition_name="test_condition",
            location_name="test_location",
            key="nonexistent_slot",
        )

        experiment_app_with_mocks.location_client.get_locations.return_value = [
            mock_location
        ]
        experiment_app_with_mocks.resource_client.get_resource.return_value = (
            mock_resource
        )

        result = experiment_app_with_mocks.evaluate_condition(condition)

        assert (
            result is True
        )  # Should return True because resource is NOT present at the key

    def test_evaluate_condition_resource_field_check(
        self,
        experiment_app_with_mocks: TestExperimentApplication,
        mock_resource: Resource,
    ) -> None:
        """Test evaluate_condition for resource_field_check."""
        condition = ResourceFieldCheckCondition(
            condition_name="test_condition",
            resource_id=mock_resource.resource_id,
            field="field_value",
            operator="is_greater_than",
            target_value=5,
        )
        mock_resource.field_value = 10

        experiment_app_with_mocks.resource_client.get_resource.return_value = (
            mock_resource
        )

        result = experiment_app_with_mocks.evaluate_condition(condition)

        assert result is True

    def test_evaluate_condition_resource_child_field_check_dict(
        self,
        experiment_app_with_mocks: TestExperimentApplication,
        mock_resource: Resource,
    ) -> None:
        """Test evaluate_condition for resource_child_field_check with dict children."""
        condition = ResourceChildFieldCheckCondition(
            condition_name="test_condition",
            resource_id=mock_resource.resource_id,
            key="slot1",
            field="field_value",
            operator="is_equal_to",
            target_value=10,
        )

        # Set up the child resource with the field
        mock_resource.children["slot1"].field_value = 10
        experiment_app_with_mocks.resource_client.get_resource.return_value = (
            mock_resource
        )

        result = experiment_app_with_mocks.evaluate_condition(condition)

        assert result is True

    def test_evaluate_condition_resource_child_field_check_list(
        self, experiment_app_with_mocks: TestExperimentApplication
    ) -> None:
        """Test evaluate_condition for resource_child_field_check with list children."""
        list_resource = Resource(
            resource_id=new_ulid_str(),
            resource_name="list_resource",
            resource_class="list_class",
            field_value=0,
            children=[
                Resource(
                    resource_id=new_ulid_str(),
                    resource_name="child_0",
                    resource_class="child_class",
                    field_value=15,
                )
            ],
        )
        condition = ResourceChildFieldCheckCondition(
            condition_name="test_condition",
            resource_id=list_resource.resource_id,
            key="0",
            field="field_value",
            operator="is_greater_than",
            target_value=10,
        )
        experiment_app_with_mocks.resource_client.get_resource.return_value = (
            list_resource
        )
        assert getattr(list_resource.children[0], "field_value", None) == 15
        result = experiment_app_with_mocks.evaluate_condition(condition)
        assert result is True

    def test_evaluate_condition_invalid_type(
        self, experiment_app_with_mocks: TestExperimentApplication
    ) -> None:
        """Test evaluate_condition with invalid condition type."""
        # Create a valid condition first, then change the type
        condition = ResourceFieldCheckCondition(
            condition_name="test_condition",
            field="field_value",
            operator="is_equal_to",
            target_value=10,
        )
        # Manually set an invalid condition_type after creation
        object.__setattr__(condition, "condition_type", "invalid_type")

        result = experiment_app_with_mocks.evaluate_condition(condition)

        assert result is False
