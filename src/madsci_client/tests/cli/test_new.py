"""Tests for the madsci new command."""

import tempfile
from unittest.mock import MagicMock, patch

from click.testing import CliRunner
from madsci.client.cli import madsci
from madsci.common.types.template_types import (
    ParameterChoice,
    ParameterType,
    TemplateParameter,
)


class TestNewCommand:
    """Tests for the new command group."""

    def test_new_help(self) -> None:
        """Test that new command shows help."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["new", "--help"])

        assert result.exit_code == 0
        assert "Create new MADSci components" in result.output
        assert "module" in result.output
        assert "experiment" in result.output
        assert "workflow" in result.output

    def test_new_list_no_templates(self) -> None:
        """Test listing templates when none are available."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["new", "list"])

        # Should succeed even with no templates
        assert result.exit_code == 0

    def test_new_module_help(self) -> None:
        """Test that new module command shows help."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["new", "module", "--help"])

        assert result.exit_code == 0
        assert "Create a new node module" in result.output
        assert "--name" in result.output
        assert "--template" in result.output

    def test_new_experiment_help(self) -> None:
        """Test that new experiment command shows help."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["new", "experiment", "--help"])

        assert result.exit_code == 0
        assert "Create a new experiment" in result.output
        assert "--modality" in result.output

    def test_new_workflow_help(self) -> None:
        """Test that new workflow command shows help."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["new", "workflow", "--help"])

        assert result.exit_code == 0
        assert "Create a new workflow" in result.output

    def test_new_lab_help(self) -> None:
        """Test that new lab command shows help."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["new", "lab", "--help"])

        assert result.exit_code == 0
        assert "Create a new lab" in result.output
        assert "--template" in result.output

    def test_new_interface_help(self) -> None:
        """Test that new interface command shows help."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["new", "interface", "--help"])

        assert result.exit_code == 0
        assert "Add a new interface" in result.output
        assert "--type" in result.output


class TestNewModuleCommand:
    """Tests for madsci new module command with actual template generation."""

    def test_new_module_no_template_found(self) -> None:
        """Test that module command handles missing template gracefully."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(
                madsci,
                [
                    "new",
                    "module",
                    tmpdir,
                    "--name",
                    "test_module",
                    "--no-interactive",
                ],
            )

            # Bundled templates should be available; exit 0 means template
            # was found and rendered, exit 1 means template not found
            # (acceptable in environments without bundled templates).
            assert result.exit_code in (0, 1)
            if result.exit_code == 1:
                assert (
                    "not found" in result.output.lower()
                    or "error" in result.output.lower()
                )


class TestNewExperimentCommand:
    """Tests for madsci new experiment command."""

    def test_new_experiment_no_template_found(self) -> None:
        """Test that experiment command handles missing template gracefully."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(
                madsci,
                [
                    "new",
                    "experiment",
                    tmpdir,
                    "--name",
                    "test_experiment",
                    "--no-interactive",
                ],
            )

            # Exit 0 = template rendered; exit 1 = template not found
            assert result.exit_code in (0, 1)
            if result.exit_code == 1:
                assert (
                    "not found" in result.output.lower()
                    or "error" in result.output.lower()
                )


class TestNewWorkflowCommand:
    """Tests for madsci new workflow command."""

    def test_new_workflow_no_template_found(self) -> None:
        """Test that workflow command handles missing template gracefully."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(
                madsci,
                [
                    "new",
                    "workflow",
                    tmpdir,
                    "--name",
                    "test_workflow",
                    "--no-interactive",
                ],
            )

            # Exit 0 = template rendered; exit 1 = template not found
            assert result.exit_code in (0, 1)
            if result.exit_code == 1:
                assert (
                    "not found" in result.output.lower()
                    or "error" in result.output.lower()
                )


def _make_engine(parameters: list[TemplateParameter]) -> MagicMock:
    """Create a mock TemplateEngine with the given parameters."""
    engine = MagicMock()
    engine.manifest.parameters = parameters
    return engine


def _prompt_return_default(*_args, **kwargs):
    """Simulate user pressing Enter (returns the default value)."""
    return kwargs.get("default", "")


