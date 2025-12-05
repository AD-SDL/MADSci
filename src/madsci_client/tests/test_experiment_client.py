"""Unit tests for ExperimentClient."""

from unittest.mock import Mock, patch

import pytest
import requests
from madsci.client.experiment_client import ExperimentClient
from madsci.common.types.experiment_types import (
    Experiment,
    ExperimentalCampaign,
    ExperimentDesign,
    ExperimentStatus,
)
from madsci.common.utils import new_ulid_str
from ulid import ULID


@pytest.fixture
def mock_session():
    """Create a mock session object."""
    return Mock()


@pytest.fixture
def mock_response():
    """Create a mock response object."""
    response = Mock()
    response.ok = True
    response.status_code = 200
    return response


@pytest.fixture
def experiment_design():
    """Create a sample ExperimentDesign for testing."""
    return ExperimentDesign(
        experiment_name="Test Experiment",
        experiment_description="A test experiment description",
    )


@pytest.fixture
def experiment():
    """Create a sample Experiment for testing."""
    return Experiment(
        experiment_id=new_ulid_str(),
        status=ExperimentStatus.IN_PROGRESS,
        run_name="Test Experiment",
        run_description="Test description",
    )


@pytest.fixture
def campaign():
    """Create a sample ExperimentalCampaign for testing."""
    return ExperimentalCampaign(
        campaign_id=new_ulid_str(),
        campaign_name="Test Campaign",
        campaign_description="Test campaign description",
        experiment_ids=[],
    )


class TestExperimentClientInit:
    """Test ExperimentClient initialization."""

    def test_init_with_url(self):
        """Test initialization with server URL."""
        client = ExperimentClient(experiment_server_url="http://localhost:8002")
        assert str(client.experiment_server_url) == "http://localhost:8002/"

    def test_init_without_url_raises_error(self):
        """Test initialization without server URL raises ValueError."""
        with patch(
            "madsci.client.experiment_client.get_current_madsci_context"
        ) as mock_context:
            mock_context.return_value.experiment_server_url = None
            with pytest.raises(ValueError, match="No experiment server URL provided"):
                ExperimentClient()


class TestExperimentClientGetExperiment:
    """Test ExperimentClient get_experiment method."""

    @patch("madsci.client.experiment_client.create_http_session")
    def test_get_experiment_success(self, mock_create_session, experiment):
        """Test successful get_experiment call."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = experiment.model_dump()

        mock_session = Mock()
        mock_session.get.return_value = mock_response
        mock_create_session.return_value = mock_session

        client = ExperimentClient(experiment_server_url="http://localhost:8002")
        result = client.get_experiment(experiment.experiment_id)

        mock_session.get.assert_called_once_with(
            f"http://localhost:8002/experiment/{experiment.experiment_id}", timeout=10.0
        )
        assert isinstance(result, Experiment)
        assert result.run_name == experiment.run_name
        assert result.status == experiment.status

    @patch("madsci.client.experiment_client.create_http_session")
    def test_get_experiment_with_ulid(self, mock_create_session, experiment):
        """Test get_experiment with ULID object."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = experiment.model_dump()

        mock_session = Mock()
        mock_session.get.return_value = mock_response
        mock_create_session.return_value = mock_session

        client = ExperimentClient(experiment_server_url="http://localhost:8002")
        ulid_obj = ULID.from_str(experiment.experiment_id)
        result = client.get_experiment(ulid_obj)

        mock_session.get.assert_called_once_with(
            f"http://localhost:8002/experiment/{ulid_obj}", timeout=10.0
        )
        assert isinstance(result, Experiment)

    @patch("madsci.client.experiment_client.create_http_session")
    def test_get_experiment_http_error(self, mock_create_session):
        """Test get_experiment with HTTP error."""
        mock_response = Mock()
        mock_response.ok = False
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")

        mock_session = Mock()
        mock_session.get.return_value = mock_response
        mock_create_session.return_value = mock_session

        client = ExperimentClient(experiment_server_url="http://localhost:8002")

        with pytest.raises(requests.HTTPError):
            client.get_experiment("nonexistent_id")


