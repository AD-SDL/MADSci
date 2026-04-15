"""Unit tests for ExperimentClient."""

from unittest.mock import Mock, patch

import httpx
import pytest
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
    response.is_success = True
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

    @patch("madsci.client.experiment_client.create_httpx_client")
    def test_get_experiment_success(self, mock_create_session, experiment):
        """Test successful get_experiment call."""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = experiment.model_dump()

        mock_session = Mock()
        mock_session.request.return_value = mock_response
        mock_create_session.return_value = mock_session

        client = ExperimentClient(experiment_server_url="http://localhost:8002")
        result = client.get_experiment(experiment.experiment_id)

        mock_session.request.assert_called_once_with(
            "GET",
            f"http://localhost:8002/experiment/{experiment.experiment_id}",
            timeout=10.0,
        )
        assert isinstance(result, Experiment)
        assert result.run_name == experiment.run_name
        assert result.status == experiment.status

    @patch("madsci.client.experiment_client.create_httpx_client")
    def test_get_experiment_with_ulid(self, mock_create_session, experiment):
        """Test get_experiment with ULID object."""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = experiment.model_dump()

        mock_session = Mock()
        mock_session.request.return_value = mock_response
        mock_create_session.return_value = mock_session

        client = ExperimentClient(experiment_server_url="http://localhost:8002")
        ulid_obj = ULID.from_str(experiment.experiment_id)
        result = client.get_experiment(ulid_obj)

        mock_session.request.assert_called_once_with(
            "GET", f"http://localhost:8002/experiment/{ulid_obj}", timeout=10.0
        )
        assert isinstance(result, Experiment)

    @patch("madsci.client.experiment_client.create_httpx_client")
    def test_get_experiment_http_error(self, mock_create_session):
        """Test get_experiment with HTTP error."""
        mock_response = Mock()
        mock_response.is_success = False
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404 Not Found",
            request=httpx.Request("GET", "http://test"),
            response=httpx.Response(404),
        )

        mock_session = Mock()
        mock_session.request.return_value = mock_response
        mock_create_session.return_value = mock_session

        client = ExperimentClient(experiment_server_url="http://localhost:8002")

        with pytest.raises(httpx.HTTPStatusError):
            client.get_experiment("nonexistent_id")


class TestExperimentClientGetExperiments:
    """Test ExperimentClient get_experiments method."""

    @patch("madsci.client.experiment_client.create_httpx_client")
    def test_get_experiments_success(self, mock_create_session, experiment):
        """Test successful get_experiments call."""
        mock_response = Mock()
        mock_response.is_success = True
        experiments_data = [experiment.model_dump(), experiment.model_dump()]
        mock_response.json.return_value = experiments_data

        mock_session = Mock()
        mock_session.request.return_value = mock_response
        mock_create_session.return_value = mock_session

        client = ExperimentClient(experiment_server_url="http://localhost:8002")
        result = client.get_experiments(number=5)

        mock_session.request.assert_called_once_with(
            "GET",
            "http://localhost:8002/experiments",
            params={"number": 5},
            timeout=10.0,
        )
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(exp, Experiment) for exp in result)

    @patch("madsci.client.experiment_client.create_httpx_client")
    def test_get_experiments_default_number(self, mock_create_session, experiment):
        """Test get_experiments with default number parameter."""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = [experiment.model_dump()]

        mock_session = Mock()
        mock_session.request.return_value = mock_response
        mock_create_session.return_value = mock_session

        client = ExperimentClient(experiment_server_url="http://localhost:8002")
        result = client.get_experiments()

        mock_session.request.assert_called_once_with(
            "GET",
            "http://localhost:8002/experiments",
            params={"number": 10},
            timeout=10.0,
        )
        assert isinstance(result, list)
        assert len(result) == 1

    @patch("madsci.client.experiment_client.create_httpx_client")
    def test_get_experiments_http_error(self, mock_create_session):
        """Test get_experiments with HTTP error."""
        mock_response = Mock()
        mock_response.is_success = False
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500 Server Error",
            request=httpx.Request("GET", "http://test"),
            response=httpx.Response(500),
        )

        mock_session = Mock()
        mock_session.request.return_value = mock_response
        mock_create_session.return_value = mock_session

        client = ExperimentClient(experiment_server_url="http://localhost:8002")

        with pytest.raises(httpx.HTTPStatusError):
            client.get_experiments()


