"""
E2E Test Runner for MADSci.

Executes test definitions and captures results.
"""

import contextlib
import io
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from madsci.common.testing.types import (
    E2ETestDefinition,
    E2ETestResult,
    E2ETestStep,
    StepResult,
    TestMode,
    ValidationConfig,
)
from madsci.common.testing.validators import (
    get_validator_registry,
    wait_for_condition,
)
from rich.console import Console


class E2ETestRunner:
    """
    Executes E2E test definitions.

    Supports both pure Python mode (no Docker) and Docker mode.
    """

    def __init__(
        self,
        working_dir: Path | None = None,
        mode: TestMode | None = None,
        console: Console | None = None,
        verbose: bool = False,
        capture_logs: bool = True,
    ) -> None:
        """
        Initialize the test runner.

        Args:
            working_dir: Base directory for test execution. If None, uses a temp dir.
            mode: Test execution mode (PYTHON, DOCKER, HYBRID). If None, uses test's mode.
            console: Rich console for output. If None, creates one.
            verbose: If True, print verbose output.
            capture_logs: If True, capture all logs to a file.
        """
        self.working_dir = working_dir or Path(tempfile.mkdtemp(prefix="madsci_e2e_"))
        self.mode_override = mode
        self.console = console or Console()
        self.verbose = verbose
        self.capture_logs = capture_logs
        self.validator_registry = get_validator_registry()
        self._background_processes: list[subprocess.Popen] = []
        self._logs_file: Path | None = None

    def run(
        self,
        test_definition: E2ETestDefinition,
        env: dict[str, str] | None = None,
    ) -> E2ETestResult:
        """
        Run an E2E test.

        Args:
            test_definition: The test to run
            env: Additional environment variables

        Returns:
            E2ETestResult with the test outcome
        """
        mode = self.mode_override or test_definition.mode
        started_at = datetime.now()

        # Prepare environment and logs
        test_env = self._prepare_environment(env)
        self._setup_logs(test_definition.name)
        self._print_test_header(test_definition.name, mode)

        # Execute test phases
        setup_results, step_results, passed, error = self._execute_test_phases(
            test_definition, test_env
        )

        # Cleanup and finalize
        cleanup_executed = self._run_cleanup(test_definition, test_env)
        completed_at = datetime.now()

        result = E2ETestResult(
            test_name=test_definition.name,
            passed=passed,
            mode=mode,
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=(completed_at - started_at).total_seconds(),
            setup_results=setup_results,
            step_results=step_results,
            cleanup_executed=cleanup_executed,
            error=error,
            logs_path=self._logs_file,
        )

        self._print_summary(result)
        return result

    def _prepare_environment(self, env: dict[str, str] | None) -> dict[str, str]:
        """Prepare the environment variables for test execution."""
        test_env = os.environ.copy()
        if env:
            test_env.update(env)
        return test_env

    def _setup_logs(self, test_name: str) -> None:
        """Set up log file for capturing output."""
        if self.capture_logs:
            # Ensure working directory exists
            self.working_dir.mkdir(parents=True, exist_ok=True)
            self._logs_file = (
                self.working_dir / f"{test_name.replace(' ', '_')}_logs.txt"
            )
            self._logs_file.touch()

    def _print_test_header(self, test_name: str, mode: TestMode) -> None:
        """Print the test header information."""
        self.console.print(f"\n[bold blue]Running test: {test_name}[/bold blue]")
        self.console.print(f"Mode: {mode.value}")
        self.console.print(f"Working directory: {self.working_dir}")

    def _execute_test_phases(
        self,
        test_definition: E2ETestDefinition,
        test_env: dict[str, str],
    ) -> tuple[list[StepResult], list[StepResult], bool, str | None]:
        """Execute all test phases (requirements check, setup, main steps)."""
        mode = self.mode_override or test_definition.mode
        setup_results: list[StepResult] = []
        step_results: list[StepResult] = []
        error: str | None = None
        passed = True

        try:
            # Check requirements
            if not self._check_requirements(test_definition, mode):
                return setup_results, step_results, False, "Requirements not met"

            # Run setup steps
            setup_results, passed, error = self._run_setup_steps(
                test_definition.setup, test_env
            )
            if not passed:
                return setup_results, step_results, passed, error

            # Run main test steps
            step_results, passed, error = self._run_main_steps(
                test_definition.steps, test_env
            )

        except KeyboardInterrupt:
            error = "Test interrupted by user"
            passed = False
        except Exception as e:
            error = f"Unexpected error: {e}"
            passed = False

        return setup_results, step_results, passed, error

    def _run_setup_steps(
        self,
        setup_steps: list[E2ETestStep],
        test_env: dict[str, str],
    ) -> tuple[list[StepResult], bool, str | None]:
        """Run setup steps and return results."""
        results: list[StepResult] = []
        if not setup_steps:
            return results, True, None

        self.console.print("\n[bold]Running setup steps...[/bold]")
        for step in setup_steps:
            result = self._run_step(step, test_env)
            results.append(result)
            self._print_step_result(result)
            if not result.passed and not step.continue_on_error:
                return results, False, f"Setup step failed: {step.name}"

        return results, True, None

    def _run_main_steps(
        self,
        steps: list[E2ETestStep],
        test_env: dict[str, str],
    ) -> tuple[list[StepResult], bool, str | None]:
        """Run main test steps and return results."""
        results: list[StepResult] = []
        self.console.print("\n[bold]Running test steps...[/bold]")
        any_failed = False

        for step in steps:
            result = self._run_step(step, test_env)
            results.append(result)
            self._print_step_result(result)
            if not result.passed:
                any_failed = True
                if not step.continue_on_error:
                    return results, False, f"Step failed: {step.name}"

        # If any step failed (even with continue_on_error), the test fails
        if any_failed:
            return results, False, None

        return results, True, None

    def run_from_yaml(self, yaml_path: Path, **kwargs: Any) -> E2ETestResult:
        """
        Load and run a test from a YAML file.

        Args:
            yaml_path: Path to the test definition YAML file
            **kwargs: Additional arguments passed to run()

        Returns:
            E2ETestResult with the test outcome
        """
        test_definition = E2ETestDefinition.from_yaml(yaml_path)
        return self.run(test_definition, **kwargs)

    def _check_requirements(
        self,
        test_definition: E2ETestDefinition,
        mode: TestMode,
    ) -> bool:
        """Check if all requirements are met for running the test."""
        reqs = test_definition.requirements

        # Check Docker requirement
        if (reqs.docker or mode == TestMode.DOCKER) and not self._is_docker_available():
            self.console.print("[red]Docker is required but not available[/red]")
            return False

        # Check Docker Compose requirement
        if reqs.docker_compose and not self._is_docker_compose_available():
            self.console.print(
                "[red]Docker Compose is required but not available[/red]"
            )
            return False

        # Check Python version (basic check)
        if reqs.python:
            current = f"{sys.version_info.major}.{sys.version_info.minor}"
            # Simple version check - could be more sophisticated
            if reqs.python.startswith(">="):
                required = reqs.python[2:]
                if current < required:
                    self.console.print(
                        f"[red]Python {reqs.python} required, but {current} found[/red]"
                    )
                    return False

        return True

    def _is_docker_available(self) -> bool:
        """Check if Docker is available."""
        try:
            result = subprocess.run(
                ["docker", "info"],  # noqa: S607
                check=False,
                capture_output=True,
                timeout=10,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def _is_docker_compose_available(self) -> bool:
        """Check if Docker Compose is available."""
        try:
            result = subprocess.run(
                ["docker", "compose", "version"],  # noqa: S607
                check=False,
                capture_output=True,
                timeout=10,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def _run_step(
        self,
        step: E2ETestStep,
        env: dict[str, str],
    ) -> StepResult:
        """Execute a single test step."""
        started_at = datetime.now()

        # Check skip condition
        skip_result = self._check_skip_condition(step, env, started_at)
        if skip_result is not None:
            return skip_result

        # Prepare working directory and environment
        working_dir = self._prepare_step_working_dir(step)
        step_env = self._prepare_step_env(env, step.env)

        # Execute command or Python code
        exit_code, stdout, stderr, error_msg = self._execute_step_action(
            step, working_dir, step_env
        )

        # Run validations and build result
        return self._build_step_result(
            step, started_at, working_dir, exit_code, stdout, stderr, error_msg
        )

    def _check_skip_condition(
        self,
        step: E2ETestStep,
        env: dict[str, str],
        started_at: datetime,
    ) -> StepResult | None:
        """Check if step should be skipped. Returns StepResult if skipped, None otherwise."""
        if not step.skip_if:
            return None

        try:
            should_skip = eval(step.skip_if, {"env": env, "os": os})  # noqa: S307
            if should_skip:
                return StepResult(
                    step_name=step.name,
                    passed=True,
                    skipped=True,
                    skip_reason=f"Skip condition met: {step.skip_if}",
                    duration_seconds=0,
                    started_at=started_at,
                    completed_at=datetime.now(),
                )
        except Exception as e:
            return StepResult(
                step_name=step.name,
                passed=False,
                duration_seconds=0,
                started_at=started_at,
                completed_at=datetime.now(),
                error=f"Error evaluating skip condition: {e}",
            )
        return None

    def _prepare_step_working_dir(self, step: E2ETestStep) -> Path:
        """Prepare and return the working directory for a step."""
        working_dir = self.working_dir
        if step.working_dir:
            working_dir = self.working_dir / step.working_dir
            working_dir.mkdir(parents=True, exist_ok=True)
        return working_dir

    def _prepare_step_env(
        self, base_env: dict[str, str], step_env: dict[str, str]
    ) -> dict[str, str]:
        """Merge base environment with step-specific environment."""
        merged = base_env.copy()
        merged.update(step_env)
        return merged

    def _execute_step_action(
        self,
        step: E2ETestStep,
        working_dir: Path,
        step_env: dict[str, str],
    ) -> tuple[int | None, str, str, str | None]:
        """Execute the step's command or Python code."""
        if step.command:
            exit_code, stdout, stderr, error_msg = self._execute_command(
                step.command,
                working_dir,
                step_env,
                step.timeout,
                step.background,
            )

            # Wait for condition if background process
            if step.background and step.wait_for and exit_code == 0:
                wait_config = ValidationConfig(
                    type=step.wait_for.type,
                    url=step.wait_for.url,
                    path=step.wait_for.path,
                    timeout=step.wait_for.timeout,
                )
                context = {"working_dir": str(working_dir)}
                if not wait_for_condition(
                    wait_config,
                    context,
                    timeout=step.wait_for.timeout,
                    poll_interval=step.wait_for.poll_interval,
                ):
                    error_msg = (
                        f"Timeout waiting for condition: {step.wait_for.type.value}"
                    )

            return exit_code, stdout, stderr, error_msg

        if step.python_code:
            return self._execute_python(step.python_code, working_dir, step_env)

        return None, "", "", None

    def _build_step_result(
        self,
        step: E2ETestStep,
        started_at: datetime,
        working_dir: Path,
        exit_code: int | None,
        stdout: str,
        stderr: str,
        error_msg: str | None,
    ) -> StepResult:
        """Build and return the step result with validations."""
        completed_at = datetime.now()
        duration = (completed_at - started_at).total_seconds()

        # Run validations
        context = {
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
            "working_dir": str(working_dir),
        }
        validation_results = [
            self.validator_registry.validate(validation, context)
            for validation in step.validations
        ]

        # Determine overall pass/fail
        passed = error_msg is None and all(v.passed for v in validation_results)

        # Log output if capturing
        self._log_step_output(step.name, stdout, stderr)

        return StepResult(
            step_name=step.name,
            passed=passed,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            duration_seconds=duration,
            started_at=started_at,
            completed_at=completed_at,
            validation_results=validation_results,
            error=error_msg,
        )

    def _log_step_output(self, step_name: str, stdout: str, stderr: str) -> None:
        """Log step output to the logs file."""
        if self._logs_file and (stdout or stderr):
            with self._logs_file.open("a") as f:
                f.write(f"\n=== Step: {step_name} ===\n")
                if stdout:
                    f.write(f"STDOUT:\n{stdout}\n")
                if stderr:
                    f.write(f"STDERR:\n{stderr}\n")

    def _execute_command(
        self,
        command: str,
        working_dir: Path,
        env: dict[str, str],
        timeout: float,
        background: bool = False,
    ) -> tuple[int | None, str, str, str | None]:
        """
        Execute a shell command.

        Returns:
            Tuple of (exit_code, stdout, stderr, error_message)
        """
        if self.verbose:
            self.console.print(f"  [dim]$ {command}[/dim]")

        try:
            if background:
                return self._execute_background_command(command, working_dir, env)
            return self._execute_foreground_command(command, working_dir, env, timeout)
        except subprocess.TimeoutExpired:
            return None, "", "", f"Command timed out after {timeout}s"
        except Exception as e:
            return None, "", "", f"Command execution error: {e}"

    def _execute_background_command(
        self,
        command: str,
        working_dir: Path,
        env: dict[str, str],
    ) -> tuple[int | None, str, str, str | None]:
        """Execute a command in the background."""
        process = subprocess.Popen(  # noqa: S602
            command,
            shell=True,  # Required for running user-provided shell commands
            cwd=working_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        self._background_processes.append(process)
        # Give it a moment to start
        time.sleep(0.5)
        # Check if it crashed immediately
        poll = process.poll()
        if poll is not None and poll != 0:
            stdout, stderr = process.communicate()
            return (
                poll,
                stdout.decode(),
                stderr.decode(),
                "Background process exited immediately",
            )
        return 0, "", "", None

    def _execute_foreground_command(
        self,
        command: str,
        working_dir: Path,
        env: dict[str, str],
        timeout: float,
    ) -> tuple[int, str, str, str | None]:
        """Execute a command in the foreground."""
        result = subprocess.run(  # noqa: S602
            command,
            check=False,
            shell=True,  # Required for running user-provided shell commands
            cwd=working_dir,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode, result.stdout, result.stderr, None

    def _execute_python(
        self,
        code: str,
        working_dir: Path,
        env: dict[str, str],
    ) -> tuple[int, str, str, str | None]:
        """
        Execute Python code.

        Returns:
            Tuple of (exit_code, stdout, stderr, error_message)
        """
        old_cwd = Path.cwd()
        old_stdout = sys.stdout
        old_stderr = sys.stderr

        stdout_capture: io.StringIO = io.StringIO()
        stderr_capture: io.StringIO = io.StringIO()

        try:
            os.chdir(working_dir)
            sys.stdout = stdout_capture
            sys.stderr = stderr_capture

            exec(code, {"env": env, "Path": Path, "os": os})  # noqa: S102

            stdout = stdout_capture.getvalue()
            stderr = stderr_capture.getvalue()
            return 0, stdout, stderr, None
        except Exception as e:
            stderr = stderr_capture.getvalue()
            return 1, "", stderr, str(e)
        finally:
            os.chdir(old_cwd)
            sys.stdout = old_stdout
            sys.stderr = old_stderr

    def _run_cleanup(
        self,
        test_definition: E2ETestDefinition,
        env: dict[str, str],
    ) -> bool:
        """Run cleanup actions."""
        cleanup = test_definition.cleanup
        executed = False

        # Stop background processes
        if cleanup.stop_background:
            self._stop_background_processes()
            executed = True

        # Run cleanup commands
        if self._run_cleanup_commands(cleanup.commands, env):
            executed = True

        # Remove files
        if self._cleanup_files(cleanup.files):
            executed = True

        return executed

    def _stop_background_processes(self) -> None:
        """Stop all background processes."""
        for process in self._background_processes:
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                process.wait(timeout=5)
            except Exception:
                with contextlib.suppress(Exception):
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        self._background_processes.clear()

    def _run_cleanup_commands(self, commands: list[str], env: dict[str, str]) -> bool:
        """Run cleanup commands. Returns True if any were executed."""
        executed = False
        for command in commands:
            try:
                subprocess.run(  # noqa: S602
                    command,
                    check=False,
                    shell=True,  # Required for running user-provided shell commands
                    cwd=self.working_dir,
                    env=env,
                    capture_output=True,
                    timeout=30,
                )
                executed = True
            except Exception:  # noqa: S110
                pass  # Best effort cleanup - intentionally ignoring exceptions
        return executed

    def _cleanup_files(self, file_patterns: list[str]) -> bool:
        """Remove files matching patterns. Returns True if any were processed."""
        executed = False
        for file_pattern in file_patterns:
            try:
                for file_path in self.working_dir.glob(file_pattern):
                    if file_path.is_file():
                        file_path.unlink()
                    elif file_path.is_dir():
                        shutil.rmtree(file_path)
                executed = True
            except Exception:  # noqa: S110
                pass  # Best effort cleanup - intentionally ignoring exceptions
        return executed

    def _print_step_result(self, result: StepResult) -> None:
        """Print the result of a step."""
        if result.skipped:
            self.console.print(f"  [yellow]⊘ {result.step_name}[/yellow] (skipped)")
            return

        status = "[green]✓[/green]" if result.passed else "[red]✗[/red]"
        self.console.print(
            f"  {status} {result.step_name} ({result.duration_seconds:.2f}s)"
        )

        if not result.passed:
            if result.error:
                self.console.print(f"    [red]Error: {result.error}[/red]")
            for validation in result.validation_results:
                if not validation.passed:
                    self.console.print(f"    [red]- {validation.message}[/red]")

        if self.verbose:
            for validation in result.validation_results:
                status = "[green]✓[/green]" if validation.passed else "[red]✗[/red]"
                self.console.print(f"    {status} {validation.message}")

    def _print_summary(self, result: E2ETestResult) -> None:
        """Print the test summary."""
        self.console.print("\n" + "=" * 60)
        status = (
            "[bold green]PASSED[/bold green]"
            if result.passed
            else "[bold red]FAILED[/bold red]"
        )
        self.console.print(f"Test: {result.test_name} - {status}")
        self.console.print(f"Duration: {result.duration_seconds:.2f}s")
        self.console.print(
            f"Steps: {result.steps_passed} passed, {result.steps_failed} failed, "
            f"{result.steps_skipped} skipped"
        )
        if result.error:
            self.console.print(f"[red]Error: {result.error}[/red]")
        if result.logs_path:
            self.console.print(f"Logs: {result.logs_path}")
        self.console.print("=" * 60 + "\n")