class TestExperimentClientGetExperiments:
    """Test ExperimentClient get_experiments method."""

    @patch("madsci.client.experiment_client.create_http_session")
    def test_get_experiments_success(self, mock_create_session, experiment):
        """Test successful get_experiments call."""
        mock_response = Mock()
        mock_response.ok = True
        experiments_data = [experiment.model_dump(), experiment.model_dump()]
        mock_response.json.return_value = experiments_data

        mock_session = Mock()
        mock_session.get.return_value = mock_response
        mock_create_session.return_value = mock_session

        client = ExperimentClient(experiment_server_url="http://localhost:8002")
        result = client.get_experiments(number=5)

        mock_session.get.assert_called_once_with(
            "http://localhost:8002/experiments",
            params={"number": 5},
            timeout=10.0,
        )
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(exp, Experiment) for exp in result)

    @patch("madsci.client.experiment_client.create_http_session")
    def test_get_experiments_default_number(self, mock_create_session, experiment):
        """Test get_experiments with default number parameter."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = [experiment.model_dump()]

        mock_session = Mock()
        mock_session.get.return_value = mock_response
        mock_create_session.return_value = mock_session

        client = ExperimentClient(experiment_server_url="http://localhost:8002")
        result = client.get_experiments()

        mock_session.get.assert_called_once_with(
            "http://localhost:8002/experiments",
            params={"number": 10},
            timeout=10.0,
        )
        assert isinstance(result, list)
        assert len(result) == 1

    @patch("madsci.client.experiment_client.create_http_session")
    def test_get_experiments_http_error(self, mock_create_session):
        """Test get_experiments with HTTP error."""
        mock_response = Mock()
        mock_response.ok = False
        mock_response.raise_for_status.side_effect = requests.HTTPError(
            "500 Server Error"
        )

        mock_session = Mock()
        mock_session.get.return_value = mock_response
        mock_create_session.return_value = mock_session

        client = ExperimentClient(experiment_server_url="http://localhost:8002")

        with pytest.raises(requests.HTTPError):
            client.get_experiments()


class TestExperimentClientStartExperiment:
    """Test ExperimentClient start_experiment method."""

    @patch("madsci.client.experiment_client.create_http_session")
    def test_start_experiment_success(
        self, mock_create_session, experiment_design, experiment
    ):
        """Test successful start_experiment call."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = experiment.model_dump()

        mock_session = Mock()
        mock_session.post.return_value = mock_response
        mock_create_session.return_value = mock_session

        client = ExperimentClient(experiment_server_url="http://localhost:8002")
        result = client.start_experiment(
            experiment_design, "Test Run", "Test Description"
        )

        # Verify the request was made correctly
        mock_session.post.assert_called_once()
        call_args = mock_session.post.call_args
        assert call_args[0][0] == "http://localhost:8002/experiment"

        # Check the JSON payload
        json_data = call_args[1]["json"]
        assert "experiment_design" in json_data
        assert json_data["run_name"] == "Test Run"
        assert json_data["run_description"] == "Test Description"
        assert call_args[1]["timeout"] == 10.0

        # Check return value
        assert isinstance(result, Experiment)
        assert result.run_name == experiment.run_name

    @patch("madsci.client.experiment_client.create_http_session")
    def test_start_experiment_minimal(
        self, mock_create_session, experiment_design, experiment
    ):
        """Test start_experiment with minimal parameters."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = experiment.model_dump()

        mock_session = Mock()
        mock_session.post.return_value = mock_response
        mock_create_session.return_value = mock_session

        client = ExperimentClient(experiment_server_url="http://localhost:8002")
        result = client.start_experiment(experiment_design)

        mock_session.post.assert_called_once()
        call_args = mock_session.post.call_args
        json_data = call_args[1]["json"]
        assert json_data["run_name"] is None
        assert json_data["run_description"] is None
        assert isinstance(result, Experiment)

    @patch("madsci.client.experiment_client.create_http_session")
    def test_start_experiment_http_error(self, mock_create_session, experiment_design):
        """Test start_experiment with HTTP error."""
        mock_response = Mock()
        mock_response.ok = False
        mock_response.raise_for_status.side_effect = requests.HTTPError(
            "400 Bad Request"
        )

        mock_session = Mock()
        mock_session.post.return_value = mock_response
        mock_create_session.return_value = mock_session

        client = ExperimentClient(experiment_server_url="http://localhost:8002")

        with pytest.raises(requests.HTTPError):
            client.start_experiment(experiment_design)


class TestExperimentClientLifecycleMethods:
    """Test ExperimentClient lifecycle methods (end, continue, pause, cancel)."""

    @patch("madsci.client.experiment_client.create_http_session")
    def test_end_experiment_success(self, mock_create_session, experiment):
        """Test successful end_experiment call."""
        mock_response = Mock()
        mock_response.ok = True
        ended_experiment = experiment.model_copy()
        ended_experiment.status = ExperimentStatus.COMPLETED
        mock_response.json.return_value = ended_experiment.model_dump()

        mock_session = Mock()
        mock_session.post.return_value = mock_response
        mock_create_session.return_value = mock_session

        client = ExperimentClient(experiment_server_url="http://localhost:8002")
        result = client.end_experiment(
            experiment.experiment_id, ExperimentStatus.COMPLETED
        )

        mock_session.post.assert_called_once_with(
            f"http://localhost:8002/experiment/{experiment.experiment_id}/end",
            params={"status": ExperimentStatus.COMPLETED},
            timeout=10.0,
        )
        assert isinstance(result, Experiment)
        assert result.status == ExperimentStatus.COMPLETED

    @patch("madsci.client.experiment_client.create_http_session")
    def test_end_experiment_without_status(self, mock_create_session, experiment):
        """Test end_experiment without status parameter."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = experiment.model_dump()

        mock_session = Mock()
        mock_session.post.return_value = mock_response
        mock_create_session.return_value = mock_session

        client = ExperimentClient(experiment_server_url="http://localhost:8002")
        result = client.end_experiment(experiment.experiment_id)

        mock_session.post.assert_called_once_with(
            f"http://localhost:8002/experiment/{experiment.experiment_id}/end",
            params={"status": None},
            timeout=10.0,
        )
        assert isinstance(result, Experiment)

    @patch("madsci.client.experiment_client.create_http_session")
    def test_continue_experiment_success(self, mock_create_session, experiment):
        """Test successful continue_experiment call."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = experiment.model_dump()

        mock_session = Mock()
        mock_session.post.return_value = mock_response
        mock_create_session.return_value = mock_session

        client = ExperimentClient(experiment_server_url="http://localhost:8002")
        result = client.continue_experiment(experiment.experiment_id)

        mock_session.post.assert_called_once_with(
            f"http://localhost:8002/experiment/{experiment.experiment_id}/continue",
            timeout=10.0,
        )
        assert isinstance(result, Experiment)

    @patch("madsci.client.experiment_client.create_http_session")
    def test_pause_experiment_success(self, mock_create_session, experiment):
        """Test successful pause_experiment call."""
        mock_response = Mock()
        mock_response.ok = True
        paused_experiment = experiment.model_copy()
        paused_experiment.status = ExperimentStatus.PAUSED
        mock_response.json.return_value = paused_experiment.model_dump()

        mock_session = Mock()
        mock_session.post.return_value = mock_response
        mock_create_session.return_value = mock_session

        client = ExperimentClient(experiment_server_url="http://localhost:8002")
        result = client.pause_experiment(experiment.experiment_id)

        mock_session.post.assert_called_once_with(
            f"http://localhost:8002/experiment/{experiment.experiment_id}/pause",
            timeout=10.0,
        )
        assert isinstance(result, Experiment)
        assert result.status == ExperimentStatus.PAUSED

    @patch("madsci.client.experiment_client.create_http_session")
    def test_cancel_experiment_success(self, mock_create_session, experiment):
        """Test successful cancel_experiment call."""
        mock_response = Mock()
        mock_response.ok = True
        cancelled_experiment = experiment.model_copy()
        cancelled_experiment.status = ExperimentStatus.CANCELLED
        mock_response.json.return_value = cancelled_experiment.model_dump()

        mock_session = Mock()
        mock_session.post.return_value = mock_response
        mock_create_session.return_value = mock_session

        client = ExperimentClient(experiment_server_url="http://localhost:8002")
        result = client.cancel_experiment(experiment.experiment_id)

        mock_session.post.assert_called_once_with(
            f"http://localhost:8002/experiment/{experiment.experiment_id}/cancel",
            timeout=10.0,
        )
        assert isinstance(result, Experiment)
        assert result.status == ExperimentStatus.CANCELLED

    @patch("madsci.client.experiment_client.create_http_session")
    def test_lifecycle_methods_with_ulid(self, mock_create_session, experiment):
        """Test lifecycle methods work with ULID objects."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = experiment.model_dump()

        mock_session = Mock()
        mock_session.post.return_value = mock_response
        mock_create_session.return_value = mock_session

        client = ExperimentClient(experiment_server_url="http://localhost:8002")
        ulid_obj = ULID.from_str(experiment.experiment_id)

        # Test with pause_experiment as representative
        result = client.pause_experiment(ulid_obj)

        mock_session.post.assert_called_once_with(
            f"http://localhost:8002/experiment/{ulid_obj}/pause",
            timeout=10.0,
        )
        assert isinstance(result, Experiment)

    @patch("madsci.client.experiment_client.create_http_session")
    def test_lifecycle_methods_http_error(self, mock_create_session, experiment):
        """Test lifecycle methods with HTTP error."""
        mock_response = Mock()
        mock_response.ok = False
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")

        mock_session = Mock()
        mock_session.post.return_value = mock_response
        mock_create_session.return_value = mock_session

        client = ExperimentClient(experiment_server_url="http://localhost:8002")

        with pytest.raises(requests.HTTPError):
            client.end_experiment(experiment.experiment_id)

        with pytest.raises(requests.HTTPError):
            client.continue_experiment(experiment.experiment_id)

        with pytest.raises(requests.HTTPError):
            client.pause_experiment(experiment.experiment_id)

        with pytest.raises(requests.HTTPError):
            client.cancel_experiment(experiment.experiment_id)


