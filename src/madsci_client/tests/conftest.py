"""Shared test fixtures for MADSci client tests."""

from typing import Optional
from unittest.mock import Mock, patch

import pytest
import requests


@pytest.fixture
def mock_http_session():
    """
    Fixture that provides a mock HTTP session for testing client requests.

    This fixture replaces the requests.Session object returned by create_http_session
    with a mock that can be configured for different test scenarios.

    Returns:
        Mock: A mock session object that can be configured to return specific responses

    Usage:
        def test_some_client_method(mock_http_session):
            # Configure the mock response
            mock_response = Mock()
            mock_response.json.return_value = {"test": "data"}
            mock_response.ok = True
            mock_response.status_code = 200
            mock_http_session.get.return_value = mock_response

            # Create client and test (the mock session will be used automatically)
            client = SomeClient(server_url="http://test/")
            result = client.some_method()

            # Verify the request was made correctly
            mock_http_session.get.assert_called_once()
    """
    with patch("madsci.common.utils.create_http_session") as mock_create_session:
        mock_session = Mock(spec=requests.Session)
        mock_create_session.return_value = mock_session
        yield mock_session


@pytest.fixture
def mock_successful_response():
    """
    Fixture that provides a mock HTTP response configured for success scenarios.

    Returns:
        Mock: A configured mock response object with common success attributes
    """
    mock_response = Mock()
    mock_response.ok = True
    mock_response.status_code = 200
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {}
    mock_response.text = ""
    mock_response.content = b""
    return mock_response


@pytest.fixture
def mock_error_response():
    """
    Fixture that provides a mock HTTP response configured for error scenarios.

    Returns:
        Mock: A configured mock response object with common error attributes
    """
    mock_response = Mock()
    mock_response.ok = False
    mock_response.status_code = 500
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        "Test error"
    )
    mock_response.json.return_value = {"error": "Test error"}
    mock_response.text = "Internal Server Error"
    mock_response.content = b"Internal Server Error"
    return mock_response


class HttpClientTestHelper:
    """
    Helper class for testing HTTP clients with the new create_http_session pattern.

    This class provides utility methods to simplify testing of MADSci HTTP clients
    by standardizing common test patterns.
    """

    @staticmethod
    def setup_mock_session(mock_session: Mock, method: str, response: Mock) -> None:
        """
        Configure a mock session to return a specific response for a given HTTP method.

        Args:
            mock_session: The mock session object (usually from mock_http_session fixture)
            method: The HTTP method name ('get', 'post', 'put', 'delete', etc.)
            response: The mock response object to return
        """
        getattr(mock_session, method.lower()).return_value = response

    @staticmethod
    def assert_request_made(
        mock_session: Mock,
        method: str,
        expected_url_suffix: Optional[str] = None,
        expected_params: Optional[dict] = None,
        expected_json: Optional[dict] = None,
        expected_timeout: Optional[float] = None,
    ) -> None:
        """
        Assert that a request was made with expected parameters.

        Args:
            mock_session: The mock session object
            method: The HTTP method name
            expected_url_suffix: Expected ending of the URL (optional)
            expected_params: Expected query parameters (optional)
            expected_json: Expected JSON payload (optional)
            expected_timeout: Expected timeout value (optional)
        """
        method_mock = getattr(mock_session, method.lower())
        method_mock.assert_called_once()

        call_args = method_mock.call_args

        if expected_url_suffix:
            url = call_args[0][0]
            assert url.endswith(expected_url_suffix), (
                f"URL {url} does not end with {expected_url_suffix}"
            )

        if expected_params:
            assert call_args[1].get("params") == expected_params

        if expected_json:
            assert call_args[1].get("json") == expected_json

        if expected_timeout:
            assert call_args[1].get("timeout") == expected_timeout


@pytest.fixture
def http_test_helper():
    """Fixture that provides the HttpClientTestHelper utility class."""
    return HttpClientTestHelper
