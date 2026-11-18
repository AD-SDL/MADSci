"""Unit tests for ExperimentClient."""

from unittest.mock import AsyncMock, Mock, patch

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


# ------------------------------------------------------------------
# Async method tests
# ------------------------------------------------------------------

EXPERIMENT_URL = "http://localhost:8002/"


def _async_response(json_data, status_code: int = 200) -> Mock:
    """Create a mock httpx.Response for the async request path."""
    response = Mock(spec=httpx.Response)
    response.json.return_value = json_data
    response.status_code = status_code
    response.is_success = status_code < 400
    if status_code >= 400:
        response.raise_for_status.side_effect = httpx.HTTPStatusError(
            f"{status_code} Error",
            request=httpx.Request("GET", EXPERIMENT_URL),
            response=httpx.Response(status_code),
        )
    return response


@pytest.fixture
def async_client():
    """ExperimentClient with the async request method replaced by an AsyncMock."""
    client = ExperimentClient(experiment_server_url=EXPERIMENT_URL)
    client._async_request = AsyncMock()
    return client


# (method name, path after the server URL, HTTP method) for the async methods
# that take only an experiment ID and return one Experiment.
EXPERIMENT_ID_METHODS = [
    ("async_get_experiment", "experiment/{id}", "GET"),
    ("async_continue_experiment", "experiment/{id}/continue", "POST"),
    ("async_pause_experiment", "experiment/{id}/pause", "POST"),
    ("async_cancel_experiment", "experiment/{id}/cancel", "POST"),
]