class TestExperimentClientStartExperiment:
    """Test ExperimentClient start_experiment method."""

    @patch("madsci.client.experiment_client.create_httpx_client")
    def test_start_experiment_success(
        self, mock_create_session, experiment_design, experiment
    ):
        """Test successful start_experiment call."""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = experiment.model_dump()

        mock_session = Mock()
        mock_session.request.return_value = mock_response
        mock_create_session.return_value = mock_session

        client = ExperimentClient(experiment_server_url="http://localhost:8002")
        result = client.start_experiment(
            experiment_design, "Test Run", "Test Description"
        )

        # Verify the request was made correctly
        mock_session.request.assert_called_once()
        call_args = mock_session.request.call_args
        assert call_args[0][0] == "POST"
        assert call_args[0][1] == "http://localhost:8002/experiment"

        # Check the JSON payload
        json_data = call_args[1]["json"]
        assert "experiment_design" in json_data
        assert json_data["run_name"] == "Test Run"
        assert json_data["run_description"] == "Test Description"
        assert call_args[1]["timeout"] == 10.0

        # Check return value
        assert isinstance(result, Experiment)
        assert result.run_name == experiment.run_name

    @patch("madsci.client.experiment_client.create_httpx_client")
    def test_start_experiment_minimal(
        self, mock_create_session, experiment_design, experiment
    ):
        """Test start_experiment with minimal parameters."""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = experiment.model_dump()

        mock_session = Mock()
        mock_session.request.return_value = mock_response
        mock_create_session.return_value = mock_session

        client = ExperimentClient(experiment_server_url="http://localhost:8002")
        result = client.start_experiment(experiment_design)

        mock_session.request.assert_called_once()
        call_args = mock_session.request.call_args
        json_data = call_args[1]["json"]
        assert json_data["run_name"] is None
        assert json_data["run_description"] is None
        assert isinstance(result, Experiment)

    @patch("madsci.client.experiment_client.create_httpx_client")
    def test_start_experiment_http_error(self, mock_create_session, experiment_design):
        """Test start_experiment with HTTP error."""
        mock_response = Mock()
        mock_response.is_success = False
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "400 Bad Request",
            request=httpx.Request("GET", "http://test"),
            response=httpx.Response(400),
        )

        mock_session = Mock()
        mock_session.request.return_value = mock_response
        mock_create_session.return_value = mock_session

        client = ExperimentClient(experiment_server_url="http://localhost:8002")

        with pytest.raises(httpx.HTTPStatusError):
            client.start_experiment(experiment_design)


