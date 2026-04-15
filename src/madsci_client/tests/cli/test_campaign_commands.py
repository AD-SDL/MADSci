"""Tests for the madsci campaign command group."""

from __future__ import annotations

from unittest.mock import patch

from click.testing import CliRunner
from madsci.client.cli import madsci
from madsci.common.types.experiment_types import ExperimentalCampaign
from madsci.common.utils import new_ulid_str

_CAMPAIGN_ID = new_ulid_str()


def _make_campaign(
    *,
    campaign_id: str | None = None,
    campaign_name: str = "Test Campaign",
) -> ExperimentalCampaign:
    """Build a minimal ExperimentalCampaign for testing."""
    return ExperimentalCampaign(
        campaign_id=campaign_id or _CAMPAIGN_ID,
        campaign_name=campaign_name,
        experiment_ids=[],
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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
# campaign group help
# ---------------------------------------------------------------------------


class TestCampaignGroup:
    """Tests for the campaign command group itself."""

    def test_campaign_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["campaign", "--help"])
        assert result.exit_code == 0
        assert "Manage experimental campaigns" in result.output

    def test_campaign_alias(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["camp", "--help"])
        assert result.exit_code == 0
        assert "Manage experimental campaigns" in result.output


# ---------------------------------------------------------------------------
# campaign create
# ---------------------------------------------------------------------------


class TestCampaignCreate:
    """Tests for 'campaign create'."""

    def test_create_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["campaign", "create", "--help"])
        assert result.exit_code == 0
        assert "--name" in result.output
        assert "--desc" in result.output

    def test_create_basic(self) -> None:
        mock_result = _make_campaign(campaign_name="My Campaign")
        with _patch_client_init(), _patch_client("register_campaign", mock_result):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "campaign",
                    "create",
                    "--name",
                    "My Campaign",
                    "--experiment-url",
                    "http://localhost:8002/",
                ],
            )
            assert result.exit_code == 0
            assert "created" in result.output.lower()

    def test_create_with_desc(self) -> None:
        mock_result = _make_campaign(campaign_name="Test")
        with _patch_client_init(), _patch_client("register_campaign", mock_result):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "campaign",
                    "create",
                    "--name",
                    "Test",
                    "--desc",
                    "A test campaign",
                    "--experiment-url",
                    "http://localhost:8002/",
                ],
            )
            assert result.exit_code == 0

    def test_create_json(self) -> None:
        mock_result = _make_campaign(campaign_name="JSON Test")
        with _patch_client_init(), _patch_client("register_campaign", mock_result):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "--json",
                    "campaign",
                    "create",
                    "--name",
                    "JSON Test",
                    "--experiment-url",
                    "http://localhost:8002/",
                ],
            )
            assert result.exit_code == 0

    def test_create_missing_name(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            madsci,
            [
                "campaign",
                "create",
                "--experiment-url",
                "http://localhost:8002/",
            ],
        )
        assert result.exit_code != 0

    def test_create_quiet(self) -> None:
        mock_result = _make_campaign(campaign_name="Quiet")
        with _patch_client_init(), _patch_client("register_campaign", mock_result):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "--quiet",
                    "campaign",
                    "create",
                    "--name",
                    "Quiet",
                    "--experiment-url",
                    "http://localhost:8002/",
                ],
            )
            assert result.exit_code == 0


# ---------------------------------------------------------------------------
# campaign list
# ---------------------------------------------------------------------------


class TestCampaignList:
    """Tests for 'campaign list'."""

    def test_list_campaigns_help(self, cli_runner=None) -> None:
        """Verify campaign list --help works."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["campaign", "list", "--help"])
        assert result.exit_code == 0
        assert "List all campaigns" in result.output

    def test_list_campaigns_empty(self) -> None:
        with _patch_client_init(), _patch_client("get_campaigns", []):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "campaign",
                    "list",
                    "--experiment-url",
                    "http://localhost:8002/",
                ],
            )
            assert result.exit_code == 0
            assert "No campaigns found" in result.output

    def test_list_campaigns_with_results(self) -> None:
        mock_campaigns = [
            _make_campaign(campaign_name="Campaign Alpha"),
        ]
        with _patch_client_init(), _patch_client("get_campaigns", mock_campaigns):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "campaign",
                    "list",
                    "--experiment-url",
                    "http://localhost:8002/",
                ],
            )
            assert result.exit_code == 0
            assert "Campaign Alpha" in result.output

    def test_list_campaigns_json(self) -> None:
        mock_campaigns = [
            _make_campaign(campaign_name="Campaign Beta"),
        ]
        with _patch_client_init(), _patch_client("get_campaigns", mock_campaigns):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "--json",
                    "campaign",
                    "list",
                    "--experiment-url",
                    "http://localhost:8002/",
                ],
            )
            assert result.exit_code == 0

    def test_list_campaigns_quiet(self) -> None:
        mock_campaigns = [
            _make_campaign(campaign_name="Campaign Gamma"),
        ]
        with _patch_client_init(), _patch_client("get_campaigns", mock_campaigns):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "--quiet",
                    "campaign",
                    "list",
                    "--experiment-url",
                    "http://localhost:8002/",
                ],
            )
            # quiet Console suppresses output; just verify no crash
            assert result.exit_code == 0


# ---------------------------------------------------------------------------
# campaign get
# ---------------------------------------------------------------------------


class TestCampaignGet:
    """Tests for 'campaign get'."""

    def test_get_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["campaign", "get", "--help"])
        assert result.exit_code == 0

    def test_get_basic(self) -> None:
        mock_result = _make_campaign(campaign_name="Test Campaign")
        with _patch_client_init(), _patch_client("get_campaign", mock_result):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "campaign",
                    "get",
                    _CAMPAIGN_ID,
                    "--experiment-url",
                    "http://localhost:8002/",
                ],
            )
            assert result.exit_code == 0
            assert "Test Campaign" in result.output

    def test_get_json(self) -> None:
        mock_result = _make_campaign(campaign_name="JSON")
        with _patch_client_init(), _patch_client("get_campaign", mock_result):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "--json",
                    "campaign",
                    "get",
                    _CAMPAIGN_ID,
                    "--experiment-url",
                    "http://localhost:8002/",
                ],
            )
            assert result.exit_code == 0

    def test_get_missing_arg(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["campaign", "get"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# CLI registration
# ---------------------------------------------------------------------------


class TestCampaignRegistered:
    """Test that the campaign command is properly registered."""

    def test_campaign_in_lazy_commands(self) -> None:
        from madsci.client.cli import _LAZY_COMMANDS

        assert "campaign" in _LAZY_COMMANDS

    def test_camp_alias(self) -> None:
        from madsci.client.cli import AliasedGroup

        assert "camp" in AliasedGroup._aliases
        assert AliasedGroup._aliases["camp"] == "campaign"
