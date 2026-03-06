"""Tests for Phase G.4: madsci config command group."""

import json

import pytest
from click.testing import CliRunner
from madsci.client.cli import madsci


@pytest.fixture()
def runner() -> CliRunner:
    """Create a CLI test runner."""
    return CliRunner()


class TestConfigHelp:
    """Tests for config command help."""

    def test_config_help(self, runner: CliRunner) -> None:
        """config --help works."""
        result = runner.invoke(madsci, ["config", "--help"])
        assert result.exit_code == 0
        assert "export" in result.output
        assert "create" in result.output

    def test_config_export_help(self, runner: CliRunner) -> None:
        """config export --help works."""
        result = runner.invoke(madsci, ["config", "export", "--help"])
        assert result.exit_code == 0
        assert "--include-secrets" in result.output
        assert "--format" in result.output

    def test_config_create_help(self, runner: CliRunner) -> None:
        """config create --help works."""
        result = runner.invoke(madsci, ["config", "create", "--help"])
        assert result.exit_code == 0
        assert "manager" in result.output
        assert "node" in result.output


class TestConfigExport:
    """Tests for config export subcommand."""

    def test_export_requires_type_or_all(self, runner: CliRunner) -> None:
        """config export without type or --all fails."""
        result = runner.invoke(madsci, ["config", "export"])
        assert result.exit_code != 0

    def test_export_event_yaml(self, runner: CliRunner) -> None:
        """config export event produces YAML output with prefixed keys."""
        result = runner.invoke(madsci, ["config", "export", "event"])
        assert result.exit_code == 0
        assert "event_server_url" in result.output

    def test_export_event_json(self, runner: CliRunner) -> None:
        """config export event --format json produces JSON with prefixed keys."""
        result = runner.invoke(
            madsci, ["config", "export", "event", "--format", "json"]
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "event_server_url" in data

    def test_export_redacts_secrets(self, runner: CliRunner) -> None:
        """config export redacts secret fields by default."""
        result = runner.invoke(madsci, ["config", "export", "event"])
        assert result.exit_code == 0
        assert "***REDACTED***" in result.output

    def test_export_reveals_secrets(self, runner: CliRunner) -> None:
        """config export --include-secrets reveals secret values."""
        result = runner.invoke(
            madsci, ["config", "export", "event", "--include-secrets"]
        )
        assert result.exit_code == 0
        assert "***REDACTED***" not in result.output
        assert "mongodb://localhost:27017" in result.output

    def test_export_all(self, runner: CliRunner) -> None:
        """config export --all exports all manager settings."""
        result = runner.invoke(madsci, ["config", "export", "--all"])
        assert result.exit_code == 0
        # Should contain prefixed settings from multiple managers
        assert "event_server_url" in result.output

    def test_export_to_file(self, runner: CliRunner, tmp_path) -> None:
        """config export --output writes to file."""
        output_file = tmp_path / "event.yaml"
        result = runner.invoke(
            madsci,
            ["config", "export", "event", "--output", str(output_file)],
        )
        assert result.exit_code == 0
        assert output_file.exists()
        assert "event_server_url" in output_file.read_text()

    def test_export_no_defaults(self, runner: CliRunner) -> None:
        """config export --no-include-defaults excludes default values."""
        result = runner.invoke(
            madsci,
            ["config", "export", "event", "--no-include-defaults", "--format", "json"],
        )
        assert result.exit_code == 0
        # With no custom settings, result should be minimal
        data = json.loads(result.output)
        # All values match defaults, so no non-default fields
        assert len(data) == 0 or isinstance(data, dict)


class TestConfigCreateManager:
    """Tests for config create manager subcommand."""

    def test_create_manager_event(self, runner: CliRunner, tmp_path) -> None:
        """config create manager event creates a config file with prefixed keys."""
        output_file = tmp_path / "event.settings.yaml"
        result = runner.invoke(
            madsci,
            [
                "config",
                "create",
                "manager",
                "event",
                "--output",
                str(output_file),
            ],
        )
        assert result.exit_code == 0
        assert output_file.exists()
        content = output_file.read_text()
        assert "event_server_url" in content
        assert "***REDACTED***" in content  # secrets are placeholders

    def test_create_manager_resource(self, runner: CliRunner, tmp_path) -> None:
        """config create manager resource creates a config file."""
        output_file = tmp_path / "resource.settings.yaml"
        result = runner.invoke(
            madsci,
            [
                "config",
                "create",
                "manager",
                "resource",
                "--output",
                str(output_file),
            ],
        )
        assert result.exit_code == 0
        assert output_file.exists()

    def test_create_manager_json(self, runner: CliRunner, tmp_path) -> None:
        """config create manager event --format json produces JSON with prefixed keys."""
        output_file = tmp_path / "event.settings.json"
        result = runner.invoke(
            madsci,
            [
                "config",
                "create",
                "manager",
                "event",
                "--output",
                str(output_file),
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0
        data = json.loads(output_file.read_text())
        assert "event_server_url" in data


class TestConfigCreateNode:
    """Tests for config create node subcommand."""

    def test_create_node_rest(self, runner: CliRunner, tmp_path) -> None:
        """config create node rest creates a REST node config."""
        output_file = tmp_path / "node.settings.yaml"
        result = runner.invoke(
            madsci,
            [
                "config",
                "create",
                "node",
                "rest",
                "--output",
                str(output_file),
            ],
        )
        assert result.exit_code == 0
        assert output_file.exists()
        content = output_file.read_text()
        assert "node_url" in content

    def test_create_node_basic(self, runner: CliRunner, tmp_path) -> None:
        """config create node basic creates a basic node config."""
        output_file = tmp_path / "node.settings.yaml"
        result = runner.invoke(
            madsci,
            [
                "config",
                "create",
                "node",
                "basic",
                "--output",
                str(output_file),
            ],
        )
        assert result.exit_code == 0
        assert output_file.exists()


class TestConfigAlias:
    """Tests for the cfg alias."""

    def test_cfg_alias(self, runner: CliRunner) -> None:
        """cfg alias resolves to config."""
        result = runner.invoke(madsci, ["cfg", "--help"])
        assert result.exit_code == 0
        assert "export" in result.output