class TestExperimentClientCampaignMethods:
    """Test ExperimentClient campaign methods."""

    @patch("madsci.client.experiment_client.create_http_session")
    def test_register_campaign_success(self, mock_create_session, campaign):
        """Test successful register_campaign call."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = campaign.model_dump()

        mock_session = Mock()
        mock_session.post.return_value = mock_response
        mock_create_session.return_value = mock_session

        client = ExperimentClient(experiment_server_url="http://localhost:8002")
        result = client.register_campaign(campaign)

        mock_session.post.assert_called_once_with(
            "http://localhost:8002/campaign",
            json=campaign.model_dump(mode="json"),
            timeout=10.0,
        )
        # Note: This method returns response.json() directly, not a validated model
        assert result == campaign.model_dump()

    @patch("madsci.client.experiment_client.create_http_session")
    def test_register_campaign_http_error(self, mock_create_session, campaign):
        """Test register_campaign with HTTP error."""
        mock_response = Mock()
        mock_response.ok = False
        mock_response.raise_for_status.side_effect = requests.HTTPError(
            "400 Bad Request"
        )

        mock_session = Mock()
        mock_session.post.return_value = mock_response
        mock_create_session.return_value = mock_session

        client = ExperimentClient(experiment_server_url="http://localhost:8002")

        with pytest.raises(requests.HTTPError):
            client.register_campaign(campaign)

    @patch("madsci.client.experiment_client.create_http_session")
    def test_get_campaign_success(self, mock_create_session, campaign):
        """Test successful get_campaign call."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = campaign.model_dump()

        mock_session = Mock()
        mock_session.get.return_value = mock_response
        mock_create_session.return_value = mock_session

        client = ExperimentClient(experiment_server_url="http://localhost:8002")
        result = client.get_campaign(campaign.campaign_id)

        mock_session.get.assert_called_once_with(
            f"http://localhost:8002/campaign/{campaign.campaign_id}",
            timeout=10.0,
        )
        # Note: This method returns response.json() directly, not a validated model
        assert result == campaign.model_dump()

    @patch("madsci.client.experiment_client.create_http_session")
    def test_get_campaign_http_error(self, mock_create_session):
        """Test get_campaign with HTTP error."""
        mock_response = Mock()
        mock_response.ok = False
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")

        mock_session = Mock()
        mock_session.get.return_value = mock_response
        mock_create_session.return_value = mock_session

        client = ExperimentClient(experiment_server_url="http://localhost:8002")

        with pytest.raises(requests.HTTPError):
            client.get_campaign("nonexistent_campaign_id")
