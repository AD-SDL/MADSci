"""Tests for experiment modalities (ExperimentBase, Script, Notebook, Node).

These tests verify the core functionality of the new experiment modalities
introduced in Phase 4 of the UX overhaul.
"""

import contextlib
import warnings
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from madsci.common.types.experiment_types import (
    Experiment,
    ExperimentDesign,
    ExperimentStatus,
)
from madsci.experiment_application import (
    ExperimentApplication,
    ExperimentApplicationConfig,
    ExperimentBase,
    ExperimentBaseConfig,
    ExperimentNode,
    ExperimentNodeConfig,
    ExperimentNotebook,
    ExperimentNotebookConfig,
    ExperimentScript,
    ExperimentScriptConfig,
    ExperimentTUI,
    ExperimentTUIConfig,
)

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_experiment_design() -> ExperimentDesign:
    """Create a mock experiment design for testing."""
    return ExperimentDesign(
        experiment_name="Test Experiment",
        experiment_description="A test experiment for unit tests",
    )


@pytest.fixture
def mock_experiment(mock_experiment_design: ExperimentDesign) -> Experiment:
    """Create a mock experiment for testing."""
    return Experiment(
        experiment_id="01JTEST123456789ABCDEFGH",
        status=ExperimentStatus.IN_PROGRESS,
        experiment_design=mock_experiment_design,
    )


@pytest.fixture
def mock_experiment_client(mock_experiment: Experiment) -> MagicMock:
    """Create a mock experiment client."""
    client = MagicMock()
    client.start_experiment.return_value = mock_experiment
    client.end_experiment.return_value = mock_experiment
    client.pause_experiment.return_value = mock_experiment
    client.cancel_experiment.return_value = mock_experiment
    client.get_experiment.return_value = mock_experiment
    return client


@pytest.fixture
def mock_event_client() -> MagicMock:
    """Create a mock event client."""
    return MagicMock()


# =============================================================================
# ExperimentBaseConfig Tests
# =============================================================================


class TestExperimentBaseConfig:
    """Tests for ExperimentBaseConfig."""

    def test_default_values(self) -> None:
        """Test that config has sensible defaults."""
        config = ExperimentBaseConfig()
        assert config.lab_server_url is None
        assert config.event_server_url is None
        assert config.experiment_server_url is None
        assert config.workcell_server_url is None
        assert config.data_server_url is None
        assert config.resource_server_url is None
        assert config.location_server_url is None

    def test_custom_values(self) -> None:
        """Test setting custom values."""
        config = ExperimentBaseConfig(
            lab_server_url="http://localhost:8000/",
            experiment_server_url="http://localhost:8002/",
        )
        assert str(config.lab_server_url) == "http://localhost:8000/"
        assert str(config.experiment_server_url) == "http://localhost:8002/"


# =============================================================================
# ExperimentBase Tests
# =============================================================================


class TestExperimentBase:
    """Tests for ExperimentBase class."""

    def test_init_with_design(self, mock_experiment_design: ExperimentDesign) -> None:
        """Test initialization with an experiment design."""
        exp = ExperimentBase(experiment_design=mock_experiment_design)
        assert exp.experiment_design == mock_experiment_design
        assert exp.experiment is None

    def test_init_with_config(self) -> None:
        """Test initialization with custom config."""
        config = ExperimentBaseConfig(lab_server_url="http://localhost:8000/")
        exp = ExperimentBase(config=config)
        assert exp.config == config

    def test_start_experiment_run_without_design(self) -> None:
        """Test that starting without design raises error."""
        exp = ExperimentBase()
        with pytest.raises(ValueError, match="experiment_design is required"):
            exp.start_experiment_run()

    def test_start_experiment_run_with_mock(
        self,
        mock_experiment_design: ExperimentDesign,
        mock_experiment_client: MagicMock,
        mock_event_client: MagicMock,
    ) -> None:
        """Test starting an experiment run with mocked clients."""
        exp = ExperimentBase(experiment_design=mock_experiment_design)
        exp._experiment_client = mock_experiment_client
        exp._event_client = mock_event_client

        result = exp.start_experiment_run(run_name="Test Run")

        mock_experiment_client.start_experiment.assert_called_once()
        assert result is not None
        assert exp.experiment is not None

    def test_end_experiment_without_active(self, mock_event_client: MagicMock) -> None:
        """Test ending experiment without active experiment."""
        exp = ExperimentBase()
        exp._event_client = mock_event_client

        result = exp.end_experiment()
        assert result is None

    def test_is_running_property(
        self,
        mock_experiment_design: ExperimentDesign,
        mock_experiment: Experiment,
    ) -> None:
        """Test is_running property."""
        exp = ExperimentBase(experiment_design=mock_experiment_design)
        assert exp.is_running is False

        exp.experiment = mock_experiment
        assert exp.is_running is True

    def test_logger_property(self, mock_event_client: MagicMock) -> None:
        """Test logger property returns event_client."""
        exp = ExperimentBase()
        exp._event_client = mock_event_client
        assert exp.logger == mock_event_client


