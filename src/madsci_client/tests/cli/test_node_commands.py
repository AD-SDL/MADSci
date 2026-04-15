"""Tests for the madsci node command group."""

from __future__ import annotations

from unittest.mock import patch

from click.testing import CliRunner
from madsci.client.cli import madsci
from madsci.common.types.action_types import ActionResult, ActionStatus
from madsci.common.types.admin_command_types import AdminCommandResponse
from madsci.common.types.node_types import (
    NodeSetConfigResponse,
    NodeStatus,
)
from madsci.common.utils import new_ulid_str

# Pre-generate stable ULID strings for tests
_NODE_ID = new_ulid_str()
_ACTION_ID = new_ulid_str()

_WC_URL = "http://localhost:8005/"
_NODE_URL = "http://localhost:2000/"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_node_dict(
    *,
    node_name: str = "test_node",
    node_url: str = _NODE_URL,
    ready: bool = True,
    actions: dict | None = None,
) -> dict:
    """Build a minimal node dict as returned by WorkcellClient.get_node()."""
    if actions is None:
        actions = {"pick": {"name": "pick", "description": "Pick an item"}}
    return {
        "node_url": node_url,
        "status": {
            "ready": ready,
            "busy": False,
            "paused": False,
            "locked": False,
            "stopped": False,
            "errored": False,
            "disconnected": False,
            "initializing": False,
            "running_actions": [],
            "errors": [],
            "waiting_for_config": [],
            "config_values": {},
        },
        "info": {
            "node_name": node_name,
            "node_id": _NODE_ID,
            "node_type": "device",
            "module_name": "test_module",
            "module_version": "1.0.0",
            "actions": actions,
            "capabilities": {"get_info": True, "send_action": True},
            "config": {"speed": 100, "timeout": 30},
        },
        "state": {"position": [0, 0, 0]},
    }


def _make_node_status(*, errored: bool = False) -> NodeStatus:
    """Build a NodeStatus for testing."""
    return NodeStatus(
        busy=False,
        paused=False,
        locked=False,
        stopped=False,
        errored=errored,
        disconnected=False,
        initializing=False,
    )


def _patch_wc_init():
    """Patch WorkcellClient.__init__ to avoid network access."""
    return patch(
        "madsci.client.workcell_client.WorkcellClient.__init__",
        return_value=None,
    )


def _patch_wc(method_name: str, return_value):
    """Shortcut to patch a WorkcellClient method."""
    return patch(
        f"madsci.client.workcell_client.WorkcellClient.{method_name}",
        return_value=return_value,
    )


def _patch_node_init():
    """Patch RestNodeClient.__init__ to avoid network access."""
    return patch(
        "madsci.client.node.rest_node_client.RestNodeClient.__init__",
        return_value=None,
    )


def _patch_node(method_name: str, return_value):
    """Shortcut to patch a RestNodeClient method."""
    return patch(
        f"madsci.client.node.rest_node_client.RestNodeClient.{method_name}",
        return_value=return_value,
    )


# ---------------------------------------------------------------------------
# node group help
# ---------------------------------------------------------------------------


class TestNodeGroup:
    """Tests for the node command group itself."""

    def test_node_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["node", "--help"])
        assert result.exit_code == 0
        assert "Manage nodes" in result.output

    def test_node_alias(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["nd", "--help"])
        assert result.exit_code == 0
        assert "Manage nodes" in result.output


# ---------------------------------------------------------------------------
# node list
# ---------------------------------------------------------------------------


