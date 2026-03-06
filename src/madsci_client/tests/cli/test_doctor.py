"""Tests for the madsci doctor command."""

import json

from click.testing import CliRunner
from madsci.client.cli import madsci


class TestDoctorCommand:
    """Tests for the doctor command."""

    def test_doctor_basic(self) -> None:
        """Test basic doctor output."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["doctor"])

        # Doctor may fail if checks fail, but should run
        assert result.exit_code in (0, 1)
        assert (
            "MADSci System Diagnostics" in result.output
            or "passed" in result.output.lower()
        )

    def test_doctor_json(self) -> None:
        """Test JSON output format."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["doctor", "--json"])

        # Doctor may fail if checks fail, but JSON should be valid
        assert result.exit_code in (0, 1)

        # Parse JSON output
        data = json.loads(result.output)
        assert "summary" in data
        assert "checks" in data
        assert "passed" in data["summary"]
        assert "failed" in data["summary"]

    def test_doctor_check_python(self) -> None:
        """Test running only Python checks."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["doctor", "--check", "python"])

        assert result.exit_code in (0, 1)
        assert "Python" in result.output

    def test_doctor_check_docker(self) -> None:
        """Test running only Docker checks."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["doctor", "--check", "docker"])

        assert result.exit_code in (0, 1)
        # Docker check should be present even if Docker is not installed
        assert "Docker" in result.output or "docker" in result.output.lower()

    def test_doctor_check_ports(self) -> None:
        """Test running only port checks."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["doctor", "--check", "ports"])

        assert result.exit_code in (0, 1)
        # Should mention ports
        assert "Port" in result.output or "port" in result.output.lower()