class TestExperimentClientAsyncMethods:
    """Test the async methods of ExperimentClient."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("method_name", "path", "http_method"), EXPERIMENT_ID_METHODS
    )
    async def test_experiment_id_methods(
        self, async_client, experiment, method_name, path, http_method
    ):
        """Each method sends the right request and returns an Experiment."""
        async_client._async_request.return_value = _async_response(
            experiment.model_dump(mode="json")
        )

        result = await getattr(async_client, method_name)(experiment.experiment_id)

        async_client._async_request.assert_awaited_once_with(
            http_method,
            EXPERIMENT_URL + path.format(id=experiment.experiment_id),
            timeout=10.0,
        )
        assert isinstance(result, Experiment)
        assert result.run_name == experiment.run_name

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("method_name", "path", "http_method"), EXPERIMENT_ID_METHODS
    )
    async def test_experiment_id_methods_raise_http_error(
        self, async_client, method_name, path, http_method
    ):
        """Each method raises HTTPStatusError on an error response."""
        async_client._async_request.return_value = _async_response({}, 404)

        with pytest.raises(httpx.HTTPStatusError):
            await getattr(async_client, method_name)(new_ulid_str())

    @pytest.mark.asyncio
    @pytest.mark.parametrize("timeout", [0.0, 3.5])
    async def test_timeout_override(self, async_client, experiment, timeout):
        """An explicit timeout is sent as given, including 0.0."""
        async_client._async_request.return_value = _async_response(
            experiment.model_dump(mode="json")
        )

        await async_client.async_get_experiment(
            experiment.experiment_id, timeout=timeout
        )

        assert async_client._async_request.await_args.kwargs["timeout"] == timeout

    @pytest.mark.asyncio
    async def test_get_experiments(self, async_client, experiment):
        """async_get_experiments sends the number and returns Experiments."""
        async_client._async_request.return_value = _async_response(
            [experiment.model_dump(mode="json")]
        )

        result = await async_client.async_get_experiments(number=5)

        async_client._async_request.assert_awaited_once_with(
            "GET", EXPERIMENT_URL + "experiments", params={"number": 5}, timeout=10.0
        )
        assert len(result) == 1
        assert isinstance(result[0], Experiment)

    @pytest.mark.asyncio
    async def test_start_experiment(self, async_client, experiment_design, experiment):
        """async_start_experiment posts the registration and returns an Experiment."""
        async_client._async_request.return_value = _async_response(
            experiment.model_dump(mode="json")
        )

        result = await async_client.async_start_experiment(
            experiment_design, run_name="Run 1", run_description="First run"
        )

        args = async_client._async_request.await_args
        assert args.args == ("POST", EXPERIMENT_URL + "experiment")
        body = args.kwargs["json"]
        assert body["experiment_design"]["experiment_name"] == "Test Experiment"
        assert body["run_name"] == "Run 1"
        assert body["run_description"] == "First run"
        assert args.kwargs["timeout"] == 10.0
        assert isinstance(result, Experiment)

    @pytest.mark.asyncio
    async def test_end_experiment_with_status(self, async_client, experiment):
        """async_end_experiment sends the status as a query parameter."""
        async_client._async_request.return_value = _async_response(
            experiment.model_dump(mode="json")
        )

        result = await async_client.async_end_experiment(
            experiment.experiment_id, status=ExperimentStatus.COMPLETED
        )

        async_client._async_request.assert_awaited_once_with(
            "POST",
            EXPERIMENT_URL + f"experiment/{experiment.experiment_id}/end",
            params={"status": ExperimentStatus.COMPLETED},
            timeout=10.0,
        )
        assert isinstance(result, Experiment)

    @pytest.mark.asyncio
    async def test_register_campaign(self, async_client, campaign):
        """async_register_campaign posts the campaign and returns it."""
        async_client._async_request.return_value = _async_response(
            campaign.model_dump(mode="json")
        )

        result = await async_client.async_register_campaign(campaign)

        async_client._async_request.assert_awaited_once_with(
            "POST",
            EXPERIMENT_URL + "campaign",
            json=campaign.model_dump(mode="json"),
            timeout=10.0,
        )
        assert isinstance(result, ExperimentalCampaign)
        assert result.campaign_id == campaign.campaign_id

    @pytest.mark.asyncio
    async def test_get_campaign(self, async_client, campaign):
        """async_get_campaign gets one campaign by ID."""
        async_client._async_request.return_value = _async_response(
            campaign.model_dump(mode="json")
        )

        result = await async_client.async_get_campaign(campaign.campaign_id)

        async_client._async_request.assert_awaited_once_with(
            "GET", EXPERIMENT_URL + f"campaign/{campaign.campaign_id}", timeout=10.0
        )
        assert isinstance(result, ExperimentalCampaign)

    @pytest.mark.asyncio
    async def test_get_campaigns(self, async_client, campaign):
        """async_get_campaigns returns a list of campaigns."""
        async_client._async_request.return_value = _async_response(
            [campaign.model_dump(mode="json")]
        )

        result = await async_client.async_get_campaigns()

        async_client._async_request.assert_awaited_once_with(
            "GET", EXPERIMENT_URL + "campaigns", timeout=10.0
        )
        assert [c.campaign_id for c in result] == [campaign.campaign_id]

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("method_name", "args"),
        [
            ("async_get_experiments", ()),
            ("async_start_experiment", ("experiment_design",)),
            ("async_end_experiment", ("exp-id",)),
            ("async_register_campaign", ("campaign",)),
            ("async_get_campaign", ("campaign-id",)),
            ("async_get_campaigns", ()),
        ],
    )
    async def test_other_methods_raise_http_error(
        self, async_client, request, method_name, args
    ):
        """The other async methods also raise HTTPStatusError on an error response."""
        async_client._async_request.return_value = _async_response({}, 500)
        fixtures = {"experiment_design", "campaign"}
        call_args = [
            request.getfixturevalue(arg) if arg in fixtures else arg for arg in args
        ]

        with pytest.raises(httpx.HTTPStatusError):
            await getattr(async_client, method_name)(*call_args)

    @pytest.mark.asyncio
    async def test_end_experiment_without_status(self, async_client, experiment):
        """async_end_experiment without a status sends status=None."""
        async_client._async_request.return_value = _async_response(
            experiment.model_dump(mode="json")
        )

        await async_client.async_end_experiment(experiment.experiment_id)

        assert async_client._async_request.await_args.kwargs["params"] == {
            "status": None
        }
