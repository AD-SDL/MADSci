# ruff: noqa: S106, ARG001, PLC0415
"""Security-hardening regression tests for the Auth Manager.

Each test pins one of the merge-blocking findings from the security review
(see openspec/changes/auth-manager-security-hardening/).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import ipaddress
import json
import sqlite3
import threading
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from joserfc import jwt
from joserfc.jwk import RSAKey
from madsci.auth_manager.auth_server import AuthManager, _client_ip
from madsci.auth_manager.services.token_service import (
    TokenError,
    hash_refresh_token,
)
from madsci.auth_manager.tables import RefreshTokenTable
from madsci.common.db_handlers.postgres_handler import SQLiteHandler
from madsci.common.types.auth_types import (
    AuthManagerSettings,
)
from madsci.common.utils import new_ulid_str
from sqlmodel import Session, select

# ---------------------------------------------------------------------------
# Shared fixture (mirrors test_auth_server.server fixture)
# ---------------------------------------------------------------------------


@pytest.fixture
def server() -> tuple[AuthManager, TestClient]:
    settings = AuthManagerSettings(
        enable_registry_resolution=False,
        lab_id="lab-test",
        otel_enabled=False,
        argon2_time_cost=1,
        argon2_memory_cost=8 * 1024,
        argon2_parallelism=1,
    )
    # These tests exercise the raw HTTP surface; the dedicated
    # ``server_with_auth`` fixture below covers the middleware path.
    settings.auth_enabled = False
    settings.auth_required = False
    mgr = AuthManager(settings=settings, postgres_handler=SQLiteHandler())
    mgr.bootstrap(admin_username="admin", admin_password="hunter2")
    return mgr, TestClient(mgr.create_server())


# ---------------------------------------------------------------------------
# Tasks 1.3 / 1.4: algorithm pinning
# ---------------------------------------------------------------------------


def test_token_service_rejects_alg_none(server) -> None:
    mgr, _ = server
    # Build a JWT with alg=none and the right claims.
    header = (
        base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode())
        .rstrip(b"=")
        .decode()
    )
    now = int(datetime.now(timezone.utc).timestamp())
    payload = (
        base64.urlsafe_b64encode(
            json.dumps(
                {
                    "iss": str(mgr.settings.server_url).rstrip("/"),
                    "aud": "lab-test",
                    "sub": "anyone",
                    "iat": now,
                    "exp": now + 60,
                    "jti": new_ulid_str(),
                    "principal_type": "user",
                    "permissions": ["*"],
                }
            ).encode()
        )
        .rstrip(b"=")
        .decode()
    )
    fake = f"{header}.{payload}."

    with pytest.raises(TokenError) as exc:
        mgr._token_service.verify_token(fake)
    assert "disallowed alg" in str(exc.value)


def test_token_service_rejects_hs256_using_public_key(server) -> None:
    mgr, _ = server
    # Pull the public key PEM and construct an HS256 token using it as the
    # HMAC secret — the classic alg-confusion attack.
    signing_row = mgr._signing_key_service.get_signing_key()
    public_pem = signing_row.public_key_pem.encode()

    header = (
        base64.urlsafe_b64encode(
            json.dumps({"alg": "HS256", "typ": "JWT", "kid": signing_row.kid}).encode()
        )
        .rstrip(b"=")
        .decode()
    )
    now = int(datetime.now(timezone.utc).timestamp())
    payload = (
        base64.urlsafe_b64encode(
            json.dumps(
                {
                    "iss": str(mgr.settings.server_url).rstrip("/"),
                    "aud": "lab-test",
                    "sub": "anyone",
                    "iat": now,
                    "exp": now + 60,
                    "jti": new_ulid_str(),
                    "principal_type": "user",
                    "permissions": ["*"],
                }
            ).encode()
        )
        .rstrip(b"=")
        .decode()
    )
    signing_input = f"{header}.{payload}".encode()
    sig = hmac.new(public_pem, signing_input, hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(sig).rstrip(b"=").decode()
    forged = f"{header}.{payload}.{sig_b64}"

    with pytest.raises(TokenError) as exc:
        mgr._token_service.verify_token(forged)
    assert "disallowed alg" in str(exc.value)


def test_auth_client_rejects_alg_none() -> None:
    from madsci.client.auth_client import AuthClient, AuthClientError

    client = AuthClient(auth_server_url="http://example.invalid/")
    bad = (
        base64.urlsafe_b64encode(json.dumps({"alg": "none"}).encode())
        .rstrip(b"=")
        .decode()
        + ".eyJ9.X"
    )
    with pytest.raises(AuthClientError):
        client.verify_jwt(bad)


# ---------------------------------------------------------------------------
# Task 2.5: Auth Manager refuses to start without lab_id
# ---------------------------------------------------------------------------


def test_auth_manager_settings_default_to_auth_enabled() -> None:
    """Production safety: AuthManagerSettings defaults must enforce auth.

    Pins the fix for the security review's HIGH finding — a fresh
    deployment with no overrides must NOT expose admin endpoints
    unauthenticated.
    """
    settings = AuthManagerSettings(
        enable_registry_resolution=False, lab_id=new_ulid_str()
    )
    assert settings.auth_enabled is True
    assert settings.auth_required is True


def test_auth_manager_run_server_refuses_unsafe_config(tmp_path) -> None:
    """run_server() refuses to bind unless auth is enforced.

    Defense-in-depth: even if an operator deliberately overrode the safe
    defaults, the production startup path catches the misconfiguration
    rather than silently exposing the admin surface.
    """
    settings = AuthManagerSettings(
        enable_registry_resolution=False,
        lab_id=new_ulid_str(),
        otel_enabled=False,
        argon2_time_cost=1,
        argon2_memory_cost=8 * 1024,
        argon2_parallelism=1,
    )
    settings.auth_enabled = False
    settings.auth_required = False
    mgr = AuthManager(settings=settings, postgres_handler=SQLiteHandler())
    with pytest.raises(RuntimeError) as exc:
        mgr.run_server()
    assert "auth_enabled" in str(exc.value)


def test_auth_manager_refuses_to_start_without_lab_id() -> None:
    settings = AuthManagerSettings(
        enable_registry_resolution=False,
        lab_id=None,
        otel_enabled=False,
        argon2_time_cost=1,
        argon2_memory_cost=8 * 1024,
        argon2_parallelism=1,
    )
    with pytest.raises(RuntimeError) as exc:
        AuthManager(settings=settings, postgres_handler=SQLiteHandler())
    assert "lab_id" in str(exc.value)


# ---------------------------------------------------------------------------
# Tasks 3.5 / 3.6 / 10.2: atomic refresh-token consumption + rotated_to
# ---------------------------------------------------------------------------


def test_sqlite_supports_returning_required_for_atomic_refresh() -> None:
    # The atomic refresh-token consumption uses UPDATE...RETURNING via
    # SQLAlchemy core; SQLite >= 3.35 supports it, which is what our test
    # environment ships with.
    parts = sqlite3.sqlite_version.split(".")
    major, minor = int(parts[0]), int(parts[1])
    assert (major, minor) >= (3, 35), (
        f"SQLite >= 3.35 required for atomic refresh-token consumption; "
        f"have {sqlite3.sqlite_version}"
    )


def test_concurrent_refresh_at_most_one_succeeds(server) -> None:
    """Atomic claim invariant: no two concurrent refreshes both succeed.

    SQLite under thread contention can produce ``database is locked`` errors
    that surface as non-TokenError exceptions; we tolerate those as failures
    (not successes). The security-relevant property is that AT MOST one
    thread observes the row as freshly-revoked — never two.
    """
    mgr, client = server
    r = client.post(
        "/token",
        data={"grant_type": "password", "username": "admin", "password": "hunter2"},
    )
    refresh = r.json()["refresh_token"]

    successes: list[str] = []
    reuse_detected: list[str] = []
    other_errors: list[str] = []

    def worker() -> None:
        try:
            new_id = new_ulid_str()
            row = mgr._token_service.consume_refresh_token(
                refresh, rotated_to_token_id=new_id
            )
            successes.append(row.token_id)
        except TokenError as e:
            if "reuse" in str(e):
                reuse_detected.append(str(e))
            else:
                other_errors.append(str(e))
        except Exception as e:  # pragma: no cover  (SQLite contention)
            other_errors.append(f"{type(e).__name__}: {e}")

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(successes) <= 1, (
        f"expected at most one success, got {len(successes)}:"
        f" successes={successes} reuse={reuse_detected} other={other_errors}"
    )
    # In the common case, exactly one succeeds and the rest see reuse.
    if successes:
        assert reuse_detected, (
            f"a winner means losers should see reuse; got {reuse_detected}"
            f" + other_errors={other_errors}"
        )


def test_rotated_to_links_parent_to_child(server) -> None:
    mgr, client = server
    r = client.post(
        "/token",
        data={"grant_type": "password", "username": "admin", "password": "hunter2"},
    )
    parent_refresh = r.json()["refresh_token"]
    parent_hash = hash_refresh_token(parent_refresh)

    # Trigger rotation
    r = client.post(
        "/token",
        data={"grant_type": "refresh_token", "refresh_token": parent_refresh},
    )
    assert r.status_code == 200
    new_refresh = r.json()["refresh_token"]
    new_hash = hash_refresh_token(new_refresh)

    engine = mgr._postgres_handler.get_engine()
    with Session(engine) as session:
        parent = session.exec(
            select(RefreshTokenTable).where(RefreshTokenTable.token_hash == parent_hash)
        ).first()
        child = session.exec(
            select(RefreshTokenTable).where(RefreshTokenTable.token_hash == new_hash)
        ).first()
    assert parent is not None
    assert child is not None
    assert parent.rotated_to == child.token_id


# ---------------------------------------------------------------------------
# Tasks 4.6 / 5.3: admin authorization (auth-required mode)
# ---------------------------------------------------------------------------


@pytest.fixture
def server_with_auth() -> tuple[AuthManager, TestClient, str]:
    """An Auth Manager with AuthMiddleware installed, plus an admin token.

    Uses the production defaults (``auth_enabled=True``,
    ``auth_required=True``) and lets ``AuthManager._setup_auth_middleware``
    install the middleware automatically. The Auth Manager's middleware is
    self-verifying (uses its own ``TokenService`` rather than a remote
    ``AuthClient``), so no HTTP transport plumbing is needed.
    """
    # OwnershipInfo.from_jwt_claims validates lab_id as a ULID, so the
    # auth-enabled middleware path requires a real ULID (the simpler tests
    # above don't pass through the middleware so they can use "lab-test").
    lab_ulid = new_ulid_str()
    settings = AuthManagerSettings(
        enable_registry_resolution=False,
        lab_id=lab_ulid,
        otel_enabled=False,
        argon2_time_cost=1,
        argon2_memory_cost=8 * 1024,
        argon2_parallelism=1,
    )
    # Defaults are now True, but be explicit so the test reads as a
    # behavioral assertion, not a default-coupling.
    settings.auth_enabled = True
    settings.auth_required = True
    mgr = AuthManager(settings=settings, postgres_handler=SQLiteHandler())
    mgr.bootstrap(admin_username="admin", admin_password="hunter2")
    test_client = TestClient(mgr.create_server())

    # Acquire admin token
    r = test_client.post(
        "/token",
        data={"grant_type": "password", "username": "admin", "password": "hunter2"},
    )
    assert r.status_code == 200, r.text
    admin_token = r.json()["access_token"]
    return mgr, test_client, admin_token


def test_admin_endpoints_reject_unauthenticated(server_with_auth) -> None:
    _, client, _ = server_with_auth
    paths = [
        ("GET", "/users"),
        ("POST", "/users"),
        ("GET", "/projects"),
        ("POST", "/projects"),
        ("GET", "/roles"),
        ("POST", "/roles"),
        ("POST", "/roles/grant"),
        ("POST", "/service-accounts"),
        ("POST", "/node-identities"),
        ("POST", "/credentials/foo/rotate"),
        ("POST", "/keys/rotate"),
        ("GET", "/keys"),
        ("DELETE", "/keys/anything"),
    ]
    for method, path in paths:
        r = client.request(method, path, json={})
        assert r.status_code == 401, (
            f"{method} {path} should be 401, got {r.status_code}"
        )


def test_admin_endpoints_require_permission(server_with_auth) -> None:
    _mgr, client, admin_token = server_with_auth

    # Create a user with no permissions
    r = client.post(
        "/users",
        json={"username": "bob", "password": "x" * 12},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200, r.text

    # bob has no roles, so login + call admin endpoint = 403
    r = client.post(
        "/token",
        data={"grant_type": "password", "username": "bob", "password": "x" * 12},
    )
    bob_token = r.json()["access_token"]

    r = client.get("/users", headers={"Authorization": f"Bearer {bob_token}"})
    assert r.status_code == 403


def test_admin_endpoints_succeed_with_admin_token(server_with_auth) -> None:
    _, client, admin_token = server_with_auth
    r = client.get("/users", headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200


def test_token_endpoint_remains_public(server_with_auth) -> None:
    _, client, _ = server_with_auth
    r = client.post(
        "/token",
        data={"grant_type": "password", "username": "admin", "password": "hunter2"},
    )
    assert r.status_code == 200


def test_jwks_remains_public(server_with_auth) -> None:
    _, client, _ = server_with_auth
    r = client.get("/.well-known/jwks.json")
    assert r.status_code == 200


def test_unauthenticated_introspect_returns_inactive(server_with_auth) -> None:
    _, client, admin_token = server_with_auth
    # Use admin_token as the token to introspect; unauthenticated caller
    r = client.post("/introspect", json={"token": admin_token})
    assert r.status_code == 200
    assert r.json() == {"active": False}


def test_authenticated_privileged_introspect_returns_claims(server_with_auth) -> None:
    _, client, admin_token = server_with_auth
    # admin has * permissions
    r = client.post(
        "/introspect",
        json={"token": admin_token},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["active"] is True
    assert body["sub"]


def test_unauthenticated_revoke_is_rejected(server_with_auth) -> None:
    _, client, admin_token = server_with_auth
    r = client.post("/revoke", json={"token": admin_token})
    assert r.status_code == 401


def test_self_revocation_succeeds(server_with_auth) -> None:
    _, client, admin_token = server_with_auth
    r = client.post(
        "/revoke",
        json={"token": admin_token},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200


def test_cross_principal_revoke_requires_permission(server_with_auth) -> None:
    _mgr, client, admin_token = server_with_auth
    # Create bob without any auth.token.revoke permission
    client.post(
        "/users",
        json={"username": "bob2", "password": "x" * 12},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    bob_token = client.post(
        "/token",
        data={"grant_type": "password", "username": "bob2", "password": "x" * 12},
    ).json()["access_token"]

    # bob tries to revoke admin's token -> 403
    r = client.post(
        "/revoke",
        json={"token": admin_token},
        headers={"Authorization": f"Bearer {bob_token}"},
    )
    assert r.status_code == 403


def test_cross_principal_refresh_token_revoke_requires_permission(
    server_with_auth,
) -> None:
    """Refresh-token revocation honors the same self-vs-other rule.

    Pins the security review's filtered ``/revoke refresh-token path lacks
    self-vs-other check`` finding — without this, bob with knowledge of
    admin's refresh token could force-sign-out admin without holding
    ``auth.token.revoke``.
    """
    _mgr, client, admin_token = server_with_auth
    # Get admin's refresh token
    admin_refresh = client.post(
        "/token",
        data={
            "grant_type": "password",
            "username": "admin",
            "password": "hunter2",
        },
    ).json()["refresh_token"]

    # bob (no permissions) logs in
    client.post(
        "/users",
        json={"username": "bob3", "password": "x" * 12},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    bob_token = client.post(
        "/token",
        data={"grant_type": "password", "username": "bob3", "password": "x" * 12},
    ).json()["access_token"]

    # bob tries to revoke admin's refresh token -> 403
    r = client.post(
        "/revoke",
        json={"refresh_token": admin_refresh},
        headers={"Authorization": f"Bearer {bob_token}"},
    )
    assert r.status_code == 403

    # Admin's refresh token still works
    r = client.post(
        "/token",
        data={"grant_type": "refresh_token", "refresh_token": admin_refresh},
    )
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# AuthClient iss/aud validation (security review filtered defense-in-depth)
# ---------------------------------------------------------------------------


def test_auth_client_rejects_token_with_wrong_audience(server) -> None:
    """AuthClient.verify_jwt enforces ``expected_audience`` when configured."""
    from madsci.client.auth_client import AuthClient, AuthClientError

    mgr, _ = server
    # Issue a token via the manager (aud = "lab-test")
    signing = mgr._signing_key_service.get_signing_key()
    signing_key = RSAKey.import_key(
        signing.private_key_pem, parameters={"kid": signing.kid}
    )
    now = int(datetime.now(timezone.utc).timestamp())
    claims = {
        "iss": str(mgr.settings.server_url).rstrip("/"),
        "aud": "lab-test",
        "sub": "u",
        "iat": now,
        "exp": now + 600,
        "jti": new_ulid_str(),
        "principal_type": "user",
        "permissions": ["*"],
    }
    header = {"alg": "RS256", "kid": signing.kid, "typ": "JWT"}
    token = jwt.encode(header, claims, signing_key, algorithms=["RS256"])

    jwks_dict = mgr._signing_key_service.jwks()

    # AuthClient configured for a DIFFERENT audience must reject. The
    # underlying joserfc raises InvalidClaimError; AuthClient propagates
    # whatever the JOSE library raises for non-signature failures.
    client = AuthClient(
        auth_server_url="http://example.invalid/",
        expected_audience="some-other-lab",
    )
    # Stub jwks() entirely so retry-on-failure doesn't try to HTTP-fetch
    client.jwks = lambda **_: jwks_dict  # type: ignore[method-assign]
    with pytest.raises((AuthClientError, Exception)) as exc:
        client.verify_jwt(token)
    assert "aud" in str(exc.value).lower() or "audience" in str(exc.value).lower()

    # Same client with the correct audience accepts it
    client.close()
    client = AuthClient(
        auth_server_url="http://example.invalid/",
        expected_audience="lab-test",
    )
    client.jwks = lambda **_: jwks_dict  # type: ignore[method-assign]
    decoded = client.verify_jwt(token)
    assert decoded.aud == "lab-test"


# ---------------------------------------------------------------------------
# Task 7.4: clock-skew leeway
# ---------------------------------------------------------------------------


def test_token_with_iat_slightly_in_future_verifies(server) -> None:
    mgr, _ = server
    # Issue a token by hand with iat 5s in the future
    signing = mgr._signing_key_service.get_signing_key()
    now = int(datetime.now(timezone.utc).timestamp())
    claims = {
        "iss": str(mgr.settings.server_url).rstrip("/"),
        "aud": "lab-test",
        "sub": "admin",
        "iat": now + 5,
        "nbf": now + 5,
        "exp": now + 600,
        "jti": new_ulid_str(),
        "principal_type": "user",
        "permissions": ["*"],
    }
    header = {"alg": "RS256", "kid": signing.kid, "typ": "JWT"}
    signing_key = RSAKey.import_key(
        signing.private_key_pem, parameters={"kid": signing.kid}
    )
    token = jwt.encode(header, claims, signing_key, algorithms=["RS256"])
    # Default leeway is 30s; should succeed.
    decoded = mgr._token_service.verify_token(token)
    assert decoded.sub == "admin"


def test_expired_token_outside_leeway_is_rejected(server) -> None:
    mgr, _ = server
    signing = mgr._signing_key_service.get_signing_key()
    now = int(datetime.now(timezone.utc).timestamp())
    claims = {
        "iss": str(mgr.settings.server_url).rstrip("/"),
        "aud": "lab-test",
        "sub": "admin",
        "iat": now - 600,
        "exp": now - 60,  # 60s in past, beyond 30s leeway
        "jti": new_ulid_str(),
        "principal_type": "user",
        "permissions": ["*"],
    }
    header = {"alg": "RS256", "kid": signing.kid, "typ": "JWT"}
    signing_key = RSAKey.import_key(
        signing.private_key_pem, parameters={"kid": signing.kid}
    )
    token = jwt.encode(header, claims, signing_key, algorithms=["RS256"])
    with pytest.raises(TokenError):
        mgr._token_service.verify_token(token)


# ---------------------------------------------------------------------------
# Task 8.5: audit failure-closed for token issuance
# ---------------------------------------------------------------------------


def test_audit_write_failure_propagates(server, monkeypatch) -> None:
    """Audit write failure during token issuance MUST NOT return a token.

    The request either fails outright (5xx) or raises through TestClient —
    either way, no token leaves the server.
    """
    _, client = server

    from madsci.auth_manager.services import audit_logger as al_mod

    def boom(self, *args, **kwargs):
        raise RuntimeError("simulated audit DB failure")

    monkeypatch.setattr(al_mod.AuditLogger, "log", boom)

    try:
        r = client.post(
            "/token",
            data={
                "grant_type": "password",
                "username": "admin",
                "password": "hunter2",
            },
        )
    except RuntimeError as exc:
        # FastAPI/TestClient may propagate the unhandled exception; that's
        # an acceptable failure-closed signal — the client never sees a token.
        assert "simulated audit" in str(exc)
        return
    # If we got a response, it must NOT be a successful token grant.
    assert r.status_code >= 400, f"audit failure leaked a token: {r.text}"


# ---------------------------------------------------------------------------
# Task 9.4: X-Forwarded-For trust gating
# ---------------------------------------------------------------------------


class _FakeRequest:
    def __init__(self, host: str | None, xff: str | None) -> None:
        self.headers = {"x-forwarded-for": xff} if xff else {}
        self.client = type("C", (), {"host": host})() if host else None


def test_xff_ignored_by_default() -> None:
    req = _FakeRequest("10.0.0.1", "1.2.3.4")
    assert _client_ip(req) == "10.0.0.1"


def test_xff_honored_when_trusted() -> None:
    req = _FakeRequest("10.0.0.1", "1.2.3.4")
    assert _client_ip(req, trust_forwarded_for=True) == "1.2.3.4"


def test_xff_falls_back_to_socket_on_garbage() -> None:
    req = _FakeRequest("10.0.0.1", "not-an-ip")
    assert _client_ip(req, trust_forwarded_for=True) == "10.0.0.1"


def test_xff_first_value_used() -> None:
    req = _FakeRequest("10.0.0.1", "1.2.3.4, 5.6.7.8")
    assert _client_ip(req, trust_forwarded_for=True) == "1.2.3.4"
    # Sanity: result is a valid IP
    ipaddress.ip_address("1.2.3.4")
