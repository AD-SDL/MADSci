"""Tests for async action execution methods on RestNodeClient."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from madsci.client.node.rest_node_client import RestNodeClient
from madsci.common.types.action_types import (
    ActionRequest,
    ActionResult,
    ActionStatus,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_client(url: str = "http://localhost:8000/") -> RestNodeClient:
    """Create a RestNodeClient with mocked internals for testing."""
    with patch("madsci.common.http_client.create_httpx_client") as mock_create:
        mock_create.return_value = MagicMock(spec=httpx.Client)
        return RestNodeClient(url=url)


def _mock_response(json_data: dict, status_code: int = 200) -> MagicMock:
    """Create a mock httpx.Response with the given JSON payload."""
    resp = MagicMock(spec=httpx.Response)
    resp.json.return_value = json_data
    resp.status_code = status_code
    resp.raise_for_status.return_value = None
    return resp


def _two_step_side_effect(create_resp: MagicMock, start_resp: MagicMock) -> AsyncMock:
    """Build an AsyncMock side-effect that returns *create_resp* on the first
    call and *start_resp* on subsequent calls.  The fake function uses
    underscore-prefixed parameters to satisfy linter ARG001 rules."""
    responses = iter([create_resp, start_resp])

    async def _side_effect(_method: str, _url: str, **_kwargs) -> MagicMock:
        return next(responses)

    return AsyncMock(side_effect=_side_effect)


# ---------------------------------------------------------------------------
# async_send_action tests
# ---------------------------------------------------------------------------


class TestAsyncSendAction:
    """Tests for RestNodeClient.async_send_action."""

    @pytest.mark.asyncio
    async def test_method_exists(self) -> None:
        """async_send_action should exist on RestNodeClient."""
        client = _make_client()
        assert hasattr(client, "async_send_action")
        assert callable(client.async_send_action)

    @pytest.mark.asyncio
    async def test_posts_to_correct_url(self) -> None:
        """async_send_action should POST to action/{action_name}."""
        client = _make_client()

        mock_create = _mock_response({"action_id": "test-id-123"})
        mock_start = _mock_response({"action_id": "test-id-123", "status": "running"})
        client._async_request = _two_step_side_effect(mock_create, mock_start)

        action_request = ActionRequest(action_name="test_action", args={"key": "value"})
        await client.async_send_action(action_request)

        first_call = client._async_request.call_args_list[0]
        assert first_call[0][0] == "POST"
        assert "action/test_action" in first_call[0][1]

    @pytest.mark.asyncio
    async def test_serializes_args_as_json_body(self) -> None:
        """async_send_action should serialize action args into JSON request body."""
        client = _make_client()

        mock_create = _mock_response({"action_id": "test-id-123"})
        mock_start = _mock_response({"action_id": "test-id-123", "status": "running"})
        client._async_request = _two_step_side_effect(mock_create, mock_start)

        action_request = ActionRequest(
            action_name="test_action",
            args={"key": "value", "count": 42},
        )
        await client.async_send_action(action_request)

        first_call = client._async_request.call_args_list[0]
        json_body = first_call[1].get("json") or first_call.kwargs.get("json")
        assert json_body is not None
        assert json_body["args"] == {"key": "value", "count": 42}

    @pytest.mark.asyncio
    async def test_returns_action_result(self) -> None:
        """async_send_action should return an ActionResult."""
        client = _make_client()

        mock_create = _mock_response({"action_id": "test-id-123"})
        mock_start = _mock_response({"action_id": "test-id-123", "status": "running"})
        client._async_request = _two_step_side_effect(mock_create, mock_start)

        action_request = ActionRequest(action_name="test_action", args={})
        result = await client.async_send_action(action_request)

        assert isinstance(result, ActionResult)
        assert result.action_id == "test-id-123"

    @pytest.mark.asyncio
    async def test_calls_raise_for_status(self) -> None:
        """async_send_action should call raise_for_status on each response."""
        client = _make_client()

        mock_create = _mock_response({"action_id": "test-id-123"})
        mock_start = _mock_response({"action_id": "test-id-123", "status": "running"})
        client._async_request = _two_step_side_effect(mock_create, mock_start)

        action_request = ActionRequest(action_name="test_action", args={})
        await client.async_send_action(action_request)

        mock_create.raise_for_status.assert_called_once()
        mock_start.raise_for_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_does_not_await_result(self) -> None:
        """async_send_action should NOT poll or wait for the action to complete."""
        client = _make_client()

        mock_create = _mock_response({"action_id": "test-id-123"})
        mock_start = _mock_response({"action_id": "test-id-123", "status": "running"})
        client._async_request = _two_step_side_effect(mock_create, mock_start)

        action_request = ActionRequest(action_name="test_action", args={})
        result = await client.async_send_action(action_request)

        # Should return running status (not wait for completion)
        assert result.status == ActionStatus.RUNNING
        # Should only make 2 calls (create + start), not additional polling calls
        assert client._async_request.call_count == 2

    @pytest.mark.asyncio
    async def test_uses_timeout(self) -> None:
        """async_send_action should pass timeout to _async_request."""
        client = _make_client()

        mock_create = _mock_response({"action_id": "test-id-123"})
        mock_start = _mock_response({"action_id": "test-id-123", "status": "running"})
        client._async_request = _two_step_side_effect(mock_create, mock_start)

        action_request = ActionRequest(action_name="test_action", args={})
        await client.async_send_action(action_request, timeout=30.0)

        # Both calls should have received the timeout
        for call in client._async_request.call_args_list:
            assert call[1].get("timeout") == 30.0 or call.kwargs.get("timeout") == 30.0

    @pytest.mark.asyncio
    async def test_serializes_var_args(self) -> None:
        """async_send_action should include var_args in JSON body when present."""
        client = _make_client()

        mock_create = _mock_response({"action_id": "test-id-123"})
        mock_start = _mock_response({"action_id": "test-id-123", "status": "running"})
        client._async_request = _two_step_side_effect(mock_create, mock_start)

        action_request = ActionRequest(
            action_name="test_action",
            args={"key": "value"},
            var_args=["a", "b"],
            var_kwargs={"extra": "stuff"},
        )
        await client.async_send_action(action_request)

        first_call = client._async_request.call_args_list[0]
        json_body = first_call[1].get("json") or first_call.kwargs.get("json")
        assert json_body["var_args"] == ["a", "b"]
        assert json_body["var_kwargs"] == {"extra": "stuff"}

    @pytest.mark.asyncio
    async def test_propagates_http_errors(self) -> None:
        """async_send_action should propagate HTTP errors from the request."""
        client = _make_client()

        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        error = httpx.HTTPStatusError(
            "Server error",
            request=httpx.Request("POST", "http://localhost:8000/action/test"),
            response=httpx.Response(500),
        )
        mock_resp.raise_for_status.side_effect = error

        client._async_request = AsyncMock(return_value=mock_resp)

        action_request = ActionRequest(action_name="test_action", args={})
        with pytest.raises(httpx.HTTPStatusError):
            await client.async_send_action(action_request)


# ---------------------------------------------------------------------------
# async_get_action_result_by_name tests
# ---------------------------------------------------------------------------


class TestAsyncGetActionResultByName:
    """Tests for RestNodeClient.async_get_action_result_by_name."""

    @pytest.mark.asyncio
    async def test_method_exists(self) -> None:
        """async_get_action_result_by_name should exist on RestNodeClient."""
        client = _make_client()
        assert hasattr(client, "async_get_action_result_by_name")
        assert callable(client.async_get_action_result_by_name)

    @pytest.mark.asyncio
    async def test_gets_from_correct_url(self) -> None:
        """async_get_action_result_by_name should GET from action/{name}/{id}/result."""
        client = _make_client()

        mock_resp = _mock_response({"action_id": "action-123", "status": "succeeded"})
        client._async_request = AsyncMock(return_value=mock_resp)

        await client.async_get_action_result_by_name("my_action", "action-123")

        client._async_request.assert_called_once()
        call_args = client._async_request.call_args
        assert call_args[0][0] == "GET"
        assert "action/my_action/action-123/result" in call_args[0][1]

    @pytest.mark.asyncio
    async def test_returns_action_result(self) -> None:
        """async_get_action_result_by_name should return an ActionResult."""
        client = _make_client()

        mock_resp = _mock_response(
            {
                "action_id": "action-123",
                "status": "succeeded",
                "json_result": {"output": 42},
            }
        )
        client._async_request = AsyncMock(return_value=mock_resp)

        result = await client.async_get_action_result_by_name("my_action", "action-123")

        assert isinstance(result, ActionResult)
        assert result.action_id == "action-123"
        assert result.status == ActionStatus.SUCCEEDED

    @pytest.mark.asyncio
    async def test_calls_raise_for_status(self) -> None:
        """async_get_action_result_by_name should call raise_for_status on the response."""
        client = _make_client()

        mock_resp = _mock_response({"action_id": "action-123", "status": "succeeded"})
        client._async_request = AsyncMock(return_value=mock_resp)

        await client.async_get_action_result_by_name("my_action", "action-123")

        mock_resp.raise_for_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_uses_timeout(self) -> None:
        """async_get_action_result_by_name should pass timeout to _async_request."""
        client = _make_client()

        mock_resp = _mock_response({"action_id": "action-123", "status": "succeeded"})
        client._async_request = AsyncMock(return_value=mock_resp)

        await client.async_get_action_result_by_name(
            "my_action", "action-123", timeout=15.0
        )

        call_args = client._async_request.call_args
        timeout_used = call_args[1].get("timeout") or call_args.kwargs.get("timeout")
        assert timeout_used == 15.0

    @pytest.mark.asyncio
    async def test_include_files_false_strips_files(self) -> None:
        """async_get_action_result_by_name with include_files=False should not fetch files."""
        client = _make_client()

        mock_resp = _mock_response(
            {
                "action_id": "action-123",
                "status": "succeeded",
                "files": ["file1.txt", "file2.txt"],
            }
        )
        client._async_request = AsyncMock(return_value=mock_resp)

        result = await client.async_get_action_result_by_name(
            "my_action", "action-123", include_files=False
        )

        assert isinstance(result, ActionResult)
        # files should be None since include_files=False
        assert result.files is None
        # Only one HTTP call (no file download calls)
        assert client._async_request.call_count == 1

    @pytest.mark.asyncio
    async def test_propagates_http_errors(self) -> None:
        """async_get_action_result_by_name should propagate non-server HTTP errors."""
        client = _make_client()

        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 404
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not found",
            request=httpx.Request("GET", "http://localhost:8000/action/test/id/result"),
            response=httpx.Response(404),
        )
        client._async_request = AsyncMock(return_value=mock_resp)

        with pytest.raises(httpx.HTTPStatusError):
            await client.async_get_action_result_by_name("test", "id")

    @pytest.mark.asyncio
    async def test_server_error_falls_back_to_generic_endpoint(self) -> None:
        """async_get_action_result_by_name should fall back on 500+ errors."""
        client = _make_client()

        # First response: 500 error from typed endpoint
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 500
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server error",
            request=httpx.Request("GET", "http://localhost:8000/action/test/id/result"),
            response=httpx.Response(500),
        )

        # Second response: success from fallback generic endpoint
        mock_fallback_resp = _mock_response({"action_id": "id", "status": "succeeded"})

        responses = iter([mock_resp, mock_fallback_resp])

        async def _fake_request(_method: str, _url: str, **_kwargs) -> MagicMock:
            return next(responses)

        client._async_request = AsyncMock(side_effect=_fake_request)

        result = await client.async_get_action_result_by_name("test", "id")

        assert isinstance(result, ActionResult)
        # Should have made 2 calls: original typed endpoint + fallback
        assert client._async_request.call_count == 2

    @pytest.mark.asyncio
    async def test_default_timeout_used_when_none(self) -> None:
        """async_get_action_result_by_name should use config.timeout_default when no timeout given."""
        client = _make_client()

        mock_resp = _mock_response({"action_id": "action-123", "status": "succeeded"})
        client._async_request = AsyncMock(return_value=mock_resp)

        await client.async_get_action_result_by_name("my_action", "action-123")

        call_args = client._async_request.call_args
        timeout_val = call_args[1].get("timeout") or call_args.kwargs.get("timeout")
        assert timeout_val == client.config.timeout_default
