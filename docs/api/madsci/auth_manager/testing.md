Module madsci.auth_manager.testing
==================================
Reusable in-memory Auth Manager fixture and helpers for tests.

Importable by any test suite that needs a real Auth Manager wired up against
``SQLiteHandler`` plus an ``AuthClient`` whose HTTP transport is bound to
the in-memory FastAPI app via ``httpx.MockTransport``.

Functions
---------

`in_memory_auth(*, lab_id: str | None = None) ‑> Iterator[tuple[madsci.auth_manager.auth_server.AuthManager, madsci.client.auth_client.AuthClient]]`
:   Context-managed (mgr, client) pair for one-off use.

`make_auth_client(mgr: AuthManager) ‑> madsci.client.auth_client.AuthClient`
:   Build an AuthClient whose HTTP transport is bound to ``mgr``.

`make_auth_manager(*, lab_id: str | None = None, admin_username: str = 'admin', admin_password: str = 'hunter2') ‑> madsci.auth_manager.auth_server.AuthManager`
:   Build a fully-bootstrapped in-memory AuthManager.

`make_mock_transport(mgr: AuthManager) ‑> httpx.MockTransport`
:   Build an httpx MockTransport that forwards requests to ``mgr``.