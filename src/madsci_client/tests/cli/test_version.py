"""Tests for the madsci version command."""

import json

from click.testing import CliRunner
from madsci.client.cli import madsci


class TestVersionCommand:
    """Tests for the version command."""

    def test_version_basic(self) -> None:
        """Test basic version output."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["version"])

        assert result.exit_code == 0
        assert "MADSci" in result.output

    def test_version_json(self) -> None:
        """Test JSON output format."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["version", "--json"])

        assert result.exit_code == 0

        # Parse JSON output
        data = json.loads(result.output)
        assert "version" in data
        assert "packages" in data
        assert "system" in data

    def test_version_shows_packages(self) -> None:
        """Test that installed packages are shown."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["version"])

        assert result.exit_code == 0
        # At minimum, madsci.common should be installed
        assert "madsci" in result.output.lower()

    def test_version_shows_python(self) -> None:
        """Test that Python version is shown."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["version"])

        assert result.exit_code == 0
        assert "Python" in result.output or "python" in result.output.lower()
