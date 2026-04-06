"""Tests for the madsci experiment command group."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import patch

from click.testing import CliRunner
from madsci.client.cli import madsci
from madsci.common.types.experiment_types import (
    Experiment,
    ExperimentDesign,
    ExperimentStatus,
)
from madsci.common.utils import new_ulid_str

# Pre-generate stable ULID strings for tests
_EXP_ID_DEFAULT = new_ulid_str()
_EXP_ID_STARTED = new_ulid_str()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_experiment(
    *,
    experiment_id: str | None = None,
    status: ExperimentStatus = ExperimentStatus.IN_PROGRESS,
    name: str = "test-experiment",
    run_name: str | None = "run_1",
    started_at: datetime | None = None,
    ended_at: datetime | None = None,
) -> Experiment:
    """Build a minimal Experiment for testing."""
    return Experiment(
        experiment_id=experiment_id or _EXP_ID_DEFAULT,
        status=status,
        experiment_design=ExperimentDesign(
            experiment_name=name,
        ),
        run_name=run_name,
        started_at=started_at,
        ended_at=ended_at,
    )


def _patch_client(method_name: str, return_value):
    """Shortcut to patch an ExperimentClient method."""
    return patch(
        f"madsci.client.experiment_client.ExperimentClient.{method_name}",
        return_value=return_value,
    )


def _patch_client_init():
    """Patch ExperimentClient.__init__ to avoid network access."""
    return patch(
        "madsci.client.experiment_client.ExperimentClient.__init__",
        return_value=None,
    )


# ---------------------------------------------------------------------------
# experiment group help
# ---------------------------------------------------------------------------


class TestExperimentGroup:
    """Tests for the experiment command group itself."""

    def test_experiment_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["experiment", "--help"])
        assert result.exit_code == 0
        assert "Manage experiments" in result.output

    def test_experiment_alias(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["exp", "--help"])
        assert result.exit_code == 0
        assert "Manage experiments" in result.output


# ---------------------------------------------------------------------------
# experiment list
# ---------------------------------------------------------------------------


class TestExperimentList:
    """Tests for 'experiment list'."""

    def test_list_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["experiment", "list", "--help"])
        assert result.exit_code == 0
        assert "--count" in result.output
        assert "--status" in result.output

    def test_list_default(self) -> None:
        exps = [_make_experiment()]
        with _patch_client_init(), _patch_client("get_experiments", exps):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "experiment",
                    "list",
                    "--experiment-url",
                    "http://localhost:8002/",
                ],
            )
            assert result.exit_code == 0
            assert "test-experiment" in result.output

    def test_list_json(self) -> None:
        exps = [_make_experiment()]
        with _patch_client_init(), _patch_client("get_experiments", exps):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "--json",
                    "experiment",
                    "list",
                    "--experiment-url",
                    "http://localhost:8002/",
                ],
            )
            assert result.exit_code == 0

    def test_list_empty(self) -> None:
        with _patch_client_init(), _patch_client("get_experiments", []):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "experiment",
                    "list",
                    "--experiment-url",
                    "http://localhost:8002/",
                ],
            )
            assert result.exit_code == 0
            assert "No experiments found" in result.output

    def test_list_status_filter(self) -> None:
        exps = [
            _make_experiment(status=ExperimentStatus.COMPLETED),
            _make_experiment(
                experiment_id=new_ulid_str(), status=ExperimentStatus.FAILED
            ),
        ]
        with _patch_client_init(), _patch_client("get_experiments", exps):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "--json",
                    "experiment",
                    "list",
                    "--status",
                    "completed",
                    "--experiment-url",
                    "http://localhost:8002/",
                ],
            )
            assert result.exit_code == 0
            assert "completed" in result.output
            assert "failed" not in result.output

    def test_list_quiet(self) -> None:
        exps = [_make_experiment()]
        with _patch_client_init(), _patch_client("get_experiments", exps):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "--quiet",
                    "experiment",
                    "list",
                    "--experiment-url",
                    "http://localhost:8002/",
                ],
            )
            # quiet Console suppresses output; just verify no crash
            assert result.exit_code == 0


# ---------------------------------------------------------------------------
# experiment get
# ---------------------------------------------------------------------------


class TestExperimentGet:
    """Tests for 'experiment get'."""

    def test_get_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["experiment", "get", "--help"])
        assert result.exit_code == 0

    def test_get_basic(self) -> None:
        exp = _make_experiment(
            started_at=datetime(2026, 1, 1, 12, 0, 0),
        )
        with _patch_client_init(), _patch_client("get_experiment", exp):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "experiment",
                    "get",
                    _EXP_ID_DEFAULT,
                    "--experiment-url",
                    "http://localhost:8002/",
                ],
            )
            assert result.exit_code == 0
            assert "test-experiment" in result.output

    def test_get_json(self) -> None:
        exp = _make_experiment()
        with _patch_client_init(), _patch_client("get_experiment", exp):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "--json",
                    "experiment",
                    "get",
                    _EXP_ID_DEFAULT,
                    "--experiment-url",
                    "http://localhost:8002/",
                ],
            )
            assert result.exit_code == 0


# ---------------------------------------------------------------------------
# experiment start
# ---------------------------------------------------------------------------


class TestExperimentStart:
    """Tests for 'experiment start'."""

    def test_start_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["experiment", "start", "--help"])
        assert result.exit_code == 0
        assert "--design" in result.output
        assert "--name" in result.output

    def test_start_with_name(self) -> None:
        exp = _make_experiment(experiment_id=_EXP_ID_STARTED)
        with _patch_client_init(), _patch_client("start_experiment", exp):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "experiment",
                    "start",
                    "--name",
                    "My Experiment",
                    "--experiment-url",
                    "http://localhost:8002/",
                ],
            )
            assert result.exit_code == 0
            assert "started" in result.output.lower()

    def test_start_missing_args(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            madsci,
            [
                "experiment",
                "start",
                "--experiment-url",
                "http://localhost:8002/",
            ],
        )
        assert result.exit_code != 0
        assert "Provide --design" in result.output or "Error" in result.output

    def test_start_quiet(self) -> None:
        exp = _make_experiment(experiment_id=_EXP_ID_STARTED)
        with _patch_client_init(), _patch_client("start_experiment", exp):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "--quiet",
                    "experiment",
                    "start",
                    "--name",
                    "Test",
                    "--experiment-url",
                    "http://localhost:8002/",
                ],
            )
            assert result.exit_code == 0


# ---------------------------------------------------------------------------
# experiment run
# ---------------------------------------------------------------------------


class TestExperimentRun:
    """Tests for 'experiment run'."""

    def test_run_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["experiment", "run", "--help"])
        assert result.exit_code == 0

    def test_run_missing_path(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["experiment", "run"])
        assert result.exit_code != 0

    def test_run_nonexistent_file(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["experiment", "run", "/nonexistent/path.py"])
        assert result.exit_code != 0

    def test_run_script(self, tmp_path) -> None:
        script = tmp_path / "test_exp.py"
        script.write_text("print('hello from experiment')\n")

        runner = CliRunner()
        result = runner.invoke(
            madsci,
            ["experiment", "run", str(script)],
        )
        assert result.exit_code == 0
        assert "completed" in result.output.lower()


# ---------------------------------------------------------------------------
# experiment pause / continue / cancel / end
# ---------------------------------------------------------------------------


class TestExperimentPause:
    """Tests for 'experiment pause'."""

    def test_pause_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["experiment", "pause", "--help"])
        assert result.exit_code == 0

    def test_pause_basic(self) -> None:
        exp = _make_experiment(status=ExperimentStatus.PAUSED)
        with _patch_client_init(), _patch_client("pause_experiment", exp):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "experiment",
                    "pause",
                    _EXP_ID_DEFAULT,
                    "--experiment-url",
                    "http://localhost:8002/",
                ],
            )
            assert result.exit_code == 0
            assert "paused" in result.output.lower()


class TestExperimentContinue:
    """Tests for 'experiment continue'."""

    def test_continue_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["experiment", "continue", "--help"])
        assert result.exit_code == 0

    def test_continue_basic(self) -> None:
        exp = _make_experiment(status=ExperimentStatus.IN_PROGRESS)
        with _patch_client_init(), _patch_client("continue_experiment", exp):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "experiment",
                    "continue",
                    _EXP_ID_DEFAULT,
                    "--experiment-url",
                    "http://localhost:8002/",
                ],
            )
            assert result.exit_code == 0
            assert "continued" in result.output.lower()


class TestExperimentCancel:
    """Tests for 'experiment cancel'."""

    def test_cancel_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["experiment", "cancel", "--help"])
        assert result.exit_code == 0
        assert "--yes" in result.output

    def test_cancel_with_yes(self) -> None:
        exp = _make_experiment(status=ExperimentStatus.CANCELLED)
        with _patch_client_init(), _patch_client("cancel_experiment", exp):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "experiment",
                    "cancel",
                    _EXP_ID_DEFAULT,
                    "--yes",
                    "--experiment-url",
                    "http://localhost:8002/",
                ],
            )
            assert result.exit_code == 0
            assert "cancelled" in result.output.lower()

    def test_cancel_abort(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            madsci,
            [
                "experiment",
                "cancel",
                _EXP_ID_DEFAULT,
                "--experiment-url",
                "http://localhost:8002/",
            ],
            input="n\n",
        )
        assert result.exit_code != 0


class TestExperimentEnd:
    """Tests for 'experiment end'."""

    def test_end_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["experiment", "end", "--help"])
        assert result.exit_code == 0
        assert "--status" in result.output

    def test_end_basic(self) -> None:
        exp = _make_experiment(status=ExperimentStatus.COMPLETED)
        with _patch_client_init(), _patch_client("end_experiment", exp):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "experiment",
                    "end",
                    _EXP_ID_DEFAULT,
                    "--experiment-url",
                    "http://localhost:8002/",
                ],
            )
            assert result.exit_code == 0
            assert "ended" in result.output.lower()

    def test_end_with_status(self) -> None:
        exp = _make_experiment(status=ExperimentStatus.FAILED)
        with _patch_client_init(), _patch_client("end_experiment", exp):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "experiment",
                    "end",
                    _EXP_ID_DEFAULT,
                    "--status",
                    "failed",
                    "--experiment-url",
                    "http://localhost:8002/",
                ],
            )
            assert result.exit_code == 0
            assert "ended" in result.output.lower()


# ---------------------------------------------------------------------------
# run experiment deprecation
# ---------------------------------------------------------------------------


class TestRunExperimentDeprecation:
    """Test that 'madsci run experiment' shows deprecation warning."""

    def test_run_experiment_deprecation_notice(self, tmp_path) -> None:
        script = tmp_path / "test_exp.py"
        script.write_text("print('hello')\n")

        runner = CliRunner()
        result = runner.invoke(
            madsci,
            ["run", "experiment", str(script)],
        )
        assert result.exit_code == 0
        assert "deprecated" in result.output.lower()
        assert "madsci experiment run" in result.output


# ---------------------------------------------------------------------------
# CLI registration
# ---------------------------------------------------------------------------


class TestExperimentRegistered:
    """Test that the experiment command is properly registered."""

    def test_experiment_in_lazy_commands(self) -> None:
        from madsci.client.cli import _LAZY_COMMANDS

        assert "experiment" in _LAZY_COMMANDS

    def test_exp_alias(self) -> None:
        from madsci.client.cli import AliasedGroup

        assert "exp" in AliasedGroup._aliases
        assert AliasedGroup._aliases["exp"] == "experiment"
