"""Tests for E2E test runner."""

from pathlib import Path

import pytest
from madsci.common.testing.runner import E2ETestRunner
from madsci.common.testing.types import (
    E2ETestCleanup,
    E2ETestDefinition,
    E2ETestStep,
    TestMode,
    ValidationConfig,
    ValidationType,
)


class TestE2ETestRunner:
    """Tests for E2ETestRunner."""

    @pytest.fixture
    def runner(self, tmp_path: Path) -> E2ETestRunner:
        """Create a test runner with temp directory."""
        return E2ETestRunner(
            working_dir=tmp_path,
            verbose=False,
        )

    def test_simple_command_execution(self, runner: E2ETestRunner):
        """Test basic command execution."""
        test_def = E2ETestDefinition(
            name="Simple Echo Test",
            steps=[
                E2ETestStep(
                    name="Echo hello",
                    command="echo hello",
                    validations=[
                        ValidationConfig(
                            type=ValidationType.EXIT_CODE,
                            expected=0,
                        ),
                        ValidationConfig(
                            type=ValidationType.OUTPUT_CONTAINS,
                            pattern="hello",
                        ),
                    ],
                ),
            ],
        )

        result = runner.run(test_def)

        assert result.passed is True
        assert len(result.step_results) == 1
        assert result.step_results[0].passed is True

    def test_failing_command(self, runner: E2ETestRunner):
        """Test that failing command is detected."""
        test_def = E2ETestDefinition(
            name="Failing Command Test",
            steps=[
                E2ETestStep(
                    name="Fail command",
                    command="exit 1",
                    validations=[
                        ValidationConfig(
                            type=ValidationType.EXIT_CODE,
                            expected=0,
                        ),
                    ],
                ),
            ],
        )

        result = runner.run(test_def)

        assert result.passed is False
        assert result.step_results[0].passed is False

    def test_file_creation_validation(self, runner: E2ETestRunner):
        """Test file creation is validated."""
        test_def = E2ETestDefinition(
            name="File Creation Test",
            steps=[
                E2ETestStep(
                    name="Create file",
                    command="echo content > testfile.txt",
                    validations=[
                        ValidationConfig(
                            type=ValidationType.FILE_EXISTS,
                            path="testfile.txt",
                        ),
                        ValidationConfig(
                            type=ValidationType.FILE_CONTAINS,
                            path="testfile.txt",
                            pattern="content",
                        ),
                    ],
                ),
            ],
        )

        result = runner.run(test_def)

        assert result.passed is True
        assert all(v.passed for v in result.step_results[0].validation_results)

    def test_step_skip_condition(self, runner: E2ETestRunner):
        """Test step skip condition."""
        test_def = E2ETestDefinition(
            name="Skip Test",
            steps=[
                E2ETestStep(
                    name="Skipped step",
                    command="echo should not run",
                    skip_if="True",
                ),
            ],
        )

        result = runner.run(test_def)

        assert result.passed is True
        assert result.step_results[0].skipped is True

    def test_continue_on_error(self, runner: E2ETestRunner):
        """Test continue_on_error flag."""
        test_def = E2ETestDefinition(
            name="Continue On Error Test",
            steps=[
                E2ETestStep(
                    name="Failing step",
                    command="exit 1",
                    continue_on_error=True,
                    validations=[
                        ValidationConfig(
                            type=ValidationType.EXIT_CODE,
                            expected=0,
                        ),
                    ],
                ),
                E2ETestStep(
                    name="Next step",
                    command="echo second",
                    validations=[
                        ValidationConfig(
                            type=ValidationType.EXIT_CODE,
                            expected=0,
                        ),
                    ],
                ),
            ],
        )

        result = runner.run(test_def)

        # Overall test fails but both steps ran
        assert result.passed is False
        assert len(result.step_results) == 2
        assert result.step_results[0].passed is False
        assert result.step_results[1].passed is True

    def test_setup_steps(self, runner: E2ETestRunner):
        """Test setup steps are run before main steps."""
        test_def = E2ETestDefinition(
            name="Setup Test",
            setup=[
                E2ETestStep(
                    name="Setup step",
                    command="echo setup > setup.txt",
                ),
            ],
            steps=[
                E2ETestStep(
                    name="Main step",
                    validations=[
                        ValidationConfig(
                            type=ValidationType.FILE_EXISTS,
                            path="setup.txt",
                        ),
                    ],
                ),
            ],
        )

        result = runner.run(test_def)

        assert result.passed is True
        assert len(result.setup_results) == 1
        assert result.setup_results[0].passed is True

    def test_cleanup_runs_on_success(self, runner: E2ETestRunner):
        """Test cleanup runs after successful test."""
        test_def = E2ETestDefinition(
            name="Cleanup Test",
            steps=[
                E2ETestStep(
                    name="Create file",
                    command="echo content > cleanup_test.txt",
                ),
            ],
            cleanup=E2ETestCleanup(
                files=["cleanup_test.txt"],
            ),
        )

        result = runner.run(test_def)

        assert result.passed is True
        assert result.cleanup_executed is True
        # File should be cleaned up
        assert not (runner.working_dir / "cleanup_test.txt").exists()

    def test_cleanup_runs_on_failure(self, runner: E2ETestRunner):
        """Test cleanup runs even after test failure."""
        test_def = E2ETestDefinition(
            name="Cleanup On Failure Test",
            steps=[
                E2ETestStep(
                    name="Create and fail",
                    command="echo content > to_clean.txt && exit 1",
                    validations=[
                        ValidationConfig(
                            type=ValidationType.EXIT_CODE,
                            expected=0,
                        ),
                    ],
                ),
            ],
            cleanup=E2ETestCleanup(
                files=["to_clean.txt"],
            ),
        )

        result = runner.run(test_def)

        assert result.passed is False
        assert result.cleanup_executed is True

    def test_working_directory_per_step(self, runner: E2ETestRunner):
        """Test step-specific working directory."""
        test_def = E2ETestDefinition(
            name="Working Dir Test",
            steps=[
                E2ETestStep(
                    name="Create subdir",
                    command="mkdir -p subdir",
                ),
                E2ETestStep(
                    name="Work in subdir",
                    command="pwd > location.txt",
                    working_dir="subdir",
                    validations=[
                        ValidationConfig(
                            type=ValidationType.FILE_EXISTS,
                            path="location.txt",
                        ),
                    ],
                ),
            ],
        )

        result = runner.run(test_def)

        assert result.passed is True
        assert (runner.working_dir / "subdir" / "location.txt").exists()

    def test_environment_variables(self, runner: E2ETestRunner):
        """Test step environment variables."""
        test_def = E2ETestDefinition(
            name="Env Var Test",
            steps=[
                E2ETestStep(
                    name="Echo env var",
                    command="echo $MY_VAR > output.txt",
                    env={"MY_VAR": "test_value"},
                    validations=[
                        ValidationConfig(
                            type=ValidationType.FILE_CONTAINS,
                            path="output.txt",
                            pattern="test_value",
                        ),
                    ],
                ),
            ],
        )

        result = runner.run(test_def)

        assert result.passed is True

    def test_python_code_execution(self, runner: E2ETestRunner):
        """Test Python code execution in step."""
        test_def = E2ETestDefinition(
            name="Python Code Test",
            steps=[
                E2ETestStep(
                    name="Run Python",
                    python_code='Path("python_output.txt").write_text("from python")',
                    validations=[
                        ValidationConfig(
                            type=ValidationType.FILE_EXISTS,
                            path="python_output.txt",
                        ),
                        ValidationConfig(
                            type=ValidationType.FILE_CONTAINS,
                            path="python_output.txt",
                            pattern="from python",
                        ),
                    ],
                ),
            ],
        )

        result = runner.run(test_def)

        assert result.passed is True

    def test_test_result_summary(self, runner: E2ETestRunner):
        """Test result summary generation."""
        test_def = E2ETestDefinition(
            name="Summary Test",
            steps=[
                E2ETestStep(
                    name="Step 1",
                    command="echo one",
                ),
                E2ETestStep(
                    name="Step 2",
                    command="echo two",
                ),
            ],
        )

        result = runner.run(test_def)

        summary = result.summary()
        assert "Summary Test" in summary
        assert "PASSED" in summary


class TestE2ETestDefinitionFromYAML:
    """Tests for loading test definitions from YAML."""

    def test_load_from_yaml(self, tmp_path: Path):
        """Test loading test definition from YAML file."""
        yaml_content = """
name: YAML Test
description: Test loaded from YAML
mode: python
steps:
  - name: Echo test
    command: echo hello
    validations:
      - type: exit_code
        expected: 0
"""
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(yaml_content)

        test_def = E2ETestDefinition.from_yaml(yaml_file)

        assert test_def.name == "YAML Test"
        assert test_def.description == "Test loaded from YAML"
        assert test_def.mode == TestMode.PYTHON
        assert len(test_def.steps) == 1
        assert test_def.steps[0].name == "Echo test"

    def test_run_from_yaml(self, tmp_path: Path):
        """Test running test from YAML file."""
        yaml_content = """
name: Run From YAML
steps:
  - name: Create file
    command: touch created.txt
    validations:
      - type: file_exists
        path: created.txt
"""
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(yaml_content)

        runner = E2ETestRunner(working_dir=tmp_path / "work")
        result = runner.run_from_yaml(yaml_file)

        assert result.passed is True
