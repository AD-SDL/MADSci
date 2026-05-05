# ruff: noqa: S106, ARG001, PLC0415
"""Smoke tests for the ``madsci auth`` CLI command group.

These tests boot an in-memory Auth Manager, mount its FastAPI app behind an
``httpx.MockTransport`` so the CLI's ``AuthClient`` can talk to it without
opening a real socket, and exercise every subcommand.
"""

from __future__ import annotations

import json
from typing import Iterator

import httpx
import pytest
from click.testing import CliRunner
from fastapi.testclient import TestClient
from madsci.auth_manager.auth_server import AuthManager
from madsci.client.cli import madsci as cli
from madsci.common.db_handlers.postgres_handler import SQLiteHandler
from madsci.common.types.auth_types import AuthManagerSettings


@pytest.fixture
def patched_auth_client(monkeypatch: pytest.MonkeyPatch) -> Iterator[AuthManager]:
    """Mount AuthManager behind a MockTransport and patch AuthClient to use it."""
    settings = AuthManagerSettings(
        enable_registry_resolution=False,
        lab_id="lab-test",
        otel_enabled=False,
        argon2_time_cost=1,
        argon2_memory_cost=8 * 1024,
        argon2_parallelism=1,
    )
    mgr = AuthManager(settings=settings, postgres_handler=SQLiteHandler())
    mgr.bootstrap(admin_username="admin", admin_password="hunter2")
    test_client = TestClient(mgr.create_server())

    def _handler(request: httpx.Request) -> httpx.Response:
        # Translate httpx Request -> TestClient call
        method = request.method
        # Strip the http://localhost:8007 prefix to get path+query
        path = request.url.raw_path.decode("ascii")
        kwargs: dict = {"headers": dict(request.headers.items())}
        if request.content:
            kwargs["content"] = request.content
        resp = test_client.request(method, path, **kwargs)
        return httpx.Response(
            status_code=resp.status_code,
            headers=dict(resp.headers),
            content=resp.content,
        )

    transport = httpx.MockTransport(_handler)

    import madsci.client.auth_client as ac_mod

    original_init = ac_mod.AuthClient.__init__

    def patched_init(self, *args: object, **kwargs: object) -> None:
        original_init(self, *args, **kwargs)
        # Override the lazy http property to use the mock transport
        self._http = httpx.Client(
            base_url=self.auth_server_url,
            transport=transport,
            timeout=self._timeout,
        )

    monkeypatch.setattr(ac_mod.AuthClient, "__init__", patched_init)

    yield mgr


def _run(argv: list[str]) -> str:
    runner = CliRunner()
    result = runner.invoke(cli, argv, catch_exceptions=False)
    if result.exit_code != 0:
        raise AssertionError(
            f"CLI {argv} failed: exit={result.exit_code}\nout={result.output}\n"
        )
    return result.output


def test_user_list_and_create(patched_auth_client: AuthManager) -> None:
    out = _run(["auth", "user", "list"])
    users = json.loads(out)
    usernames = {u["username"] for u in users}
    assert "admin" in usernames

    out = _run(["auth", "user", "create", "alice", "--password", "x" * 12])
    created = json.loads(out)
    assert created["username"] == "alice"


def test_project_create_and_list(patched_auth_client: AuthManager) -> None:
    _run(["auth", "project", "create", "proj-cli"])
    out = _run(["auth", "project", "list"])
    names = {p["name"] for p in json.loads(out)}
    assert "proj-cli" in names


def test_keys_list_and_rotate(patched_auth_client: AuthManager) -> None:
    out = _run(["auth", "keys", "list"])
    n_before = len(json.loads(out))
    _run(["auth", "keys", "rotate"])
    out = _run(["auth", "keys", "list"])
    assert len(json.loads(out)) == n_before + 1


def test_manager_register_returns_credentials(
    patched_auth_client: AuthManager,
) -> None:
    out = _run(
        [
            "auth",
            "manager",
            "register",
            "--manager-id",
            "01HZZ" + "0" * 21,
        ]
    )
    body = json.loads(out)
    assert body["client_id"].startswith("sa-")
    assert body["client_secret"]


def test_node_register_returns_credentials(patched_auth_client: AuthManager) -> None:
    out = _run(
        [
            "auth",
            "node",
            "register",
            "--node-id",
            "01HZZ" + "0" * 21,
        ]
    )
    body = json.loads(out)
    assert body["client_id"].startswith("node-")


def test_bootstrap_rejects_password_flag() -> None:
    """The bootstrap CLI must NOT accept ``--password`` on argv (leaks via ps)."""
    runner = CliRunner()
    result = runner.invoke(cli, ["auth", "bootstrap", "--password", "x"])
    # Click rejects unknown options with exit code 2 + 'No such option' message
    assert result.exit_code != 0
    assert "no such option" in result.output.lower() or "--password" in result.output


def test_bootstrap_uses_env_var_for_password(monkeypatch) -> None:
    """``MADSCI_AUTH_BOOTSTRAP_PASSWORD`` env var is honored without prompting.

    We test the password-resolution helper directly rather than driving the
    full ``madsci auth bootstrap`` command, because the latter would call
    ``create_all_tables`` against the global ``SQLModel.metadata`` — which,
    when other test modules have been collected, includes tables from other
    managers (e.g., ``resource_history``) that real SQLite cannot create
    (composite PK + autoincrement). The injected ``SQLiteHandler`` used in
    the rest of the suite has a workaround for this; the bootstrap CLI's
    file-backed ``SQLAlchemyHandler`` does not.
    """
    from madsci.client.cli.commands.auth import (
        BOOTSTRAP_PASSWORD_ENV_VAR,
        _resolve_bootstrap_password,
    )

    monkeypatch.setenv(BOOTSTRAP_PASSWORD_ENV_VAR, "envvar-secret-x" * 2)
    pw = _resolve_bootstrap_password("envadmin")
    assert pw == "envvar-secret-x" * 2


def test_bootstrap_password_helper_fails_without_env_or_tty(monkeypatch) -> None:
    """No env var + no TTY => clear ClickException, NOT a silent fallback."""
    import click
    from madsci.client.cli.commands.auth import (
        BOOTSTRAP_PASSWORD_ENV_VAR,
        _resolve_bootstrap_password,
    )

    monkeypatch.delenv(BOOTSTRAP_PASSWORD_ENV_VAR, raising=False)
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    with pytest.raises(click.ClickException) as exc:
        _resolve_bootstrap_password("admin")
    assert BOOTSTRAP_PASSWORD_ENV_VAR in str(exc.value.message)


def test_credentials_rotate(patched_auth_client: AuthManager) -> None:
    reg = json.loads(
        _run(
            [
                "auth",
                "manager",
                "register",
                "--manager-id",
                "01HZZ" + "0" * 21,
            ]
        )
    )
    out = _run(["auth", "credentials", "rotate", reg["client_id"]])
    body = json.loads(out)
    assert body["client_id"] == reg["client_id"]
    assert body["client_secret"] != reg["client_secret"]
