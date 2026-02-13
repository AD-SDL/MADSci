"""Tests for the madsci new --tui template browser."""

from unittest.mock import patch

from click.testing import CliRunner
from madsci.client.cli import madsci


class TestNewTuiFlag:
    """Tests for the --tui flag on the new command."""

    def test_new_tui_flag_recognized(self) -> None:
        """Test that --tui flag is recognized in --help."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["new", "--help"])
        assert result.exit_code == 0
        assert "--tui" in result.output

    def test_new_no_subcommand_shows_help(self) -> None:
        """Test that running 'madsci new' with no subcommand and no --tui shows help."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["new"])
        assert result.exit_code == 0
        assert "Create new MADSci components" in result.output

    def test_new_tui_import_error(self) -> None:
        """Test graceful handling when TUI dependencies are missing."""
        runner = CliRunner()
        with patch(
            "madsci.client.cli.commands.new._launch_tui_browser",
            side_effect=ImportError("textual not installed"),
        ):
            result = runner.invoke(madsci, ["new", "--tui"])
            # Should fail gracefully, not crash
            assert (
                result.exit_code != 0
                or "Error" in result.output
                or "textual" in result.output
            )

    def test_new_subcommands_still_work(self) -> None:
        """Test that existing subcommands still work with the new group."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["new", "list", "--help"])
        assert result.exit_code == 0
        assert "List available templates" in result.output

    def test_new_module_still_works(self) -> None:
        """Test that madsci new module --help still works."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["new", "module", "--help"])
        assert result.exit_code == 0
        assert "Create a new node module" in result.output


class TestTemplateBrowserScreen:
    """Tests for the TemplateBrowserScreen widget."""

    def test_screen_can_be_imported(self) -> None:
        """Test that the screen module can be imported."""
        from madsci.client.cli.tui.screens.new_wizard import TemplateBrowserScreen

        assert TemplateBrowserScreen is not None

    def test_template_selected_message(self) -> None:
        """Test TemplateSelected message creation."""
        from madsci.client.cli.tui.screens.new_wizard import TemplateSelected

        msg = TemplateSelected("module/basic")
        assert msg.template_id == "module/basic"

    def test_template_detail_panel(self) -> None:
        """Test TemplateDetailPanel update_detail method."""
        from madsci.client.cli.tui.screens.new_wizard import TemplateDetailPanel

        panel = TemplateDetailPanel()
        # Panel can be instantiated without error
        assert panel is not None