class TestExperimentClientLifecycleMethods:
    """Test ExperimentClient lifecycle methods (end, continue, pause, cancel)."""

    @patch("madsci.client.experiment_client.create_httpx_client")
    def test_end_experiment_success(self, mock_create_session, experiment):
        """Test successful end_experiment call."""
        mock_response = Mock()
        mock_response.is_success = True
        ended_experiment = experiment.model_copy()
        ended_experiment.status = ExperimentStatus.COMPLETED
        mock_response.json.return_value = ended_experiment.model_dump()

        mock_session = Mock()
        mock_session.request.return_value = mock_response
        mock_create_session.return_value = mock_session

        client = ExperimentClient(experiment_server_url="http://localhost:8002")
        result = client.end_experiment(
            experiment.experiment_id, ExperimentStatus.COMPLETED
        )

        mock_session.request.assert_called_once_with(
            "POST",
            f"http://localhost:8002/experiment/{experiment.experiment_id}/end",
            params={"status": ExperimentStatus.COMPLETED},
            timeout=10.0,
        )
        assert isinstance(result, Experiment)
        assert result.status == ExperimentStatus.COMPLETED

    @patch("madsci.client.experiment_client.create_httpx_client")
    def test_end_experiment_without_status(self, mock_create_session, experiment):
        """Test end_experiment without status parameter."""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = experiment.model_dump()

        mock_session = Mock()
        mock_session.request.return_value = mock_response
        mock_create_session.return_value = mock_session

        client = ExperimentClient(experiment_server_url="http://localhost:8002")
        result = client.end_experiment(experiment.experiment_id)

        mock_session.request.assert_called_once_with(
            "POST",
            f"http://localhost:8002/experiment/{experiment.experiment_id}/end",
            params={"status": None},
            timeout=10.0,
        )
        assert isinstance(result, Experiment)

    @patch("madsci.client.experiment_client.create_httpx_client")
    def test_continue_experiment_success(self, mock_create_session, experiment):
        """Test successful continue_experiment call."""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = experiment.model_dump()

        mock_session = Mock()
        mock_session.request.return_value = mock_response
        mock_create_session.return_value = mock_session

        client = ExperimentClient(experiment_server_url="http://localhost:8002")
        result = client.continue_experiment(experiment.experiment_id)

        mock_session.request.assert_called_once_with(
            "POST",
            f"http://localhost:8002/experiment/{experiment.experiment_id}/continue",
            timeout=10.0,
        )
        assert isinstance(result, Experiment)

    @patch("madsci.client.experiment_client.create_httpx_client")
    def test_pause_experiment_success(self, mock_create_session, experiment):
        """Test successful pause_experiment call."""
        mock_response = Mock()
        mock_response.is_success = True
        paused_experiment = experiment.model_copy()
        paused_experiment.status = ExperimentStatus.PAUSED
        mock_response.json.return_value = paused_experiment.model_dump()

        mock_session = Mock()
        mock_session.request.return_value = mock_response
        mock_create_session.return_value = mock_session

        client = ExperimentClient(experiment_server_url="http://localhost:8002")
        result = client.pause_experiment(experiment.experiment_id)

        mock_session.request.assert_called_once_with(
            "POST",
            f"http://localhost:8002/experiment/{experiment.experiment_id}/pause",
            timeout=10.0,
        )
        assert isinstance(result, Experiment)
        assert result.status == ExperimentStatus.PAUSED

    @patch("madsci.client.experiment_client.create_httpx_client")
    def test_cancel_experiment_success(self, mock_create_session, experiment):
        """Test successful cancel_experiment call."""
        mock_response = Mock()
        mock_response.is_success = True
        cancelled_experiment = experiment.model_copy()
        cancelled_experiment.status = ExperimentStatus.CANCELLED
        mock_response.json.return_value = cancelled_experiment.model_dump()

        mock_session = Mock()
        mock_session.request.return_value = mock_response
        mock_create_session.return_value = mock_session

        client = ExperimentClient(experiment_server_url="http://localhost:8002")
        result = client.cancel_experiment(experiment.experiment_id)

        mock_session.request.assert_called_once_with(
            "POST",
            f"http://localhost:8002/experiment/{experiment.experiment_id}/cancel",
            timeout=10.0,
        )
        assert isinstance(result, Experiment)
        assert result.status == ExperimentStatus.CANCELLED

    @patch("madsci.client.experiment_client.create_httpx_client")
    def test_lifecycle_methods_with_ulid(self, mock_create_session, experiment):
        """Test lifecycle methods work with ULID objects."""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = experiment.model_dump()

        mock_session = Mock()
        mock_session.request.return_value = mock_response
        mock_create_session.return_value = mock_session

        client = ExperimentClient(experiment_server_url="http://localhost:8002")
        ulid_obj = ULID.from_str(experiment.experiment_id)

        # Test with pause_experiment as representative
        result = client.pause_experiment(ulid_obj)

        mock_session.request.assert_called_once_with(
            "POST",
            f"http://localhost:8002/experiment/{ulid_obj}/pause",
            timeout=10.0,
        )
        assert isinstance(result, Experiment)

    @patch("madsci.client.experiment_client.create_httpx_client")
    def test_lifecycle_methods_http_error(self, mock_create_session, experiment):
        """Test lifecycle methods with HTTP error."""
        mock_response = Mock()
        mock_response.is_success = False
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404 Not Found",
            request=httpx.Request("GET", "http://test"),
            response=httpx.Response(404),
        )

        mock_session = Mock()
        mock_session.request.return_value = mock_response
        mock_create_session.return_value = mock_session

        client = ExperimentClient(experiment_server_url="http://localhost:8002")

        with pytest.raises(httpx.HTTPStatusError):
            client.end_experiment(experiment.experiment_id)

        with pytest.raises(httpx.HTTPStatusError):
            client.continue_experiment(experiment.experiment_id)

        with pytest.raises(httpx.HTTPStatusError):
            client.pause_experiment(experiment.experiment_id)

        with pytest.raises(httpx.HTTPStatusError):
            client.cancel_experiment(experiment.experiment_id)


