"""Tests for the madsci workflow command group."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import patch

from click.testing import CliRunner
from madsci.client.cli import madsci
from madsci.common.types.action_types import ActionStatus
from madsci.common.types.step_types import Step
from madsci.common.types.workflow_types import (
    Workflow,
    WorkflowStatus,
)
from madsci.common.utils import new_ulid_str

# Pre-generate stable ULID strings for tests
_WF_ID_DEFAULT = new_ulid_str()
_WF_ID_ACTIVE = new_ulid_str()
_WF_ID_ARCHIVED = new_ulid_str()
_WF_ID_NEW = new_ulid_str()
_WF_ID_RESUBMIT = new_ulid_str()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_workflow(
    *,
    workflow_id: str | None = None,
    name: str = "test-workflow",
    status_kwargs: dict | None = None,
    steps: list[Step] | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    label: str | None = None,
) -> Workflow:
    """Build a minimal Workflow for testing."""
    if workflow_id is None:
        workflow_id = _WF_ID_DEFAULT
    if status_kwargs is None:
        status_kwargs = {"running": True}
    wf_status = WorkflowStatus(**status_kwargs)

    if steps is None:
        steps = [
            Step(
                name="step_0",
                action="do_thing",
                node="my_node",
                status=ActionStatus.SUCCEEDED,
            ),
            Step(
                name="step_1",
                action="do_other",
                node="other_node",
                status=ActionStatus.NOT_STARTED,
            ),
        ]

    return Workflow(
        name=name,
        workflow_id=workflow_id,
        status=wf_status,
        steps=steps,
        start_time=start_time,
        end_time=end_time,
        label=label,
    )


def _patch_client(method_name: str, return_value):
    """Shortcut to patch a WorkcellClient method."""
    return patch(
        f"madsci.client.workcell_client.WorkcellClient.{method_name}",
        return_value=return_value,
    )


def _patch_client_init():
    """Patch WorkcellClient.__init__ to avoid network access."""
    return patch(
        "madsci.client.workcell_client.WorkcellClient.__init__",
        return_value=None,
    )


# ---------------------------------------------------------------------------
# workflow group help
# ---------------------------------------------------------------------------


class TestWorkflowGroup:
    """Tests for the workflow command group itself."""

    def test_workflow_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["workflow", "--help"])
        assert result.exit_code == 0
        assert "Manage workflows" in result.output

    def test_workflow_alias(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["wf", "--help"])
        assert result.exit_code == 0
        assert "Manage workflows" in result.output


# ---------------------------------------------------------------------------
# workflow list
# ---------------------------------------------------------------------------


class TestWorkflowList:
    """Tests for 'workflow list'."""

    def test_list_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["workflow", "list", "--help"])
        assert result.exit_code == 0
        assert "--active" in result.output
        assert "--archived" in result.output
        assert "--limit" in result.output

    def test_list_default(self) -> None:
        wf = _make_workflow()
        with (
            _patch_client_init(),
            _patch_client("get_active_workflows", {"wf1": wf}),
            _patch_client("get_workflow_queue", []),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                ["workflow", "list", "--workcell-url", "http://localhost:8005/"],
            )
            assert result.exit_code == 0
            # Table may truncate the name; check for the prefix
            assert "test-work" in result.output

    def test_list_all(self) -> None:
        wf_active = _make_workflow(workflow_id=_WF_ID_ACTIVE)
        wf_archived = _make_workflow(
            workflow_id=_WF_ID_ARCHIVED,
            status_kwargs={"completed": True},
        )
        with (
            _patch_client_init(),
            _patch_client("get_active_workflows", {"a": wf_active}),
            _patch_client("get_workflow_queue", []),
            _patch_client("get_archived_workflows", {"b": wf_archived}),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "workflow",
                    "list",
                    "--all",
                    "--workcell-url",
                    "http://localhost:8005/",
                ],
            )
            assert result.exit_code == 0

    def test_list_json(self) -> None:
        wf = _make_workflow()
        with (
            _patch_client_init(),
            _patch_client("get_active_workflows", {"wf1": wf}),
            _patch_client("get_workflow_queue", []),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "--json",
                    "workflow",
                    "list",
                    "--workcell-url",
                    "http://localhost:8005/",
                ],
            )
            assert result.exit_code == 0

    def test_list_quiet(self) -> None:
        wf = _make_workflow()
        with (
            _patch_client_init(),
            _patch_client("get_active_workflows", {"wf1": wf}),
            _patch_client("get_workflow_queue", []),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "--quiet",
                    "workflow",
                    "list",
                    "--workcell-url",
                    "http://localhost:8005/",
                ],
            )
            # quiet Console suppresses output by design; just verify no crash
            assert result.exit_code == 0

    def test_list_empty(self) -> None:
        with (
            _patch_client_init(),
            _patch_client("get_active_workflows", {}),
            _patch_client("get_workflow_queue", []),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                ["workflow", "list", "--workcell-url", "http://localhost:8005/"],
            )
            assert result.exit_code == 0
            assert "No workflows found" in result.output


# ---------------------------------------------------------------------------
# workflow show
# ---------------------------------------------------------------------------


class TestWorkflowShow:
    """Tests for 'workflow show'."""

    def test_show_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["workflow", "show", "--help"])
        assert result.exit_code == 0
        assert "--steps" in result.output
        assert "--follow" in result.output

    def test_show_basic(self) -> None:
        wf = _make_workflow(
            start_time=datetime(2026, 1, 1, 12, 0, 0),
            end_time=datetime(2026, 1, 1, 12, 5, 0),
        )
        with _patch_client_init(), _patch_client("query_workflow", wf):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "workflow",
                    "show",
                    _WF_ID_DEFAULT,
                    "--workcell-url",
                    "http://localhost:8005/",
                ],
            )
            assert result.exit_code == 0
            assert "test-workflow" in result.output
            assert _WF_ID_DEFAULT[:12] in result.output

    def test_show_with_steps(self) -> None:
        wf = _make_workflow()
        with _patch_client_init(), _patch_client("query_workflow", wf):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "workflow",
                    "show",
                    _WF_ID_DEFAULT,
                    "--steps",
                    "--workcell-url",
                    "http://localhost:8005/",
                ],
            )
            assert result.exit_code == 0
            assert "step_0" in result.output
            assert "step_1" in result.output
            assert "do_thing" in result.output

    def test_show_json(self) -> None:
        wf = _make_workflow()
        with _patch_client_init(), _patch_client("query_workflow", wf):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "--json",
                    "workflow",
                    "show",
                    _WF_ID_DEFAULT,
                    "--workcell-url",
                    "http://localhost:8005/",
                ],
            )
            assert result.exit_code == 0

    def test_show_quiet(self) -> None:
        wf = _make_workflow()
        with _patch_client_init(), _patch_client("query_workflow", wf):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "--quiet",
                    "workflow",
                    "show",
                    _WF_ID_DEFAULT,
                    "--workcell-url",
                    "http://localhost:8005/",
                ],
            )
            # quiet Console suppresses output by design; just verify no crash
            assert result.exit_code == 0

    def test_show_not_found(self) -> None:
        with _patch_client_init(), _patch_client("query_workflow", None):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "workflow",
                    "show",
                    "NOTFOUND12345",
                    "--workcell-url",
                    "http://localhost:8005/",
                ],
            )
            assert result.exit_code != 0
            assert "not found" in result.output


# ---------------------------------------------------------------------------
# workflow submit
# ---------------------------------------------------------------------------


class TestWorkflowSubmit:
    """Tests for 'workflow submit'."""

    def test_submit_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["workflow", "submit", "--help"])
        assert result.exit_code == 0
        assert "--parameters" in result.output
        assert "--no-wait" in result.output
        assert "--name" in result.output

    def test_submit_missing_path(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["workflow", "submit"])
        assert result.exit_code != 0

    def test_submit_nonexistent_file(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["workflow", "submit", "/nonexistent/path.yaml"])
        assert result.exit_code != 0

    def test_submit_no_wait(self, tmp_path) -> None:
        wf_yaml = tmp_path / "test.workflow.yaml"
        wf_yaml.write_text(
            "name: test\nsteps:\n  - name: s1\n    action: do_it\n    node: n1\n"
        )

        with (
            _patch_client_init(),
            _patch_client("submit_workflow_definition", _WF_ID_NEW),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "workflow",
                    "submit",
                    str(wf_yaml),
                    "--no-wait",
                    "--workcell-url",
                    "http://localhost:8005/",
                ],
            )
            assert result.exit_code == 0
            assert _WF_ID_NEW[:12] in result.output

    def test_submit_no_wait_quiet(self, tmp_path) -> None:
        wf_yaml = tmp_path / "test.workflow.yaml"
        wf_yaml.write_text(
            "name: test\nsteps:\n  - name: s1\n    action: do_it\n    node: n1\n"
        )

        with (
            _patch_client_init(),
            _patch_client("submit_workflow_definition", _WF_ID_NEW),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "--quiet",
                    "workflow",
                    "submit",
                    str(wf_yaml),
                    "--no-wait",
                    "--workcell-url",
                    "http://localhost:8005/",
                ],
            )
            # quiet Console suppresses output by design; just verify no crash
            assert result.exit_code == 0

    def test_submit_wait(self, tmp_path) -> None:
        wf_yaml = tmp_path / "test.workflow.yaml"
        wf_yaml.write_text(
            "name: test\nsteps:\n  - name: s1\n    action: do_it\n    node: n1\n"
        )

        wf = _make_workflow(status_kwargs={"completed": True})
        with _patch_client_init(), _patch_client("start_workflow", wf):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "workflow",
                    "submit",
                    str(wf_yaml),
                    "--workcell-url",
                    "http://localhost:8005/",
                ],
            )
            assert result.exit_code == 0
            assert (
                "finished" in result.output.lower()
                or "completed" in result.output.lower()
            )

    def test_submit_invalid_parameters_json(self, tmp_path) -> None:
        wf_yaml = tmp_path / "test.workflow.yaml"
        wf_yaml.write_text(
            "name: test\nsteps:\n  - name: s1\n    action: do_it\n    node: n1\n"
        )

        runner = CliRunner()
        result = runner.invoke(
            madsci,
            [
                "workflow",
                "submit",
                str(wf_yaml),
                "--parameters",
                "not-valid-json",
                "--workcell-url",
                "http://localhost:8005/",
            ],
        )
        assert result.exit_code != 0
        assert "Invalid JSON" in result.output


# ---------------------------------------------------------------------------
# workflow pause
# ---------------------------------------------------------------------------


class TestWorkflowPause:
    """Tests for 'workflow pause'."""

    def test_pause_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["workflow", "pause", "--help"])
        assert result.exit_code == 0

    def test_pause_basic(self) -> None:
        wf = _make_workflow(status_kwargs={"paused": True})
        with _patch_client_init(), _patch_client("pause_workflow", wf):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "workflow",
                    "pause",
                    _WF_ID_DEFAULT,
                    "--workcell-url",
                    "http://localhost:8005/",
                ],
            )
            assert result.exit_code == 0
            assert "paused" in result.output.lower()

    def test_pause_json(self) -> None:
        wf = _make_workflow(status_kwargs={"paused": True})
        with _patch_client_init(), _patch_client("pause_workflow", wf):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "--json",
                    "workflow",
                    "pause",
                    _WF_ID_DEFAULT,
                    "--workcell-url",
                    "http://localhost:8005/",
                ],
            )
            assert result.exit_code == 0


# ---------------------------------------------------------------------------
# workflow resume
# ---------------------------------------------------------------------------


class TestWorkflowResume:
    """Tests for 'workflow resume'."""

    def test_resume_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["workflow", "resume", "--help"])
        assert result.exit_code == 0

    def test_resume_basic(self) -> None:
        wf = _make_workflow(status_kwargs={"running": True})
        with _patch_client_init(), _patch_client("resume_workflow", wf):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "workflow",
                    "resume",
                    _WF_ID_DEFAULT,
                    "--workcell-url",
                    "http://localhost:8005/",
                ],
            )
            assert result.exit_code == 0
            assert "resumed" in result.output.lower()


# ---------------------------------------------------------------------------
# workflow cancel
# ---------------------------------------------------------------------------


class TestWorkflowCancel:
    """Tests for 'workflow cancel'."""

    def test_cancel_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["workflow", "cancel", "--help"])
        assert result.exit_code == 0
        assert "--yes" in result.output

    def test_cancel_with_yes(self) -> None:
        wf = _make_workflow(status_kwargs={"cancelled": True})
        with _patch_client_init(), _patch_client("cancel_workflow", wf):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "workflow",
                    "cancel",
                    _WF_ID_DEFAULT,
                    "--yes",
                    "--workcell-url",
                    "http://localhost:8005/",
                ],
            )
            assert result.exit_code == 0
            assert "cancelled" in result.output.lower()

    def test_cancel_abort(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            madsci,
            [
                "workflow",
                "cancel",
                _WF_ID_DEFAULT,
                "--workcell-url",
                "http://localhost:8005/",
            ],
            input="n\n",
        )
        # User declined => abort
        assert result.exit_code != 0

    def test_cancel_confirm(self) -> None:
        wf = _make_workflow(status_kwargs={"cancelled": True})
        with _patch_client_init(), _patch_client("cancel_workflow", wf):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "workflow",
                    "cancel",
                    _WF_ID_DEFAULT,
                    "--workcell-url",
                    "http://localhost:8005/",
                ],
                input="y\n",
            )
            assert result.exit_code == 0
            assert "cancelled" in result.output.lower()


# ---------------------------------------------------------------------------
# workflow retry
# ---------------------------------------------------------------------------


class TestWorkflowRetry:
    """Tests for 'workflow retry'."""

    def test_retry_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["workflow", "retry", "--help"])
        assert result.exit_code == 0
        assert "--from-step" in result.output
        assert "--no-wait" in result.output

    def test_retry_basic(self) -> None:
        wf_query = _make_workflow(
            status_kwargs={"failed": True},
        )
        wf_query.status.current_step_index = 1
        wf_retried = _make_workflow(status_kwargs={"completed": True})

        with (
            _patch_client_init(),
            _patch_client("query_workflow", wf_query),
            _patch_client("retry_workflow", wf_retried),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "workflow",
                    "retry",
                    _WF_ID_DEFAULT,
                    "--workcell-url",
                    "http://localhost:8005/",
                ],
            )
            assert result.exit_code == 0
            assert (
                "retried" in result.output.lower()
                or "completed" in result.output.lower()
            )

    def test_retry_from_step(self) -> None:
        wf = _make_workflow(status_kwargs={"completed": True})
        with _patch_client_init(), _patch_client("retry_workflow", wf):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "workflow",
                    "retry",
                    _WF_ID_DEFAULT,
                    "--from-step",
                    "0",
                    "--workcell-url",
                    "http://localhost:8005/",
                ],
            )
            assert result.exit_code == 0

    def test_retry_no_wait(self) -> None:
        wf = _make_workflow(status_kwargs={"running": True})
        with _patch_client_init(), _patch_client("retry_workflow", wf):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "workflow",
                    "retry",
                    _WF_ID_DEFAULT,
                    "--from-step",
                    "0",
                    "--no-wait",
                    "--workcell-url",
                    "http://localhost:8005/",
                ],
            )
            assert result.exit_code == 0


# ---------------------------------------------------------------------------
# workflow resubmit
# ---------------------------------------------------------------------------


class TestWorkflowResubmit:
    """Tests for 'workflow resubmit'."""

    def test_resubmit_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["workflow", "resubmit", "--help"])
        assert result.exit_code == 0
        assert "--no-wait" in result.output

    def test_resubmit_basic(self) -> None:
        wf = _make_workflow(
            workflow_id=_WF_ID_RESUBMIT,
            status_kwargs={"completed": True},
        )
        with _patch_client_init(), _patch_client("resubmit_workflow", wf):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "workflow",
                    "resubmit",
                    _WF_ID_DEFAULT,
                    "--workcell-url",
                    "http://localhost:8005/",
                ],
            )
            assert result.exit_code == 0
            assert "resubmitted" in result.output.lower()

    def test_resubmit_no_wait(self) -> None:
        wf = _make_workflow(
            workflow_id=_WF_ID_RESUBMIT,
            status_kwargs={"running": True},
        )
        with _patch_client_init(), _patch_client("resubmit_workflow", wf):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "workflow",
                    "resubmit",
                    _WF_ID_DEFAULT,
                    "--no-wait",
                    "--workcell-url",
                    "http://localhost:8005/",
                ],
            )
            assert result.exit_code == 0

    def test_resubmit_json(self) -> None:
        wf = _make_workflow(
            workflow_id=_WF_ID_RESUBMIT,
            status_kwargs={"completed": True},
        )
        with _patch_client_init(), _patch_client("resubmit_workflow", wf):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "--json",
                    "workflow",
                    "resubmit",
                    _WF_ID_DEFAULT,
                    "--workcell-url",
                    "http://localhost:8005/",
                ],
            )
            assert result.exit_code == 0


# ---------------------------------------------------------------------------
# run workflow deprecation
# ---------------------------------------------------------------------------


class TestRunWorkflowDeprecation:
    """Test that 'madsci run workflow' shows deprecation warning."""

    def test_run_workflow_deprecation_notice(self, tmp_path) -> None:
        wf_yaml = tmp_path / "test.workflow.yaml"
        wf_yaml.write_text(
            "name: test\nsteps:\n  - name: s1\n    action: do_it\n    node: n1\n"
        )

        wf = _make_workflow(status_kwargs={"completed": True})
        with (
            _patch_client_init(),
            patch(
                "madsci.client.workcell_client.WorkcellClient.start_workflow",
                return_value=wf,
            ),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "run",
                    "workflow",
                    str(wf_yaml),
                    "--workcell",
                    "http://localhost:8005/",
                ],
            )
            assert result.exit_code == 0
            assert "deprecated" in result.output.lower()
            assert "madsci workflow submit" in result.output


# ---------------------------------------------------------------------------
# CLI smoke test: workflow is registered
# ---------------------------------------------------------------------------


class TestWorkflowRegistered:
    """Test that the workflow command is properly registered."""

    def test_workflow_in_lazy_commands(self) -> None:
        from madsci.client.cli import _LAZY_COMMANDS

        assert "workflow" in _LAZY_COMMANDS

    def test_wf_alias(self) -> None:
        from madsci.client.cli import AliasedGroup

        assert "wf" in AliasedGroup._aliases
        assert AliasedGroup._aliases["wf"] == "workflow"