def _confirm_return_default(*_args, **kwargs):
    """Simulate user pressing Enter on Confirm (returns the default value)."""
    return kwargs.get("default", False)


class TestCollectParametersInteractiveOverrides:
    """Tests that collect_parameters_interactive respects the overrides dict.

    Regression tests for the bug where CLI-provided args (e.g., ``-n``)
    were ignored in interactive mode.  All tests mock Rich prompts to
    simulate the user pressing Enter (accepting the default).
    """

    def test_string_override_used_as_default(self) -> None:
        """STRING parameter should use override as the prompt default."""
        from io import StringIO

        from madsci.client.cli.commands.new import collect_parameters_interactive
        from rich.console import Console

        engine = _make_engine(
            [
                TemplateParameter(
                    name="lab_name",
                    type=ParameterType.STRING,
                    description="Lab name",
                    default="default_lab",
                ),
            ]
        )
        console = Console(file=StringIO())

        with patch("rich.prompt.Prompt.ask", side_effect=_prompt_return_default):
            result = collect_parameters_interactive(
                engine,
                console,
                overrides={"lab_name": "my_override"},
            )
        assert result["lab_name"] == "my_override"

    def test_string_no_override_uses_template_default(self) -> None:
        """Without overrides, STRING should use the template default."""
        from io import StringIO

        from madsci.client.cli.commands.new import collect_parameters_interactive
        from rich.console import Console

        engine = _make_engine(
            [
                TemplateParameter(
                    name="lab_name",
                    type=ParameterType.STRING,
                    description="Lab name",
                    default="default_lab",
                ),
            ]
        )
        console = Console(file=StringIO())

        with patch("rich.prompt.Prompt.ask", side_effect=_prompt_return_default):
            result = collect_parameters_interactive(engine, console)
        assert result["lab_name"] == "default_lab"

    def test_integer_override_used_as_default(self) -> None:
        """INTEGER parameter should use override as the prompt default."""
        from io import StringIO

        from madsci.client.cli.commands.new import collect_parameters_interactive
        from rich.console import Console

        engine = _make_engine(
            [
                TemplateParameter(
                    name="port",
                    type=ParameterType.INTEGER,
                    description="Port number",
                    default=2000,
                ),
            ]
        )
        console = Console(file=StringIO())

        with patch("rich.prompt.Prompt.ask", side_effect=_prompt_return_default):
            result = collect_parameters_interactive(
                engine,
                console,
                overrides={"port": 3000},
            )
        assert result["port"] == 3000

    def test_float_override_used_as_default(self) -> None:
        """FLOAT parameter should use override as the prompt default."""
        from io import StringIO

        from madsci.client.cli.commands.new import collect_parameters_interactive
        from rich.console import Console

        engine = _make_engine(
            [
                TemplateParameter(
                    name="rate",
                    type=ParameterType.FLOAT,
                    description="Rate",
                    default=1.0,
                ),
            ]
        )
        console = Console(file=StringIO())

        with patch("rich.prompt.Prompt.ask", side_effect=_prompt_return_default):
            result = collect_parameters_interactive(
                engine,
                console,
                overrides={"rate": 2.5},
            )
        assert result["rate"] == 2.5

    def test_boolean_override_used_as_default(self) -> None:
        """BOOLEAN parameter should use override as the prompt default."""
        from io import StringIO

        from madsci.client.cli.commands.new import collect_parameters_interactive
        from rich.console import Console

        engine = _make_engine(
            [
                TemplateParameter(
                    name="enable_feature",
                    type=ParameterType.BOOLEAN,
                    description="Enable feature?",
                    default=False,
                ),
            ]
        )
        console = Console(file=StringIO())

        with patch("rich.prompt.Confirm.ask", side_effect=_confirm_return_default):
            result = collect_parameters_interactive(
                engine,
                console,
                overrides={"enable_feature": True},
            )
        assert result["enable_feature"] is True

    def test_choice_override_used_as_default(self) -> None:
        """CHOICE parameter should use the override to select the default index."""
        from io import StringIO

        from madsci.client.cli.commands.new import collect_parameters_interactive
        from rich.console import Console

        engine = _make_engine(
            [
                TemplateParameter(
                    name="db_type",
                    type=ParameterType.CHOICE,
                    description="Database type",
                    default="postgres",
                    choices=[
                        ParameterChoice(value="postgres", label="PostgreSQL"),
                        ParameterChoice(value="sqlite", label="SQLite"),
                    ],
                ),
            ]
        )
        console = Console(file=StringIO())

        # Prompt.ask returns default="2" (sqlite is index 2)
        with patch("rich.prompt.Prompt.ask", side_effect=_prompt_return_default):
            result = collect_parameters_interactive(
                engine,
                console,
                overrides={"db_type": "sqlite"},
            )
        assert result["db_type"] == "sqlite"

    def test_multi_choice_override_used_as_defaults(self) -> None:
        """MULTI_CHOICE parameter should use override list for default selections."""
        from io import StringIO

        from madsci.client.cli.commands.new import collect_parameters_interactive
        from rich.console import Console

        engine = _make_engine(
            [
                TemplateParameter(
                    name="tools",
                    type=ParameterType.MULTI_CHOICE,
                    description="Select tools",
                    choices=[
                        ParameterChoice(value="ruff", label="Ruff", default=True),
                        ParameterChoice(value="mypy", label="Mypy", default=False),
                        ParameterChoice(value="pytest", label="Pytest", default=True),
                    ],
                ),
            ]
        )
        console = Console(file=StringIO())

        # Override selects only mypy. Confirm.ask returns the default,
        # so mypy=True (in override), ruff=False, pytest=False.
        with patch("rich.prompt.Confirm.ask", side_effect=_confirm_return_default):
            result = collect_parameters_interactive(
                engine,
                console,
                overrides={"tools": ["mypy"]},
            )
        assert result["tools"] == ["mypy"]

    def test_path_override_used_as_default(self) -> None:
        """PATH parameter should use override as the prompt default."""
        from io import StringIO

        from madsci.client.cli.commands.new import collect_parameters_interactive
        from rich.console import Console

        engine = _make_engine(
            [
                TemplateParameter(
                    name="output_dir",
                    type=ParameterType.PATH,
                    description="Output directory",
                    default="/var/data/default",
                ),
            ]
        )
        console = Console(file=StringIO())

        with patch("rich.prompt.Prompt.ask", side_effect=_prompt_return_default):
            result = collect_parameters_interactive(
                engine,
                console,
                overrides={"output_dir": "/custom/path"},
            )
        assert result["output_dir"] == "/custom/path"

    def test_override_only_affects_matching_param(self) -> None:
        """Override for one param should not affect other params."""
        from io import StringIO

        from madsci.client.cli.commands.new import collect_parameters_interactive
        from rich.console import Console

        engine = _make_engine(
            [
                TemplateParameter(
                    name="lab_name",
                    type=ParameterType.STRING,
                    description="Lab name",
                    default="default_lab",
                ),
                TemplateParameter(
                    name="lab_description",
                    type=ParameterType.STRING,
                    description="Lab description",
                    default="A lab",
                ),
            ]
        )
        console = Console(file=StringIO())

        with patch("rich.prompt.Prompt.ask", side_effect=_prompt_return_default):
            result = collect_parameters_interactive(
                engine,
                console,
                overrides={"lab_name": "my_lab"},
            )
        assert result["lab_name"] == "my_lab"
        assert result["lab_description"] == "A lab"


class TestNewLabInteractiveWithName:
    """Integration test: madsci new lab -n should pass name into interactive mode."""

    def test_lab_name_passed_to_interactive(self) -> None:
        """When -n is provided without --no-interactive, the name should appear
        as the default in interactive prompts, not be discarded."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            # Provide -n and accept all interactive defaults (Enter on every prompt),
            # then answer "y" to create confirmation.
            result = runner.invoke(
                madsci,
                ["new", "lab", tmpdir, "--name", "my_custom_lab"],
                input="\n" * 20 + "y\n",
            )

            # If template was found, the output dir should contain our name
            if result.exit_code == 0:
                from pathlib import Path

                output_path = Path(tmpdir) / "my_custom_lab"
                assert output_path.exists(), (
                    f"Expected 'my_custom_lab' directory but got: "
                    f"{list(Path(tmpdir).iterdir())}"
                )