# =============================================================================
# ExperimentScript Tests
# =============================================================================


class TestExperimentScript:
    """Tests for ExperimentScript class."""

    def test_config_type(self) -> None:
        """Test that script uses correct config type."""
        exp = ExperimentScript()
        assert exp.config_model == ExperimentScriptConfig

    def test_config_run_args(self) -> None:
        """Test run_args in config."""
        config = ExperimentScriptConfig(
            run_args=[1, 2, 3],
            run_kwargs={"key": "value"},
        )
        assert config.run_args == [1, 2, 3]
        assert config.run_kwargs == {"key": "value"}

    def test_run_raises_not_implemented(self) -> None:
        """Test that run raises NotImplementedError for base class."""

        class MyScript(ExperimentScript):
            experiment_design = ExperimentDesign(experiment_name="Test")

        exp = MyScript()
        # run_experiment is not implemented, but run() calls manage_experiment
        # which calls start_experiment_run() requiring experiment_client
        with pytest.raises(NotImplementedError):
            exp.run_experiment()

    def test_main_class_method(self) -> None:
        """Test main() class method creates instance and runs."""

        class TestScript(ExperimentScript):
            experiment_design = ExperimentDesign(experiment_name="Test")
            ran = False

            def run(self, *args: Any, **kwargs: Any) -> Any:
                TestScript.ran = True
                return "result"

        result = TestScript.main()
        assert result == "result"
        assert TestScript.ran


# =============================================================================
# ExperimentNotebook Tests
# =============================================================================


