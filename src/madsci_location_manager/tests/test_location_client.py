"""Tests for the LocationClient."""

import inspect
from unittest.mock import Mock, patch

import pytest
import requests
from madsci.client.location_client import LocationClient
from madsci.common.types.location_types import Location
from madsci.common.utils import new_ulid_str


def test_location_client_initialization():
    """Test LocationClient initialization."""
    client = LocationClient("http://localhost:8006")
    assert str(client.location_server_url) == "http://localhost:8006/"


def test_location_client_initialization_with_trailing_slash():
    """Test LocationClient initialization with URL that already has trailing slash."""
    client = LocationClient("http://localhost:8006/")
    assert str(client.location_server_url) == "http://localhost:8006/"


def test_location_client_headers():
    """Test that headers are properly formatted."""
    client = LocationClient("http://localhost:8006")
    headers = client._get_headers()
    assert headers["Content-Type"] == "application/json"


@pytest.fixture
def sample_location():
    """Create a sample location for testing."""
    return Location(
        location_id=new_ulid_str(),
        name="Test Location",
        description="A test location",
    )


@pytest.fixture
def location_client():
    """Create a LocationClient for testing."""
    return LocationClient("http://localhost:8006")


def test_transfer_methods_exist(location_client):
    """Test that transfer methods exist and are callable."""
    # These methods should exist and be callable
    assert hasattr(location_client, "get_transfer_graph")
    assert callable(location_client.get_transfer_graph)

    assert hasattr(location_client, "plan_transfer")
    assert callable(location_client.plan_transfer)

    assert hasattr(location_client, "get_location_resources")
    assert callable(location_client.get_location_resources)


def test_transfer_method_signatures(location_client):
    """Test that transfer methods have correct signatures."""
    # Check get_transfer_graph signature
    sig = inspect.signature(location_client.get_transfer_graph)
    params = list(sig.parameters.keys())
    assert "retry" in params

    # Check plan_transfer signature
    sig = inspect.signature(location_client.plan_transfer)
    params = list(sig.parameters.keys())
    assert "source_location_id" in params
    assert "destination_location_id" in params
    assert "resource_id" in params
    assert "retry" in params

    # Check get_location_resources signature
    sig = inspect.signature(location_client.get_location_resources)
    params = list(sig.parameters.keys())
    assert "location_id" in params
    assert "retry" in params


def test_get_location_by_name_method_exists(location_client):
    """Test that get_location_by_name method exists and is callable."""
    assert hasattr(location_client, "get_location_by_name")
    assert callable(location_client.get_location_by_name)


def test_get_location_by_name_method_signature(location_client):
    """Test that get_location_by_name method has correct signature."""
    sig = inspect.signature(location_client.get_location_by_name)
    params = list(sig.parameters.keys())
    assert "location_name" in params
    assert "retry" in params

    # Check return type annotation
    assert sig.return_annotation.__name__ == "Location"


@patch("madsci.client.location_client.requests.Session.get")
def test_get_location_by_name_method_request(mock_get, location_client):
    """Test that get_location_by_name makes correct HTTP request."""

    # Mock successful response
    mock_response = Mock()
    test_location_id = new_ulid_str()  # Generate valid ULID
    mock_location_data = {
        "location_id": test_location_id,
        "name": "test_location_name",
        "description": "Test location description",
    }
    mock_response.json.return_value = mock_location_data
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    # Call the method
    result = location_client.get_location_by_name("test_location_name")

    # Verify the request was made correctly
    mock_get.assert_called_once()
    call_args = mock_get.call_args
    # Check that the URL is correct and query parameters are used
    assert call_args[0][0].endswith("/location")
    assert call_args[1]["params"] == {"name": "test_location_name"}

    # Verify the result is a Location object
    assert isinstance(result, Location)
    assert result.name == "test_location_name"
    assert result.location_id == test_location_id


@patch("madsci.client.location_client.requests.Session.get")
def test_get_location_by_name_method_error_handling(mock_get, location_client):
    """Test that get_location_by_name handles errors correctly."""

    # Mock 404 response
    mock_response = Mock()
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        "404 Not Found"
    )
    mock_get.return_value = mock_response

    # Call the method and expect an exception
    with pytest.raises(requests.exceptions.HTTPError):
        location_client.get_location_by_name("nonexistent_location")