class TestNodeList:
    """Tests for 'node list'."""

    def test_list_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["node", "list", "--help"])
        assert result.exit_code == 0
        assert "--workcell-url" in result.output

    def test_list_default(self) -> None:
        nodes = {"test_node": _make_node_dict()}
        with _patch_wc_init(), _patch_wc("get_nodes", nodes):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                ["node", "list", "--workcell-url", _WC_URL],
            )
            assert result.exit_code == 0
            assert "test_node" in result.output

    def test_list_empty(self) -> None:
        with _patch_wc_init(), _patch_wc("get_nodes", {}):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                ["node", "list", "--workcell-url", _WC_URL],
            )
            assert result.exit_code == 0
            assert "No nodes found" in result.output

    def test_list_json(self) -> None:
        nodes = {"test_node": _make_node_dict()}
        with _patch_wc_init(), _patch_wc("get_nodes", nodes):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                ["--json", "node", "list", "--workcell-url", _WC_URL],
            )
            assert result.exit_code == 0

    def test_list_quiet(self) -> None:
        nodes = {"test_node": _make_node_dict()}
        with _patch_wc_init(), _patch_wc("get_nodes", nodes):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                ["--quiet", "node", "list", "--workcell-url", _WC_URL],
            )
            assert result.exit_code == 0


# ---------------------------------------------------------------------------
# node info
# ---------------------------------------------------------------------------


class TestNodeInfo:
    """Tests for 'node info'."""

    def test_info_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["node", "info", "--help"])
        assert result.exit_code == 0

    def test_info_basic(self) -> None:
        node_data = _make_node_dict()
        with _patch_wc_init(), _patch_wc("get_node", node_data):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                ["node", "info", "test_node", "--workcell-url", _WC_URL],
            )
            assert result.exit_code == 0
            assert "test_node" in result.output
            assert "test_module" in result.output
            assert "pick" in result.output

    def test_info_json(self) -> None:
        node_data = _make_node_dict()
        with _patch_wc_init(), _patch_wc("get_node", node_data):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                ["--json", "node", "info", "test_node", "--workcell-url", _WC_URL],
            )
            assert result.exit_code == 0

    def test_info_quiet(self) -> None:
        node_data = _make_node_dict()
        with _patch_wc_init(), _patch_wc("get_node", node_data):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                ["--quiet", "node", "info", "test_node", "--workcell-url", _WC_URL],
            )
            assert result.exit_code == 0

    def test_info_not_found(self) -> None:
        with _patch_wc_init(), _patch_wc("get_node", None):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                ["node", "info", "missing", "--workcell-url", _WC_URL],
            )
            assert result.exit_code != 0
            assert "not found" in result.output


# ---------------------------------------------------------------------------
# node status
# ---------------------------------------------------------------------------


class TestNodeStatus:
    """Tests for 'node status'."""

    def test_status_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["node", "status", "--help"])
        assert result.exit_code == 0

    def test_status_basic(self) -> None:
        node_data = _make_node_dict()
        status = _make_node_status()
        with (
            _patch_wc_init(),
            _patch_wc("get_node", node_data),
            _patch_node_init(),
            _patch_node("get_status", status),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                ["node", "status", "test_node", "--workcell-url", _WC_URL],
            )
            assert result.exit_code == 0
            assert "ready" in result.output

    def test_status_json(self) -> None:
        node_data = _make_node_dict()
        status = _make_node_status()
        with (
            _patch_wc_init(),
            _patch_wc("get_node", node_data),
            _patch_node_init(),
            _patch_node("get_status", status),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                ["--json", "node", "status", "test_node", "--workcell-url", _WC_URL],
            )
            assert result.exit_code == 0

    def test_status_quiet(self) -> None:
        node_data = _make_node_dict()
        status = _make_node_status()
        with (
            _patch_wc_init(),
            _patch_wc("get_node", node_data),
            _patch_node_init(),
            _patch_node("get_status", status),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                ["--quiet", "node", "status", "test_node", "--workcell-url", _WC_URL],
            )
            assert result.exit_code == 0


# ---------------------------------------------------------------------------
# node state
# ---------------------------------------------------------------------------


