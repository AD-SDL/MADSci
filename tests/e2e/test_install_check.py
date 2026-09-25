"""Tests for the ``madsci-install`` skill's verification scripts.

Covers both bundled scripts:

* ``install-check.sh`` — verifies a *running* stack (checks PASS when things are present).
* ``uninstall-check.sh`` — verifies a *teardown* (checks PASS when things are absent).

Two layers of coverage each:

1. **Script self-tests** (no Docker, always run): syntax, executable bit, ``--help``
   exit code, usage errors on missing/bad ``--method`` and bad ``--scope``, the
   removed-``--goal`` deprecation shim, and port-override behaviour.
2. **Live-stack integration** (marked ``docker``, skipped unless ``--docker-enabled``):
   runs the scripts against a running example lab and asserts the expected verdict.
   Bring the stack up first with ``just up`` / ``docker compose up -d``.

The scripts live in the skill directory and are referenced from
``.claude/skills/madsci-install/SKILL.md``. ``.claude/skills`` is a symlink to
``.agents/skills``, so both paths resolve to the same file.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

# Absolute interpreter path — a bare "bash" is a partial executable path (ruff S607).
BASH = shutil.which("bash") or "/bin/bash"

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL_DIR = REPO_ROOT / ".agents" / "skills" / "madsci-install"
INSTALL_CHECK = SKILL_DIR / "install-check.sh"
UNINSTALL_CHECK = SKILL_DIR / "uninstall-check.sh"
SKILL_MD = SKILL_DIR / "SKILL.md"
UNINSTALL_MD = SKILL_DIR / "uninstall.md"

DEFAULT_MANAGER_PORTS = ("8001", "8002", "8003", "8004", "8005", "8006")
DASHBOARD_PORT = "8000"


def _run(script: Path, *args: str, timeout: int = 60) -> subprocess.CompletedProcess:
    """Run a skill check script from the repo root with ``--no-color`` for stable parsing."""
    return subprocess.run(  # noqa: S603
        [BASH, str(script), "--no-color", *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(REPO_ROOT),
        check=False,
    )


def _run_script(*args: str, timeout: int = 60) -> subprocess.CompletedProcess:
    """Run install-check.sh (back-compat helper)."""
    return _run(INSTALL_CHECK, *args, timeout=timeout)


class TestInstallCheckScriptStructure:
    """Static / self-checks that do not require a running stack or Docker."""

    def test_script_exists(self) -> None:
        assert INSTALL_CHECK.exists(), f"{INSTALL_CHECK} not found"

    def test_script_is_executable(self) -> None:
        assert os.access(INSTALL_CHECK, os.X_OK), (
            f"{INSTALL_CHECK} is not executable (chmod +x it)"
        )

    def test_valid_bash_syntax(self) -> None:
        result = subprocess.run(  # noqa: S603
            [BASH, "-n", str(INSTALL_CHECK)],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert result.returncode == 0, f"bash -n failed:\n{result.stderr}"

    def test_help_exits_zero(self) -> None:
        result = _run_script("--help")
        assert result.returncode == 0, (
            f"--help should exit 0:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )
        assert "install-check.sh" in result.stdout

    def test_missing_method_is_usage_error(self) -> None:
        """--method is required; omitting it must be a usage error, not a default."""
        result = _run_script()
        assert result.returncode == 2, (
            f"omitting --method should be a usage error (exit 2), "
            f"got {result.returncode}:\nstderr: {result.stderr}"
        )

    @pytest.mark.parametrize("bad_method", ["podman", "pip", "1", "abc"])
    def test_invalid_method_is_usage_error(self, bad_method: str) -> None:
        result = _run_script("--method", bad_method)
        assert result.returncode == 2, (
            f"--method {bad_method} should be a usage error (exit 2), "
            f"got {result.returncode}:\nstderr: {result.stderr}"
        )

    # NOTE: explicit ids — a bare "docker" param id lands in item.keywords and
    # would be swept up by conftest's docker-marker skip (see tests/e2e/conftest.py).
    @pytest.mark.parametrize(
        "method",
        [
            pytest.param("docker", id="method-docker"),
            pytest.param("local", id="method-local"),
        ],
    )
    def test_valid_methods_accepted(self, method: str) -> None:
        """A valid method must never be a usage error (exit 0 or 1, never 2)."""
        result = _run_script("--method", method, timeout=120)
        assert result.returncode in (0, 1), (
            f"--method {method} should be accepted (exit 0/1), got {result.returncode}:\n"
            f"{result.stderr}"
        )

    def test_removed_goal_flag_is_usage_error(self) -> None:
        """--goal was replaced by --method; the shim must reject it with guidance."""
        result = _run_script("--goal", "1")
        assert result.returncode == 2, (
            f"--goal should be rejected (exit 2), got {result.returncode}"
        )
        assert "--method" in result.stderr, (
            f"the --goal error should point at --method:\nstderr: {result.stderr}"
        )

    def test_unknown_arg_is_usage_error(self) -> None:
        result = _run_script("--not-a-real-flag")
        assert result.returncode == 2

    def test_skill_md_references_script(self) -> None:
        """SKILL.md must document how to run the verification script."""
        text = SKILL_MD.read_text()
        assert "install-check.sh" in text


class TestInstallCheckAgainstAbsentStack:
    """When no stack is running, health checks must FAIL (exit 1), not pass silently.

    This guards against the script reporting success when nothing is up. It runs
    with a manager-port set that is almost certainly closed, so it is safe on a
    host that is NOT running the example lab. When the example lab *is* running on
    the default ports, this test is skipped to avoid a false expectation.
    """

    def test_health_checks_fail_when_nothing_listening(self) -> None:
        if not shutil.which("curl"):
            pytest.skip("curl not available")
        # High ports unlikely to be bound by anything. --method local keeps this
        # test independent of whether a Docker daemon is present on the host.
        result = _run_script(
            "--method",
            "local",
            "--managers",
            "59117",
            "--dashboard-port",
            "59118",
            timeout=60,
        )
        assert result.returncode == 1, (
            "install-check.sh should FAIL when the target manager port is closed:\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
        assert "FAIL" in result.stdout


@pytest.mark.docker
class TestInstallCheckLiveStack:
    """Integration: verify install-check.sh --method docker against a running example lab.

    Skipped unless ``--docker-enabled`` is passed (see tests/e2e/conftest.py).
    Requires the example lab to already be up (``just up`` / ``docker compose up -d``).
    """

    def test_docker_method_passes_against_running_stack(self) -> None:
        result = _run_script("--method", "docker", timeout=120)
        assert result.returncode == 0, (
            "install-check.sh --method docker should PASS against a running example lab.\n"
            "Is the stack up (`just up`)?\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        # Every default manager port and the dashboard should report a 200.
        for port in (*DEFAULT_MANAGER_PORTS, DASHBOARD_PORT):
            assert f"localhost:{port}/health → 200" in result.stdout, (
                f"expected a 200 health line for port {port}:\n{result.stdout}"
            )
        assert "Failed: 0" in result.stdout


class TestUninstallCheckScriptStructure:
    """Static / self-checks for uninstall-check.sh (no Docker, no live stack)."""

    def test_script_exists(self) -> None:
        assert UNINSTALL_CHECK.exists(), f"{UNINSTALL_CHECK} not found"

    def test_script_is_executable(self) -> None:
        assert os.access(UNINSTALL_CHECK, os.X_OK), (
            f"{UNINSTALL_CHECK} is not executable (chmod +x it)"
        )

    def test_valid_bash_syntax(self) -> None:
        result = subprocess.run(  # noqa: S603
            [BASH, "-n", str(UNINSTALL_CHECK)],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert result.returncode == 0, f"bash -n failed:\n{result.stderr}"

    def test_help_exits_zero(self) -> None:
        result = _run(UNINSTALL_CHECK, "--help")
        assert result.returncode == 0, (
            f"--help should exit 0:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )
        assert "uninstall-check.sh" in result.stdout

    def test_missing_method_is_usage_error(self) -> None:
        """--method is required; omitting it must be a usage error, not a default."""
        result = _run(UNINSTALL_CHECK, "--scope", "stop")
        assert result.returncode == 2, (
            f"omitting --method should be a usage error (exit 2), got {result.returncode}"
        )

    @pytest.mark.parametrize("bad_method", ["podman", "pip", "3", "abc"])
    def test_invalid_method_is_usage_error(self, bad_method: str) -> None:
        result = _run(UNINSTALL_CHECK, "--method", bad_method)
        assert result.returncode == 2, (
            f"--method {bad_method} should be a usage error (exit 2), got {result.returncode}"
        )

    def test_removed_goal_flag_is_usage_error(self) -> None:
        """--goal was replaced by --method; the shim must reject it with guidance."""
        result = _run(UNINSTALL_CHECK, "--goal", "1")
        assert result.returncode == 2, (
            f"--goal should be rejected (exit 2), got {result.returncode}"
        )
        assert "--method" in result.stderr, (
            f"the --goal error should point at --method:\nstderr: {result.stderr}"
        )

    @pytest.mark.parametrize("bad_scope", ["all", "delete", "purge", ""])
    def test_invalid_scope_is_usage_error(self, bad_scope: str) -> None:
        # --method must be valid, otherwise this would exit 2 on the method check
        # and pass for the wrong reason.
        result = _run(UNINSTALL_CHECK, "--method", "docker", "--scope", bad_scope)
        assert result.returncode == 2, (
            f"--scope {bad_scope!r} should be a usage error (exit 2), got {result.returncode}"
        )

    @pytest.mark.parametrize("scope", ["stop", "remove", "wipe"])
    def test_valid_scopes_accepted(self, scope: str) -> None:
        """A valid scope must not be a usage error (exit 0 or 1, never 2)."""
        result = _run(UNINSTALL_CHECK, "--method", "docker", "--scope", scope)
        assert result.returncode in (0, 1), (
            f"--scope {scope} should be accepted (exit 0/1), got {result.returncode}:\n"
            f"{result.stderr}"
        )

    def test_unknown_arg_is_usage_error(self) -> None:
        result = _run(UNINSTALL_CHECK, "--not-a-real-flag")
        assert result.returncode == 2

    def test_skill_md_references_script(self) -> None:
        text = SKILL_MD.read_text()
        assert "uninstall-check.sh" in text

    def test_skill_md_documents_uninstall_step(self) -> None:
        """SKILL.md must point to the uninstall workflow (extracted into uninstall.md)."""
        text = SKILL_MD.read_text().lower()
        assert "uninstall" in text
        # scope vocabulary shared by the script, SKILL.md pointer, and uninstall.md
        for scope in ("stop", "remove", "wipe"):
            assert scope in text, (
                f"expected uninstall scope '{scope}' documented in SKILL.md"
            )

    def test_uninstall_md_exists_and_is_referenced(self) -> None:
        """The detailed teardown workflow lives in the bundled uninstall.md."""
        assert UNINSTALL_MD.exists(), f"{UNINSTALL_MD} not found"
        assert "uninstall.md" in SKILL_MD.read_text(), (
            "SKILL.md must link to the extracted uninstall.md"
        )

    def test_uninstall_md_contains_full_workflow(self) -> None:
        """uninstall.md must carry the detail moved out of SKILL.md."""
        text = UNINSTALL_MD.read_text()
        lower = text.lower()
        for scope in ("stop", "remove", "wipe"):
            assert scope in lower, f"expected scope '{scope}' in uninstall.md"
        # the destructive specifics that must not get lost in the extraction
        assert "uninstall-check.sh" in text
        assert "pip uninstall" in text
        assert ".madsci" in text
        assert "docker compose down" in text or "just down" in text


class TestUninstallCheckAgainstFreeHost:
    """On a host with nothing on the target ports, a 'stop' teardown must verify clean.

    Uses a high port that is almost certainly free, so this is safe regardless of
    whether the example lab is running on the default ports.
    """

    def test_stop_scope_passes_when_port_free(self) -> None:
        if not shutil.which("curl"):
            pytest.skip("curl not available")
        result = _run(
            UNINSTALL_CHECK,
            "--method",
            "docker",
            "--scope",
            "stop",
            "--managers",
            "59117",
            "--dashboard-port",
            "59118",
            timeout=60,
        )
        # No container check failures possible for these ports; the port checks
        # must PASS (nothing listening). Container check may still find real
        # MADSci containers if the lab is up — so assert on the port lines only.
        assert "port 59117 free" in result.stdout, result.stdout
        assert "port 59118 free" in result.stdout, result.stdout


@pytest.mark.docker
class TestUninstallCheckLiveStack:
    """Integration: uninstall-check must FAIL while the example lab is still running.

    This is the mirror of the install-check live test: it proves the negative
    logic (teardown verification does not falsely pass when the stack is up).
    Skipped unless ``--docker-enabled``; requires the example lab to be UP.
    """

    def test_stop_scope_fails_against_running_stack(self) -> None:
        result = _run(
            UNINSTALL_CHECK, "--method", "docker", "--scope", "stop", timeout=60
        )
        assert result.returncode == 1, (
            "uninstall-check.sh should FAIL while the example lab is still running.\n"
            "Is the stack actually up (`just up`)?\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        # It should name at least one still-running MADSci container and a live port.
        assert "still running" in result.stdout, result.stdout
        assert "still serving /health" in result.stdout, result.stdout
