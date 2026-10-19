"""Tests for the ``madsci-install`` skill's verification scripts.

Covers both bundled scripts:

* ``install-check.sh`` — verifies a *running* stack (checks PASS when things are present).
* ``uninstall-check.sh`` — verifies a *teardown* (checks PASS when things are absent).

Three layers of coverage:

1. **Script self-tests** (no Docker, always run): syntax, executable bit, ``--help``
   exit code, usage errors on unknown flags and bad ``--scope``, and the
   value-taking-flag guards.
2. **Degraded-host tests** (no Docker, always run): the scripts run with a
   deliberately stripped ``PATH``. These encode the rule that a check which
   *could not verify* must never report a pass — see ``TestDegradedHost``.
3. **Live-stack integration** (marked ``docker``, skipped unless ``--docker-enabled``):
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

# High ports that are almost certainly unbound, so the port-oriented tests are
# safe to run whether or not the example lab is up on the default ports.
FREE_MANAGER_PORT = "59117"
FREE_DASHBOARD_PORT = "59118"

# Tools the scripts may shell out to. TestDegradedHost builds a PATH from this
# list minus whichever tools it wants to simulate as missing.
_SANDBOX_TOOLS = (
    "basename",
    "cat",
    "comm",
    "curl",
    "cut",
    "dirname",
    "docker",
    "du",
    "env",
    "grep",
    "head",
    "jq",
    "ls",
    "lsof",
    "mktemp",
    "od",
    "printf",
    "python3",
    "rm",
    "sed",
    "sort",
    "ss",
    "tail",
    "tr",
    "wc",
)


def _run(
    script: Path,
    *args: str,
    timeout: int = 60,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess:
    """Run a skill check script from the repo root with ``--no-color`` for stable parsing."""
    return subprocess.run(  # noqa: S603
        [BASH, str(script), "--no-color", *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(REPO_ROOT),
        check=False,
        env=env,
    )


def _run_script(*args: str, **kwargs: object) -> subprocess.CompletedProcess:
    """Run install-check.sh (back-compat helper)."""
    return _run(INSTALL_CHECK, *args, **kwargs)  # type: ignore[arg-type]


def _sandbox_path(tmp_path: Path, *, without: tuple[str, ...]) -> dict[str, str]:
    """Build an env whose PATH holds only ``_SANDBOX_TOOLS`` minus ``without``.

    Used to prove the scripts degrade to FAIL/SKIP — never to PASS — when a tool
    they depend on for evidence is unavailable.
    """
    bindir = tmp_path / "limited-bin"
    bindir.mkdir(exist_ok=True)
    for tool in _SANDBOX_TOOLS:
        if tool in without:
            continue
        resolved = shutil.which(tool)
        if resolved:
            link = bindir / tool
            if not link.exists():
                link.symlink_to(resolved)
    return {"PATH": str(bindir), "HOME": str(tmp_path)}


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

    def test_help_is_not_truncated(self) -> None:
        """The --help sed range must cover the whole header comment.

        Condensing the header without widening the range silently cuts the
        usage text off mid-section.
        """
        result = _run_script("--help")
        assert "Exit codes:" in result.stdout, (
            "--help output stops before the exit-code block — widen the sed "
            f"range in install-check.sh:\n{result.stdout}"
        )

    def test_unknown_arg_is_usage_error(self) -> None:
        result = _run_script("--not-a-real-flag")
        assert result.returncode == 2

    @pytest.mark.parametrize(
        "flag", ["--managers", "--dashboard-port", "--install-dir"]
    )
    def test_value_flag_without_value_is_usage_error(self, flag: str) -> None:
        """A value-taking flag in final position must exit 2, not spin forever.

        ``shift 2`` with one argument left fails silently under ``set +e``, so
        the arg loop never advances. The need_value guard is what prevents that.
        """
        result = _run_script(flag, timeout=10)
        assert result.returncode == 2, (
            f"{flag} with no value should be a usage error (exit 2), "
            f"got {result.returncode}:\nstderr: {result.stderr}"
        )

    @pytest.mark.parametrize("flag", ["--with-ui", "--no-ui"])
    def test_ui_mode_flags_accepted(self, flag: str) -> None:
        """UI-mode flags must never be a usage error (exit 0 or 1, never 2)."""
        result = _run_script(flag, timeout=120)
        assert result.returncode in (0, 1), (
            f"{flag} should be accepted (exit 0/1), got {result.returncode}:\n"
            f"{result.stderr}"
        )

    def test_exec_targets_a_compose_service_not_a_container_name(self) -> None:
        """``docker compose exec`` takes a SERVICE; matching the NAME column breaks.

        NAME and SERVICE only coincide where the compose pins ``container_name:``.
        Enumerating services is the portable form.
        """
        text = INSTALL_CHECK.read_text()
        assert "ps --services --status running" in text, (
            "install-check.sh must enumerate compose services directly; matching "
            "the `docker compose ps` NAME column and passing that to "
            "`docker compose exec` fails on auto-generated container names"
        )

    def test_skill_md_references_script(self) -> None:
        """SKILL.md must document how to run the verification script."""
        text = SKILL_MD.read_text()
        assert "install-check.sh" in text

    def test_skill_md_requires_curl_as_a_prereq(self) -> None:
        """The script assumes curl exists; the skill is what guarantees it.

        install-check.sh does every HTTP assertion through curl and carries no
        fallback. That is only safe because Step 4 blocks on ``curl --version``
        alongside ``docker info``. Drop the prereq and the verification step
        silently loses its evidence.
        """
        text = SKILL_MD.read_text()
        step4 = text.split("## Step 4 — Check prerequisites", 1)
        assert len(step4) == 2, "Step 4 (prerequisites) not found in SKILL.md"
        prereqs = step4[1].split("## Step 5", 1)[0]
        assert "curl --version" in prereqs, (
            "Step 4 must block on `curl --version` — install-check.sh has no "
            f"curl fallback:\n{prereqs}"
        )


class TestInstallCheckAgainstAbsentStack:
    """When no stack is running, health checks must FAIL (exit 1), not pass silently."""

    def test_health_checks_fail_when_nothing_listening(self) -> None:
        if not shutil.which("curl"):
            pytest.skip("curl not available")
        result = _run_script(
            "--managers",
            FREE_MANAGER_PORT,
            "--dashboard-port",
            FREE_DASHBOARD_PORT,
            timeout=60,
        )
        assert result.returncode == 1, (
            "install-check.sh should FAIL when the target manager port is closed:\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
        assert "FAIL" in result.stdout


class TestDegradedHost:
    """A check that could not verify must FAIL or SKIP — never PASS.

    These are the regression tests for the class of bug where a missing tool
    made a command substitution come back empty and the empty result read as
    success.
    """

    def test_port_check_skips_without_listener_probe(self, tmp_path: Path) -> None:
        """With no ss and no lsof there is no evidence a port is free."""
        env = _sandbox_path(tmp_path, without=("ss", "lsof"))
        result = _run(
            UNINSTALL_CHECK,
            "--scope",
            "stop",
            "--managers",
            FREE_MANAGER_PORT,
            "--dashboard-port",
            FREE_DASHBOARD_PORT,
            timeout=60,
            env=env,
        )
        assert "SKIP  port-free checks" in result.stdout, (
            f"without ss/lsof the port check must SKIP, not PASS:\n{result.stdout}"
        )
        assert f"port {FREE_MANAGER_PORT} free" not in result.stdout, (
            "a port must never be reported free when nothing could probe it:\n"
            f"{result.stdout}"
        )

    def test_port_check_does_not_infer_freedom_from_http(self) -> None:
        """Port freedom must come from a listener probe, not a failed request.

        A slow host tripping --max-time and a service that is listening but
        does not serve /health are indistinguishable from 'nothing is there'.
        """
        code = [
            line
            for line in UNINSTALL_CHECK.read_text().splitlines()
            if not line.lstrip().startswith("#")
        ]
        offenders = [line for line in code if "curl" in line]
        assert not offenders, (
            "uninstall-check.sh must not decide port freedom over HTTP; use "
            "ss/lsof so 'no answer' is not mistaken for 'no listener'.\n"
            + "\n".join(offenders)
        )


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

    def test_help_is_not_truncated(self) -> None:
        result = _run(UNINSTALL_CHECK, "--help")
        assert "Exit codes:" in result.stdout, (
            "--help output stops before the exit-code block — widen the sed "
            f"range in uninstall-check.sh:\n{result.stdout}"
        )

    @pytest.mark.parametrize("bad_scope", ["all", "delete", "purge", ""])
    def test_invalid_scope_is_usage_error(self, bad_scope: str) -> None:
        result = _run(UNINSTALL_CHECK, "--scope", bad_scope)
        assert result.returncode == 2, (
            f"--scope {bad_scope!r} should be a usage error (exit 2), got {result.returncode}"
        )

    @pytest.mark.parametrize("scope", ["stop", "remove"])
    def test_valid_scopes_accepted(self, scope: str) -> None:
        """A valid scope must not be a usage error (exit 0 or 1, never 2)."""
        result = _run(UNINSTALL_CHECK, "--scope", scope)
        assert result.returncode in (0, 1), (
            f"--scope {scope} should be accepted (exit 0/1), got {result.returncode}:\n"
            f"{result.stderr}"
        )

    def test_wipe_scope_requires_explicit_madsci_dir(self) -> None:
        """--scope wipe asserts a directory is GONE, so a defaulted path is unsafe.

        ``./.madsci`` is relative to the CWD: from the wrong directory the check
        passes against a path that was never the lab's data directory,
        certifying a deletion that never happened.
        """
        result = _run(UNINSTALL_CHECK, "--scope", "wipe")
        assert result.returncode == 2, (
            "--scope wipe without --madsci-dir must be a usage error (exit 2), "
            f"got {result.returncode}:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )
        assert "--madsci-dir" in result.stderr, (
            f"the error must name the missing flag:\nstderr: {result.stderr}"
        )

    def test_wipe_scope_accepted_with_explicit_madsci_dir(self, tmp_path: Path) -> None:
        """An explicit path makes wipe a normal check again."""
        target = tmp_path / "absent-madsci"
        result = _run(
            UNINSTALL_CHECK,
            "--scope",
            "wipe",
            "--madsci-dir",
            str(target),
            "--managers",
            FREE_MANAGER_PORT,
            "--dashboard-port",
            FREE_DASHBOARD_PORT,
            timeout=60,
        )
        assert result.returncode in (0, 1), (
            f"--scope wipe with --madsci-dir should run, got {result.returncode}:\n"
            f"{result.stderr}"
        )
        assert str(target) in result.stdout, (
            f"the wipe check must report against the path it was given:\n{result.stdout}"
        )

    @pytest.mark.parametrize(
        "flag",
        [
            "--scope",
            "--managers",
            "--dashboard-port",
            "--madsci-dir",
            "--compose-project",
        ],
    )
    def test_value_flag_without_value_is_usage_error(self, flag: str) -> None:
        result = _run(UNINSTALL_CHECK, flag, timeout=10)
        assert result.returncode == 2, (
            f"{flag} with no value should be a usage error (exit 2), "
            f"got {result.returncode}:\nstderr: {result.stderr}"
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
        for scope in ("stop", "remove"):
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
        for scope in ("stop", "remove"):
            assert scope in lower, f"expected scope '{scope}' in uninstall.md"
        assert "uninstall-check.sh" in text
        assert ".madsci" in text
        assert "docker compose down" in text or "just down" in text
        # The Python uninstall is deleting the project-local venv — there is no
        # pip uninstall step, because nothing is installed outside it.
        assert ".venv" in text, (
            "uninstall.md must cover removing the project-local venv, which is "
            "the whole Python-side uninstall"
        )

    def test_madsci_data_deletion_is_handed_to_the_operator(self) -> None:
        """The skill resolves and prints the path; the operator runs the rm.

        Stopping containers and removing images are undone by a re-install.
        Dropping the bind-mounted databases is not, and the command runs as
        root against a path the agent inferred.
        """
        text = UNINSTALL_MD.read_text().lower()
        assert "operator-run" in text, (
            "uninstall.md §U3 must be framed as a hand-off, not an action the "
            "skill performs"
        )
        skill_text = SKILL_MD.read_text().lower()
        assert "never deletes `.madsci/` data" in skill_text, (
            "SKILL.md must state the no-delete rule where an agent will see it"
        )


class TestUninstallCheckAgainstFreeHost:
    """On a host with nothing on the target ports, a 'stop' teardown must verify clean."""

    def test_stop_scope_passes_when_port_free(self) -> None:
        if not (shutil.which("ss") or shutil.which("lsof")):
            pytest.skip("no listener probe (ss/lsof) available")
        result = _run(
            UNINSTALL_CHECK,
            "--scope",
            "stop",
            "--managers",
            FREE_MANAGER_PORT,
            "--dashboard-port",
            FREE_DASHBOARD_PORT,
            timeout=60,
        )
        # Container check may still find real MADSci containers if the lab is
        # up — so assert on the port lines only.
        assert f"port {FREE_MANAGER_PORT} free" in result.stdout, result.stdout
        assert f"port {FREE_DASHBOARD_PORT} free" in result.stdout, result.stdout


@pytest.mark.docker
class TestInstallCheckLiveStack:
    """Integration: verify install-check.sh against a running example lab.

    Skipped unless ``--docker-enabled`` (see tests/e2e/conftest.py).
    Requires the example lab to already be up (``just up`` / ``docker compose up -d``).
    """

    def test_passes_against_running_stack(self) -> None:
        result = _run_script(timeout=120)
        assert result.returncode == 0, (
            "install-check.sh should PASS against a running example lab.\n"
            "Is the stack up (`just up`)?\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        # Every default manager port and the dashboard should report a 200.
        for port in (*DEFAULT_MANAGER_PORTS, DASHBOARD_PORT):
            assert f"localhost:{port}/health → 200" in result.stdout, (
                f"expected a 200 health line for port {port}:\n{result.stdout}"
            )
        assert "Failed: 0" in result.stdout

    def test_container_import_names_a_service(self) -> None:
        """The container import check must resolve a compose SERVICE name."""
        result = _run_script(timeout=120)
        assert "in service '" in result.stdout, (
            "the container import check should report the compose service it "
            f"used:\n{result.stdout}"
        )


@pytest.mark.docker
class TestUninstallCheckLiveStack:
    """Integration: uninstall-check must FAIL while the example lab is still running.

    This is the mirror of the install-check live test: it proves the negative
    logic (teardown verification does not falsely pass when the stack is up).
    Skipped unless ``--docker-enabled``; requires the example lab to be UP.
    """

    def test_stop_scope_fails_against_running_stack(self) -> None:
        result = _run(UNINSTALL_CHECK, "--scope", "stop", timeout=60)
        assert result.returncode == 1, (
            "uninstall-check.sh should FAIL while the example lab is still running.\n"
            "Is the stack actually up (`just up`)?\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        # It should name at least one still-running MADSci container and a live port.
        assert "still running" in result.stdout, result.stdout
        assert "still has a listener" in result.stdout, result.stdout