class TestNodeState:
    """Tests for 'node state'."""

    def test_state_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["node", "state", "--help"])
        assert result.exit_code == 0

    def test_state_basic(self) -> None:
        node_data = _make_node_dict()
        state = {"position": [0, 0, 0], "temperature": 25.0}
        with (
            _patch_wc_init(),
            _patch_wc("get_node", node_data),
            _patch_node_init(),
            _patch_node("get_state", state),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                ["node", "state", "test_node", "--workcell-url", _WC_URL],
            )
            assert result.exit_code == 0

    def test_state_empty(self) -> None:
        node_data = _make_node_dict()
        with (
            _patch_wc_init(),
            _patch_wc("get_node", node_data),
            _patch_node_init(),
            _patch_node("get_state", {}),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                ["node", "state", "test_node", "--workcell-url", _WC_URL],
            )
            assert result.exit_code == 0
            assert "no state" in result.output.lower()

    def test_state_json(self) -> None:
        node_data = _make_node_dict()
        state = {"position": [0, 0, 0]}
        with (
            _patch_wc_init(),
            _patch_wc("get_node", node_data),
            _patch_node_init(),
            _patch_node("get_state", state),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                ["--json", "node", "state", "test_node", "--workcell-url", _WC_URL],
            )
            assert result.exit_code == 0


# ---------------------------------------------------------------------------
# node log
# ---------------------------------------------------------------------------


class TestNodeLog:
    """Tests for 'node log'."""

    def test_log_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["node", "log", "--help"])
        assert result.exit_code == 0
        assert "--tail" in result.output

    def test_log_basic(self) -> None:
        node_data = _make_node_dict()
        log_data = {
            "1": {
                "timestamp": "2026-01-01T12:00:00",
                "event_type": "INFO",
                "message": "Node started",
            },
            "2": {
                "timestamp": "2026-01-01T12:01:00",
                "event_type": "INFO",
                "message": "Action completed",
            },
        }
        with (
            _patch_wc_init(),
            _patch_wc("get_node", node_data),
            _patch_node_init(),
            _patch_node("get_log", log_data),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                ["node", "log", "test_node", "--workcell-url", _WC_URL],
            )
            assert result.exit_code == 0

    def test_log_empty(self) -> None:
        node_data = _make_node_dict()
        with (
            _patch_wc_init(),
            _patch_wc("get_node", node_data),
            _patch_node_init(),
            _patch_node("get_log", {}),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                ["node", "log", "test_node", "--workcell-url", _WC_URL],
            )
            assert result.exit_code == 0
            assert "No log entries" in result.output

    def test_log_json(self) -> None:
        node_data = _make_node_dict()
        log_data = [{"timestamp": "2026-01-01", "message": "test"}]
        with (
            _patch_wc_init(),
            _patch_wc("get_node", node_data),
            _patch_node_init(),
            _patch_node("get_log", log_data),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                ["--json", "node", "log", "test_node", "--workcell-url", _WC_URL],
            )
            assert result.exit_code == 0

    def test_log_with_tail(self) -> None:
        node_data = _make_node_dict()
        log_data = {str(i): {"message": f"event {i}"} for i in range(50)}
        with (
            _patch_wc_init(),
            _patch_wc("get_node", node_data),
            _patch_node_init(),
            _patch_node("get_log", log_data),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "node",
                    "log",
                    "test_node",
                    "--tail",
                    "5",
                    "--workcell-url",
                    _WC_URL,
                ],
            )
            assert result.exit_code == 0


# ---------------------------------------------------------------------------
# node admin
# ---------------------------------------------------------------------------


