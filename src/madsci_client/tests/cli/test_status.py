"""Tests for the madsci status command."""

import json

from click.testing import CliRunner
from madsci.client.cli import madsci


class TestStatusCommand:
    """Tests for the status command."""

    def test_status_basic(self) -> None:
        """Test basic status output."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["status"])

        # Status should always succeed (it reports offline services)
        assert result.exit_code == 0
        # Should show something about services
        assert "status" in result.output.lower() or "service" in result.output.lower()

    def test_status_json(self) -> None:
        """Test JSON output format via the global --json flag."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["--json", "status"])

        assert result.exit_code == 0

        # Parse JSON output
        data = json.loads(result.output)
        assert "services" in data
        assert "summary" in data
        assert isinstance(data["services"], list)

    def test_status_specific_service(self) -> None:
        """Test status for a specific service."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["status", "lab_manager"])

        assert result.exit_code == 0
        assert "lab_manager" in result.output

    def test_status_timeout(self) -> None:
        """Test status with custom timeout."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["status", "--timeout", "1"])

        # Should complete (may show services as offline)
        assert result.exit_code == 0
