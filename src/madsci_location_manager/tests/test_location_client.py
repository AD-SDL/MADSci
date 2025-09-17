"""Tests for the LocationClient."""

import pytest
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
        x=10.0,
        y=20.0,
        z=30.0,
    )