class TestNodeAdmin:
    """Tests for 'node admin'."""

    def test_admin_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["node", "admin", "--help"])
        assert result.exit_code == 0

    def test_admin_pause(self) -> None:
        node_data = _make_node_dict()
        response = AdminCommandResponse(success=True)
        with (
            _patch_wc_init(),
            _patch_wc("get_node", node_data),
            _patch_node_init(),
            _patch_node("send_admin_command", response),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                ["node", "admin", "test_node", "pause", "--workcell-url", _WC_URL],
            )
            assert result.exit_code == 0
            assert "pause" in result.output.lower()

    def test_admin_reset(self) -> None:
        node_data = _make_node_dict()
        response = AdminCommandResponse(success=True)
        with (
            _patch_wc_init(),
            _patch_wc("get_node", node_data),
            _patch_node_init(),
            _patch_node("send_admin_command", response),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                ["node", "admin", "test_node", "reset", "--workcell-url", _WC_URL],
            )
            assert result.exit_code == 0

    def test_admin_invalid_command(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            madsci,
            ["node", "admin", "test_node", "invalid", "--workcell-url", _WC_URL],
        )
        assert result.exit_code != 0

    def test_admin_json(self) -> None:
        node_data = _make_node_dict()
        response = AdminCommandResponse(success=True)
        with (
            _patch_wc_init(),
            _patch_wc("get_node", node_data),
            _patch_node_init(),
            _patch_node("send_admin_command", response),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "--json",
                    "node",
                    "admin",
                    "test_node",
                    "pause",
                    "--workcell-url",
                    _WC_URL,
                ],
            )
            assert result.exit_code == 0

    def test_admin_quiet(self) -> None:
        node_data = _make_node_dict()
        response = AdminCommandResponse(success=True)
        with (
            _patch_wc_init(),
            _patch_wc("get_node", node_data),
            _patch_node_init(),
            _patch_node("send_admin_command", response),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "--quiet",
                    "node",
                    "admin",
                    "test_node",
                    "pause",
                    "--workcell-url",
                    _WC_URL,
                ],
            )
            assert result.exit_code == 0


# ---------------------------------------------------------------------------
# node action
# ---------------------------------------------------------------------------


class TestNodeAction:
    """Tests for 'node action'."""

    def test_action_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["node", "action", "--help"])
        assert result.exit_code == 0
        assert "--args" in result.output
        assert "--file" in result.output
        assert "--no-wait" in result.output

    def test_action_basic(self) -> None:
        node_data = _make_node_dict()
        action_result = ActionResult(
            action_id=_ACTION_ID, status=ActionStatus.SUCCEEDED
        )
        with (
            _patch_wc_init(),
            _patch_wc("get_node", node_data),
            _patch_node_init(),
            _patch_node("send_action", action_result),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "node",
                    "action",
                    "test_node",
                    "pick",
                    "--workcell-url",
                    _WC_URL,
                ],
            )
            assert result.exit_code == 0
            assert "pick" in result.output

    def test_action_with_args(self) -> None:
        node_data = _make_node_dict()
        action_result = ActionResult(
            action_id=_ACTION_ID, status=ActionStatus.SUCCEEDED
        )
        with (
            _patch_wc_init(),
            _patch_wc("get_node", node_data),
            _patch_node_init(),
            _patch_node("send_action", action_result),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "node",
                    "action",
                    "test_node",
                    "pick",
                    "--args",
                    '{"plate_id": "p1"}',
                    "--workcell-url",
                    _WC_URL,
                ],
            )
            assert result.exit_code == 0

    def test_action_invalid_args_json(self) -> None:
        node_data = _make_node_dict()
        with (
            _patch_wc_init(),
            _patch_wc("get_node", node_data),
            _patch_node_init(),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "node",
                    "action",
                    "test_node",
                    "pick",
                    "--args",
                    "not-json",
                    "--workcell-url",
                    _WC_URL,
                ],
            )
            assert result.exit_code != 0
            assert "Invalid JSON" in result.output

    def test_action_invalid_file_format(self) -> None:
        node_data = _make_node_dict()
        with (
            _patch_wc_init(),
            _patch_wc("get_node", node_data),
            _patch_node_init(),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "node",
                    "action",
                    "test_node",
                    "pick",
                    "--file",
                    "no-equals-sign",
                    "--workcell-url",
                    _WC_URL,
                ],
            )
            assert result.exit_code != 0
            assert "Invalid --file" in result.output

    def test_action_no_wait(self) -> None:
        node_data = _make_node_dict()
        action_result = ActionResult(action_id=_ACTION_ID, status=ActionStatus.RUNNING)
        with (
            _patch_wc_init(),
            _patch_wc("get_node", node_data),
            _patch_node_init(),
            _patch_node("send_action", action_result),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "node",
                    "action",
                    "test_node",
                    "pick",
                    "--no-wait",
                    "--workcell-url",
                    _WC_URL,
                ],
            )
            assert result.exit_code == 0

    def test_action_json(self) -> None:
        node_data = _make_node_dict()
        action_result = ActionResult(
            action_id=_ACTION_ID, status=ActionStatus.SUCCEEDED
        )
        with (
            _patch_wc_init(),
            _patch_wc("get_node", node_data),
            _patch_node_init(),
            _patch_node("send_action", action_result),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "--json",
                    "node",
                    "action",
                    "test_node",
                    "pick",
                    "--workcell-url",
                    _WC_URL,
                ],
            )
            assert result.exit_code == 0


