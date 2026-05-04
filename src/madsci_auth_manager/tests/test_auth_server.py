# ruff: noqa: S105, S106
"""Integration tests for the AuthManager FastAPI server."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from madsci.auth_manager.auth_server import AuthManager
from madsci.common.db_handlers.postgres_handler import SQLiteHandler
from madsci.common.types.auth_types import AuthManagerSettings
from madsci.common.utils import new_ulid_str


@pytest.fixture
def server() -> tuple[AuthManager, TestClient]:
    settings = AuthManagerSettings(
        enable_registry_resolution=False,
        lab_id="lab-test",
        otel_enabled=False,
        # speed up tests
        argon2_time_cost=1,
        argon2_memory_cost=8 * 1024,
        argon2_parallelism=1,
    )
    mgr = AuthManager(settings=settings, postgres_handler=SQLiteHandler())
    mgr.bootstrap(admin_username="admin", admin_password="hunter2")
    app = mgr.create_server()
    return mgr, TestClient(app)


def test_health(server) -> None:
    _, client = server
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["healthy"] is True


def test_jwks(server) -> None:
    _, client = server
    r = client.get("/.well-known/jwks.json")
    assert r.status_code == 200
    body = r.json()
    assert len(body["keys"]) == 1
    assert body["keys"][0]["kty"] == "RSA"


def test_password_grant_and_refresh(server) -> None:
    _, client = server
    r = client.post(
        "/token",
        data={
            "grant_type": "password",
            "username": "admin",
            "password": "hunter2",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["token_type"] == "Bearer"
    access = body["access_token"]
    refresh = body["refresh_token"]
    assert access and refresh

    # Introspect
    r = client.post("/introspect", json={"token": access})
    assert r.status_code == 200
    intro = r.json()
    assert intro["active"] is True
    assert intro["principal_type"] == "user"

    # Refresh
    r = client.post(
        "/token", data={"grant_type": "refresh_token", "refresh_token": refresh}
    )
    assert r.status_code == 200
    new_body = r.json()
    assert new_body["access_token"] != access
    assert new_body["refresh_token"] != refresh

    # Reuse-detection
    r = client.post(
        "/token", data={"grant_type": "refresh_token", "refresh_token": refresh}
    )
    assert r.status_code == 401


def test_unsupported_grant_type(server) -> None:
    _, client = server
    r = client.post("/token", data={"grant_type": "authorization_code"})
    assert r.status_code == 400
    assert r.json()["detail"]["error"] == "unsupported_grant_type"


def test_bad_password(server) -> None:
    _, client = server
    r = client.post(
        "/token",
        data={"grant_type": "password", "username": "admin", "password": "wrong"},
    )
    assert r.status_code == 401


def test_inactive_user(server) -> None:
    _, client = server
    # Create a user, then deactivate
    new_pw = "x" * 12
    r = client.post("/users", json={"username": "bob", "password": new_pw})
    assert r.status_code == 200
    user_id = r.json()["user_id"]
    r = client.patch(f"/users/{user_id}", json={"is_active": False})
    assert r.status_code == 200
    r = client.post(
        "/token",
        data={"grant_type": "password", "username": "bob", "password": new_pw},
    )
    assert r.status_code == 401


def test_duplicate_username_409(server) -> None:
    _, client = server
    r = client.post("/users", json={"username": "admin", "password": "x" * 12})
    assert r.status_code == 409


def test_revoke_access_token(server) -> None:
    _, client = server
    r = client.post(
        "/token",
        data={"grant_type": "password", "username": "admin", "password": "hunter2"},
    )
    access = r.json()["access_token"]
    r = client.post("/revoke", json={"token": access})
    assert r.status_code == 200

    # Now introspection says inactive
    r = client.post("/introspect", json={"token": access})
    assert r.json()["active"] is False


def test_deny_list_etag(server) -> None:
    _, client = server
    r1 = client.get("/deny-list")
    assert r1.status_code == 200
    etag = r1.headers["ETag"]

    # Conditional fetch
    r2 = client.get("/deny-list", headers={"if-none-match": etag})
    assert r2.status_code == 304


def test_keys_health(server) -> None:
    _, client = server
    r = client.get("/health/keys")
    assert r.status_code == 200
    body = r.json()
    assert body["active_keys"] == 1
    assert body["signing_kid"]


def test_key_rotate(server) -> None:
    _, client = server
    r = client.get("/keys")
    n_before = len(r.json())
    r = client.post("/keys/rotate")
    assert r.status_code == 200
    r = client.get("/keys")
    assert len(r.json()) == n_before + 1


def test_register_service_account_and_client_credentials(server) -> None:
    _, client = server
    r = client.post(
        "/service-accounts", json={"manager_id": new_ulid_str(), "role_ids": []}
    )
    assert r.status_code == 200, r.text
    cred = r.json()
    cid, secret = cred["client_id"], cred["client_secret"]

    r = client.post(
        "/token",
        data={
            "grant_type": "client_credentials",
            "client_id": cid,
            "client_secret": secret,
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["access_token"]
    # No refresh token for client_credentials
    assert body.get("refresh_token") is None


def test_register_node_and_client_credentials(server) -> None:
    _, client = server
    r = client.post(
        "/node-identities",
        json={"node_id": new_ulid_str(), "workcell_id": new_ulid_str()},
    )
    assert r.status_code == 200, r.text
    cred = r.json()
    r = client.post(
        "/token",
        data={
            "grant_type": "client_credentials",
            "client_id": cred["client_id"],
            "client_secret": cred["client_secret"],
        },
    )
    assert r.status_code == 200


def test_create_role_and_grant(server) -> None:
    _, client = server
    r = client.post(
        "/roles",
        json={
            "name": "test_role",
            "permissions": ["test.read"],
        },
    )
    assert r.status_code == 200
    role_id = r.json()["role_id"]

    r = client.get("/roles")
    names = [x["name"] for x in r.json()]
    assert "test_role" in names

    # Grant globally to admin user
    users = client.get("/users").json()
    admin_id = next(u["user_id"] for u in users if u["username"] == "admin")
    r = client.post(
        "/roles/grant",
        json={"role_id": role_id, "user_id": admin_id},
    )
    assert r.status_code == 200


def test_project_create_and_membership(server) -> None:
    _, client = server
    r = client.post("/projects", json={"name": "proj-x"})
    pid = r.json()["project_id"]

    users = client.get("/users").json()
    admin_id = next(u["user_id"] for u in users if u["username"] == "admin")
    roles = client.get("/roles").json()
    role_id = next(r["role_id"] for r in roles if r["name"] == "experimenter")

    r = client.post(
        f"/projects/{pid}/members",
        json={"user_id": admin_id, "role_id": role_id},
    )
    assert r.status_code == 200

    # Token for admin should now include project_ids
    r = client.post(
        "/token",
        data={"grant_type": "password", "username": "admin", "password": "hunter2"},
    )
    intro = client.post("/introspect", json={"token": r.json()["access_token"]}).json()
    assert pid in intro["project_ids"]


def test_credential_rotation(server) -> None:
    _, client = server
    r = client.post(
        "/service-accounts", json={"manager_id": new_ulid_str(), "role_ids": []}
    )
    cid, old_secret = r.json()["client_id"], r.json()["client_secret"]
    r = client.post(f"/credentials/{cid}/rotate")
    new_secret = r.json()["client_secret"]
    assert new_secret != old_secret

    # Old secret no longer works
    r = client.post(
        "/token",
        data={
            "grant_type": "client_credentials",
            "client_id": cid,
            "client_secret": old_secret,
        },
    )
    assert r.status_code == 401

    # New secret does
    r = client.post(
        "/token",
        data={
            "grant_type": "client_credentials",
            "client_id": cid,
            "client_secret": new_secret,
        },
    )
    assert r.status_code == 200