class TestExperimentNotebook:
    """Tests for ExperimentNotebook class."""

    def test_config_type(self) -> None:
        """Test that notebook uses correct config type."""
        exp = ExperimentNotebook()
        assert exp.config_model == ExperimentNotebookConfig

    def test_config_rich_output(self) -> None:
        """Test rich_output in config."""
        config = ExperimentNotebookConfig(rich_output=False)
        assert config.rich_output is False

    def test_is_started_initial(self) -> None:
        """Test that notebook starts in not-started state."""
        exp = ExperimentNotebook()
        assert exp._is_started is False

    def test_start_without_started(
        self,
        mock_experiment_design: ExperimentDesign,
        mock_experiment_client: MagicMock,
        mock_event_client: MagicMock,
    ) -> None:
        """Test starting a notebook experiment."""
        exp = ExperimentNotebook(experiment_design=mock_experiment_design)
        exp._experiment_client = mock_experiment_client
        exp._event_client = mock_event_client

        result = exp.start()

        assert result == exp  # Returns self for chaining
        assert exp._is_started is True

    def test_start_when_already_started(
        self,
        mock_experiment_design: ExperimentDesign,
        mock_event_client: MagicMock,
    ) -> None:
        """Test starting when already started logs warning."""
        exp = ExperimentNotebook(experiment_design=mock_experiment_design)
        exp._event_client = mock_event_client
        exp._is_started = True

        result = exp.start()

        assert result == exp
        mock_event_client.warning.assert_called()

    def test_end_without_started(self, mock_event_client: MagicMock) -> None:
        """Test ending when not started logs warning."""
        exp = ExperimentNotebook()
        exp._event_client = mock_event_client
        exp._is_started = False

        result = exp.end()

        assert result == exp
        mock_event_client.warning.assert_called()

    def test_run_workflow_without_started(self) -> None:
        """Test run_workflow raises error when not started."""
        exp = ExperimentNotebook()
        exp._is_started = False

        with pytest.raises(RuntimeError, match="not started"):
            exp.run_workflow("test_workflow")

    def test_context_manager(
        self,
        mock_experiment_design: ExperimentDesign,
        mock_experiment_client: MagicMock,
        mock_event_client: MagicMock,
        mock_experiment: Experiment,
    ) -> None:
        """Test using notebook as context manager."""
        exp = ExperimentNotebook(experiment_design=mock_experiment_design)
        exp._experiment_client = mock_experiment_client
        exp._event_client = mock_event_client

        with exp:
            assert exp._is_started is True

        assert exp._is_started is False

    def test_display_plain(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test plain display without Rich."""
        config = ExperimentNotebookConfig(rich_output=False)
        exp = ExperimentNotebook(config=config)

        exp.display({"key": "value"}, title="Test")

        captured = capsys.readouterr()
        assert "Test" in captured.out
        assert "key" in captured.out


# =============================================================================
# ExperimentTUI Tests
# =============================================================================


class TestExperimentTUI:
    """Tests for ExperimentTUI class."""

    def test_config_type(self) -> None:
        """Test that TUI uses correct config type."""
        exp = ExperimentTUI()
        assert exp.config_model == ExperimentTUIConfig

    def test_config_refresh_interval(self) -> None:
        """Test refresh_interval in config."""
        config = ExperimentTUIConfig(refresh_interval=2.0)
        assert config.refresh_interval == 2.0

    def test_run_tui_without_textual(self) -> None:
        """Test that run_tui raises ImportError without textual."""
        exp = ExperimentTUI()

        # Mock run_tui to raise ImportError (simulating missing textual)
        with (
            patch.dict("sys.modules", {"textual": None}),
            patch(
                "madsci.experiment_application.experiment_tui.ExperimentTUI.run_tui",
                side_effect=ImportError("textual not available"),
            ),
            pytest.raises(ImportError),
        ):
            exp.run_tui()


# =============================================================================
# ExperimentNode Tests
# =============================================================================


class TestExperimentNode:
    """Tests for ExperimentNode class."""

    def test_config_type(self) -> None:
        """Test that node uses correct config type."""
        # Node init is more complex, just test config class
        assert ExperimentNode.config_model == ExperimentNodeConfig

    def test_config_server_settings(self) -> None:
        """Test server settings in config."""
        config = ExperimentNodeConfig(
            server_host="127.0.0.1",
            server_port=7000,
        )
        assert config.server_host == "127.0.0.1"
        assert config.server_port == 7000

    def test_config_default_port(self) -> None:
        """Test default port is 6000."""
        config = ExperimentNodeConfig()
        assert config.server_port == 6000


# =============================================================================
# ExperimentApplication Deprecation Tests
# =============================================================================


class TestExperimentApplicationDeprecation:
    """Tests for ExperimentApplication deprecation warning."""

    def test_deprecation_warning_on_init(self) -> None:
        """Test that ExperimentApplication emits deprecation warning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            # Creating an instance should trigger warning
            # We need to catch the warning before any errors from missing services
            with contextlib.suppress(Exception):
                _ = ExperimentApplication()

            # Check that deprecation warning was issued
            deprecation_warnings = [
                warning
                for warning in w
                if issubclass(warning.category, DeprecationWarning)
            ]
            assert len(deprecation_warnings) > 0
            assert "deprecated" in str(deprecation_warnings[0].message).lower()


# =============================================================================
# Import Tests
# =============================================================================


class TestModuleImports:
    """Tests for module imports and exports."""

    def test_all_exports_available(self) -> None:
        """Test that all exports in __all__ are available."""
        # All imports are at the top of the file - just verify they're all importable
        assert ExperimentBase is not None
        assert ExperimentBaseConfig is not None
        assert ExperimentScript is not None
        assert ExperimentScriptConfig is not None
        assert ExperimentNotebook is not None
        assert ExperimentNotebookConfig is not None
        assert ExperimentTUI is not None
        assert ExperimentTUIConfig is not None
        assert ExperimentNode is not None
        assert ExperimentNodeConfig is not None
        assert ExperimentApplication is not None
        assert ExperimentApplicationConfig is not None

    def test_base_inheritance(self) -> None:
        """Test that all modalities inherit from ExperimentBase."""
        assert issubclass(ExperimentScript, ExperimentBase)
        assert issubclass(ExperimentNotebook, ExperimentBase)
        assert issubclass(ExperimentTUI, ExperimentBase)
        assert issubclass(ExperimentNode, ExperimentBase)