# ---------------------------------------------------------------------------
# node action-result
# ---------------------------------------------------------------------------


class TestNodeActionResult:
    """Tests for 'node action-result'."""

    def test_action_result_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["node", "action-result", "--help"])
        assert result.exit_code == 0

    def test_action_result_basic(self) -> None:
        node_data = _make_node_dict()
        action_result = ActionResult(
            action_id=_ACTION_ID, status=ActionStatus.SUCCEEDED
        )
        with (
            _patch_wc_init(),
            _patch_wc("get_node", node_data),
            _patch_node_init(),
            _patch_node("get_action_result", action_result),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "node",
                    "action-result",
                    "test_node",
                    _ACTION_ID,
                    "--workcell-url",
                    _WC_URL,
                ],
            )
            assert result.exit_code == 0

    def test_action_result_json(self) -> None:
        node_data = _make_node_dict()
        action_result = ActionResult(
            action_id=_ACTION_ID, status=ActionStatus.SUCCEEDED
        )
        with (
            _patch_wc_init(),
            _patch_wc("get_node", node_data),
            _patch_node_init(),
            _patch_node("get_action_result", action_result),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "--json",
                    "node",
                    "action-result",
                    "test_node",
                    _ACTION_ID,
                    "--workcell-url",
                    _WC_URL,
                ],
            )
            assert result.exit_code == 0


# ---------------------------------------------------------------------------
# node action-history
# ---------------------------------------------------------------------------


class TestNodeActionHistory:
    """Tests for 'node action-history'."""

    def test_action_history_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["node", "action-history", "--help"])
        assert result.exit_code == 0
        assert "--action" in result.output

    def test_action_history_basic(self) -> None:
        node_data = _make_node_dict()
        history = {
            "pick": [
                {"action_id": _ACTION_ID, "status": "succeeded"},
            ]
        }
        with (
            _patch_wc_init(),
            _patch_wc("get_node", node_data),
            _patch_node_init(),
            _patch_node("get_action_history", history),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "node",
                    "action-history",
                    "test_node",
                    "--workcell-url",
                    _WC_URL,
                ],
            )
            assert result.exit_code == 0
            assert "pick" in result.output

    def test_action_history_empty(self) -> None:
        node_data = _make_node_dict()
        with (
            _patch_wc_init(),
            _patch_wc("get_node", node_data),
            _patch_node_init(),
            _patch_node("get_action_history", {}),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "node",
                    "action-history",
                    "test_node",
                    "--workcell-url",
                    _WC_URL,
                ],
            )
            assert result.exit_code == 0
            assert "No action history" in result.output

    def test_action_history_json(self) -> None:
        node_data = _make_node_dict()
        history = {"pick": [{"action_id": _ACTION_ID, "status": "succeeded"}]}
        with (
            _patch_wc_init(),
            _patch_wc("get_node", node_data),
            _patch_node_init(),
            _patch_node("get_action_history", history),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "--json",
                    "node",
                    "action-history",
                    "test_node",
                    "--workcell-url",
                    _WC_URL,
                ],
            )
            assert result.exit_code == 0

    def test_action_history_with_filter(self) -> None:
        node_data = _make_node_dict()
        history = {"pick": [{"action_id": _ACTION_ID, "status": "succeeded"}]}
        with (
            _patch_wc_init(),
            _patch_wc("get_node", node_data),
            _patch_node_init(),
            _patch_node("get_action_history", history),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "node",
                    "action-history",
                    "test_node",
                    "--action",
                    "pick",
                    "--workcell-url",
                    _WC_URL,
                ],
            )
            assert result.exit_code == 0


