Module madsci.common.testing.runner
===================================
E2E Test Runner for MADSci.

Executes test definitions and captures results.

Trust boundary: test YAML files are trusted developer input (like Makefiles
or CI configs).  ``skip_if`` expressions are evaluated with ``simpleeval``
for defence-in-depth.  ``_execute_python()`` uses ``exec()`` and
``_execute_foreground_command()``/``_execute_background_command()`` use
``shell=True`` intentionally — they run commands authored by the test
developer, analogous to ``make`` recipe lines.

Classes
-------

`E2ETestRunner(working_dir: pathlib.Path | None = None, mode: madsci.common.testing.types.TestMode | None = None, console: rich.console.Console | None = None, verbose: bool = False, capture_logs: bool = True)`
:   Executes E2E test definitions.

    Supports both pure Python mode (no Docker) and Docker mode.

    Initialize the test runner.

    Args:
        working_dir: Base directory for test execution. If None, uses a temp dir.
        mode: Test execution mode (PYTHON, DOCKER, HYBRID). If None, uses test's mode.
        console: Rich console for output. If None, creates one.
        verbose: If True, print verbose output.
        capture_logs: If True, capture all logs to a file.

    ### Methods

    `run(self, test_definition: madsci.common.testing.types.E2ETestDefinition, env: dict[str, str] | None = None) ‑> madsci.common.testing.types.E2ETestResult`
    :   Run an E2E test.

        Args:
            test_definition: The test to run
            env: Additional environment variables

        Returns:
            E2ETestResult with the test outcome

    `run_from_yaml(self, yaml_path: pathlib.Path, **kwargs: Any) ‑> madsci.common.testing.types.E2ETestResult`
    :   Load and run a test from a YAML file.

        Args:
            yaml_path: Path to the test definition YAML file
            **kwargs: Additional arguments passed to run()

        Returns:
            E2ETestResult with the test outcome
