"""Tests for the madsci migrate foss CLI command."""

from unittest.mock import patch

from click.testing import CliRunner
from madsci.client.cli import madsci
from madsci.common.foss_migration import (
    FossMigrationReport,
    FossMigrationStepResult,
)


class TestMigrateFossCommand:
    """Tests for the migrate foss subcommand."""

    def test_foss_appears_in_migrate_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["migrate", "--help"])
        assert result.exit_code == 0
        assert "foss" in result.output

    def test_foss_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["migrate", "foss", "--help"])
        assert result.exit_code == 0
        assert "--dry-run" in result.output
        assert "--apply" in result.output
        assert "--step" in result.output
        assert "--skip-backup" in result.output
        assert "--skip-docker" in result.output

    def test_foss_no_mode_specified(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["migrate", "foss"])
        assert "Specify --dry-run or --apply" in result.output

    def test_foss_dry_run(self) -> None:
        runner = CliRunner()
        with patch("shutil.which", return_value="/usr/bin/tool"):
            result = runner.invoke(madsci, ["migrate", "foss", "--dry-run"])
        assert result.exit_code == 0
        assert "Migration Plan" in result.output
        assert "Dry run" in result.output

    def test_foss_dry_run_missing_tools(self) -> None:
        runner = CliRunner()
        with patch("shutil.which", return_value=None):
            result = runner.invoke(madsci, ["migrate", "foss", "--dry-run"])
        assert result.exit_code == 0
        assert "Not found" in result.output

    def test_foss_apply_with_mocked_migration(self) -> None:
        runner = CliRunner()
        ok = FossMigrationStepResult(
            step="test", success=True, message="ok", duration_seconds=0.1
        )
        report = FossMigrationReport(steps=[ok])

        with patch(
            "madsci.common.foss_migration.FossMigrationTool.run_full_migration",
            return_value=report,
        ):
            result = runner.invoke(
                madsci,
                ["migrate", "foss", "--apply", "--skip-backup", "--skip-docker"],
            )
        assert result.exit_code == 0
        assert "Migration Results" in result.output

    def test_foss_step_filter(self) -> None:
        runner = CliRunner()
        ok = FossMigrationStepResult(
            step="redis", success=True, message="ok", duration_seconds=0.1
        )
        report = FossMigrationReport(steps=[ok])

        with patch(
            "madsci.common.foss_migration.FossMigrationTool.run_full_migration",
            return_value=report,
        ) as mock_run:
            result = runner.invoke(
                madsci,
                [
                    "migrate",
                    "foss",
                    "--apply",
                    "--step",
                    "redis",
                    "--skip-backup",
                    "--skip-docker",
                ],
            )
        assert result.exit_code == 0
        mock_run.assert_called_once_with(
            skip_backup=True,
            skip_docker=True,
            steps=["redis"],
        )

    def test_foss_apply_with_failure(self) -> None:
        runner = CliRunner()
        fail = FossMigrationStepResult(
            step="migrate_postgresql",
            success=False,
            message="Failed",
            error="connection refused",
            duration_seconds=0.5,
        )
        report = FossMigrationReport(steps=[fail])

        with patch(
            "madsci.common.foss_migration.FossMigrationTool.run_full_migration",
            return_value=report,
        ):
            result = runner.invoke(
                madsci,
                ["migrate", "foss", "--apply", "--skip-backup", "--skip-docker"],
            )
        # Should exit with error code
        assert result.exit_code != 0
        assert "errors" in result.output.lower()

    def test_foss_invalid_step_choice(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            madsci,
            ["migrate", "foss", "--apply", "--step", "invalid-step"],
        )
        assert result.exit_code != 0