# ---------------------------------------------------------------------------
# node config
# ---------------------------------------------------------------------------


class TestNodeConfig:
    """Tests for 'node config'."""

    def test_config_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["node", "config", "--help"])
        assert result.exit_code == 0

    def test_config_basic(self) -> None:
        node_data = _make_node_dict()
        with _patch_wc_init(), _patch_wc("get_node", node_data):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                ["node", "config", "test_node", "--workcell-url", _WC_URL],
            )
            assert result.exit_code == 0

    def test_config_json(self) -> None:
        node_data = _make_node_dict()
        with _patch_wc_init(), _patch_wc("get_node", node_data):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                ["--json", "node", "config", "test_node", "--workcell-url", _WC_URL],
            )
            assert result.exit_code == 0

    def test_config_no_config(self) -> None:
        node_data = _make_node_dict()
        node_data["info"]["config"] = None
        with _patch_wc_init(), _patch_wc("get_node", node_data):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                ["node", "config", "test_node", "--workcell-url", _WC_URL],
            )
            assert result.exit_code == 0
            assert "No configuration" in result.output

    def test_config_not_found(self) -> None:
        with _patch_wc_init(), _patch_wc("get_node", None):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                ["node", "config", "missing", "--workcell-url", _WC_URL],
            )
            assert result.exit_code != 0
            assert "not found" in result.output


# ---------------------------------------------------------------------------
# node set-config
# ---------------------------------------------------------------------------


class TestNodeSetConfig:
    """Tests for 'node set-config'."""

    def test_set_config_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["node", "set-config", "--help"])
        assert result.exit_code == 0
        assert "--data" in result.output

    def test_set_config_basic(self) -> None:
        node_data = _make_node_dict()
        response = NodeSetConfigResponse(success=True)
        with (
            _patch_wc_init(),
            _patch_wc("get_node", node_data),
            _patch_node_init(),
            _patch_node("set_config", response),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "node",
                    "set-config",
                    "test_node",
                    "--data",
                    '{"speed": 200}',
                    "--workcell-url",
                    _WC_URL,
                ],
            )
            assert result.exit_code == 0
            assert "updated" in result.output.lower()

    def test_set_config_invalid_json(self) -> None:
        node_data = _make_node_dict()
        with (
            _patch_wc_init(),
            _patch_wc("get_node", node_data),
            _patch_node_init(),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "node",
                    "set-config",
                    "test_node",
                    "--data",
                    "not-json",
                    "--workcell-url",
                    _WC_URL,
                ],
            )
            assert result.exit_code != 0
            assert "Invalid JSON" in result.output

    def test_set_config_json(self) -> None:
        node_data = _make_node_dict()
        response = NodeSetConfigResponse(success=True)
        with (
            _patch_wc_init(),
            _patch_wc("get_node", node_data),
            _patch_node_init(),
            _patch_node("set_config", response),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "--json",
                    "node",
                    "set-config",
                    "test_node",
                    "--data",
                    '{"speed": 200}',
                    "--workcell-url",
                    _WC_URL,
                ],
            )
            assert result.exit_code == 0

    def test_set_config_quiet(self) -> None:
        node_data = _make_node_dict()
        response = NodeSetConfigResponse(success=True)
        with (
            _patch_wc_init(),
            _patch_wc("get_node", node_data),
            _patch_node_init(),
            _patch_node("set_config", response),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "--quiet",
                    "node",
                    "set-config",
                    "test_node",
                    "--data",
                    '{"speed": 200}',
                    "--workcell-url",
                    _WC_URL,
                ],
            )
            assert result.exit_code == 0