class TestExperimentClientCampaignMethods:
    """Test ExperimentClient campaign methods."""

    @patch("madsci.client.experiment_client.create_httpx_client")
    def test_register_campaign_success(self, mock_create_session, campaign):
        """Test successful register_campaign call."""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = campaign.model_dump()

        mock_session = Mock()
        mock_session.request.return_value = mock_response
        mock_create_session.return_value = mock_session

        client = ExperimentClient(experiment_server_url="http://localhost:8002")
        result = client.register_campaign(campaign)

        mock_session.request.assert_called_once_with(
            "POST",
            "http://localhost:8002/campaign",
            json=campaign.model_dump(mode="json"),
            timeout=10.0,
        )
        assert isinstance(result, ExperimentalCampaign)
        assert result.campaign_id == campaign.campaign_id

    @patch("madsci.client.experiment_client.create_httpx_client")
    def test_register_campaign_http_error(self, mock_create_session, campaign):
        """Test register_campaign with HTTP error."""
        mock_response = Mock()
        mock_response.is_success = False
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "400 Bad Request",
            request=httpx.Request("GET", "http://test"),
            response=httpx.Response(400),
        )

        mock_session = Mock()
        mock_session.request.return_value = mock_response
        mock_create_session.return_value = mock_session

        client = ExperimentClient(experiment_server_url="http://localhost:8002")

        with pytest.raises(httpx.HTTPStatusError):
            client.register_campaign(campaign)

    @patch("madsci.client.experiment_client.create_httpx_client")
    def test_get_campaign_success(self, mock_create_session, campaign):
        """Test successful get_campaign call."""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = campaign.model_dump()

        mock_session = Mock()
        mock_session.request.return_value = mock_response
        mock_create_session.return_value = mock_session

        client = ExperimentClient(experiment_server_url="http://localhost:8002")
        result = client.get_campaign(campaign.campaign_id)

        mock_session.request.assert_called_once_with(
            "GET",
            f"http://localhost:8002/campaign/{campaign.campaign_id}",
            timeout=10.0,
        )
        assert isinstance(result, ExperimentalCampaign)
        assert result.campaign_id == campaign.campaign_id

    @patch("madsci.client.experiment_client.create_httpx_client")
    def test_get_campaign_http_error(self, mock_create_session):
        """Test get_campaign with HTTP error."""
        mock_response = Mock()
        mock_response.is_success = False
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404 Not Found",
            request=httpx.Request("GET", "http://test"),
            response=httpx.Response(404),
        )

        mock_session = Mock()
        mock_session.request.return_value = mock_response
        mock_create_session.return_value = mock_session

        client = ExperimentClient(experiment_server_url="http://localhost:8002")

        with pytest.raises(httpx.HTTPStatusError):
            client.get_campaign("nonexistent_campaign_id")