# ---------------------------------------------------------------------------
# node add
# ---------------------------------------------------------------------------


class TestNodeAdd:
    """Tests for 'node add'."""

    def test_add_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["node", "add", "--help"])
        assert result.exit_code == 0
        assert "--description" in result.output
        assert "--permanent" in result.output

    def test_add_basic(self) -> None:
        node_result = _make_node_dict()
        with _patch_wc_init(), _patch_wc("add_node", node_result):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "node",
                    "add",
                    "new_node",
                    "http://localhost:2001",
                    "--workcell-url",
                    _WC_URL,
                ],
            )
            assert result.exit_code == 0
            assert "added" in result.output.lower()

    def test_add_permanent(self) -> None:
        node_result = _make_node_dict()
        with _patch_wc_init(), _patch_wc("add_node", node_result):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "node",
                    "add",
                    "new_node",
                    "http://localhost:2001",
                    "--permanent",
                    "--workcell-url",
                    _WC_URL,
                ],
            )
            assert result.exit_code == 0
            assert "permanent" in result.output.lower()

    def test_add_json(self) -> None:
        node_result = _make_node_dict()
        with _patch_wc_init(), _patch_wc("add_node", node_result):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "--json",
                    "node",
                    "add",
                    "new_node",
                    "http://localhost:2001",
                    "--workcell-url",
                    _WC_URL,
                ],
            )
            assert result.exit_code == 0

    def test_add_quiet(self) -> None:
        node_result = _make_node_dict()
        with _patch_wc_init(), _patch_wc("add_node", node_result):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "--quiet",
                    "node",
                    "add",
                    "new_node",
                    "http://localhost:2001",
                    "--workcell-url",
                    _WC_URL,
                ],
            )
            assert result.exit_code == 0

    def test_add_missing_url(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            madsci,
            ["node", "add", "new_node", "--workcell-url", _WC_URL],
        )
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# node shell
# ---------------------------------------------------------------------------


class TestNodeShell:
    """Tests for 'node shell'."""

    def test_shell_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["node", "shell", "--help"])
        assert result.exit_code == 0

    def test_shell_exit(self) -> None:
        node_data = _make_node_dict()
        with (
            _patch_wc_init(),
            _patch_wc("get_node", node_data),
            _patch_node_init(),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                ["node", "shell", "test_node", "--workcell-url", _WC_URL],
                input="exit\n",
            )
            assert result.exit_code == 0

    def test_shell_status_command(self) -> None:
        node_data = _make_node_dict()
        status = _make_node_status()
        with (
            _patch_wc_init(),
            _patch_wc("get_node", node_data),
            _patch_node_init(),
            _patch_node("get_status", status),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                ["node", "shell", "test_node", "--workcell-url", _WC_URL],
                input="status\nexit\n",
            )
            assert result.exit_code == 0

    def test_shell_help_command(self) -> None:
        node_data = _make_node_dict()
        with (
            _patch_wc_init(),
            _patch_wc("get_node", node_data),
            _patch_node_init(),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                ["node", "shell", "test_node", "--workcell-url", _WC_URL],
                input="help\nexit\n",
            )
            assert result.exit_code == 0

    def test_shell_empty_line(self) -> None:
        node_data = _make_node_dict()
        with (
            _patch_wc_init(),
            _patch_wc("get_node", node_data),
            _patch_node_init(),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                ["node", "shell", "test_node", "--workcell-url", _WC_URL],
                input="\nexit\n",
            )
            assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


class TestNodeRegistered:
    """Test that the node command is properly registered."""

    def test_node_in_lazy_commands(self) -> None:
        from madsci.client.cli import _LAZY_COMMANDS

        assert "node" in _LAZY_COMMANDS

    def test_nd_alias(self) -> None:
        from madsci.client.cli import AliasedGroup

        assert "nd" in AliasedGroup._aliases
        assert AliasedGroup._aliases["nd"] == "node"
