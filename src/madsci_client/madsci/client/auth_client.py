"""Client library for the MADSci Auth Manager.

Provides programmatic access to the Auth Manager: token acquisition (password,
refresh, client_credentials), introspection, JWKS-cached JWT verification,
deny-list polling, and the admin surface (users, projects, roles,
service-accounts, node identities, signing keys).

The ``AuthClient`` is also installable into the ambient context via
``auth_client_context()`` so other service clients pick up bearer tokens
automatically (see ``madsci.common.auth_context``).
"""

from __future__ import annotations

import base64
import contextlib
import json
import threading
import time
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
from joserfc import jwt as jose_jwt
from joserfc.jwk import KeySet
from joserfc.jwt import JWTClaimsRegistry
from madsci.common.types.auth_types import JWTClaims, TokenResponse
from pydantic import AnyUrl


class AuthClientError(Exception):
    """Raised on auth-client failures."""


class AuthClient:
    """Synchronous client for the Auth Manager.

    The client is intentionally synchronous to mirror the rest of MADSci's
    service clients. Concurrency-sensitive call sites can wrap it with their
    own thread pool / asyncio.to_thread.
    """

    # JWT verification is hard-pinned to RS256 (mirrors TokenService).
    ALLOWED_ALGORITHMS: tuple[str, ...] = ("RS256",)

    def __init__(
        self,
        auth_server_url: AnyUrl | str,
        *,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        jwks_ttl_seconds: int = 300,
        deny_list_poll_interval: int = 30,
        refresh_buffer_seconds: int = 60,
        timeout: float = 10.0,
        clock_skew_seconds: int = 30,
    ) -> None:
        """Initialize the client with optional pre-existing tokens / credentials."""
        self.auth_server_url = str(auth_server_url).rstrip("/")
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._client_id = client_id
        self._client_secret = client_secret
        self._access_claims: Optional[JWTClaims] = None
        self._timeout = timeout
        self._http: Optional[httpx.Client] = None
        self._async_http: Optional[httpx.AsyncClient] = None
        self._lock = threading.RLock()
        self._clock_skew = clock_skew_seconds

        # JWKS cache
        self._jwks_ttl = jwks_ttl_seconds
        self._jwks: Optional[dict] = None
        self._jwks_fetched_at: float = 0.0

        # Deny list cache
        self._deny_list_poll = deny_list_poll_interval
        self._deny_etag: Optional[str] = None
        self._deny_set: set[str] = set()
        self._deny_fetched_at: float = 0.0

        # Auto-refresh tuning
        self._refresh_buffer = refresh_buffer_seconds

    # ------------------------------------------------------------------
    # HTTP plumbing
    # ------------------------------------------------------------------

    @property
    def http(self) -> httpx.Client:
        """Lazily-initialized synchronous httpx client."""
        if self._http is None:
            self._http = httpx.Client(
                base_url=self.auth_server_url, timeout=self._timeout
            )
        return self._http

    @property
    def async_http(self) -> httpx.AsyncClient:
        """Lazily-initialized async httpx client (mirrors ``http``)."""
        if self._async_http is None:
            self._async_http = httpx.AsyncClient(
                base_url=self.auth_server_url, timeout=self._timeout
            )
        return self._async_http

    def close(self) -> None:
        """Release the synchronous HTTP connection pool. Idempotent."""
        with contextlib.suppress(Exception):
            if self._http is not None:
                self._http.close()
                self._http = None
        # Async client must be closed via async context; best-effort here

    def __enter__(self) -> AuthClient:
        """Enter context-manager scope."""
        return self

    def __exit__(self, *_: Any) -> None:
        """Close the underlying HTTP client on exit."""
        self.close()

    # ------------------------------------------------------------------
    # Token acquisition
    # ------------------------------------------------------------------

    def login(self, username: str, password: str) -> TokenResponse:
        """Exchange username/password for access + refresh tokens (password grant)."""
        r = self.http.post(
            "/token",
            data={
                "grant_type": "password",
                "username": username,
                "password": password,
            },
        )
        r.raise_for_status()
        token = TokenResponse(**r.json())
        self._access_token = token.access_token
        self._refresh_token = token.refresh_token
        self._access_claims = self._parse_unverified(token.access_token)
        return token

    def client_credentials_login(
        self, client_id: str, client_secret: str
    ) -> TokenResponse:
        """Exchange client_id/client_secret for an access token (no refresh token)."""
        r = self.http.post(
            "/token",
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            },
        )
        r.raise_for_status()
        token = TokenResponse(**r.json())
        self._client_id = client_id
        self._client_secret = client_secret
        self._access_token = token.access_token
        self._refresh_token = token.refresh_token
        self._access_claims = self._parse_unverified(token.access_token)
        return token

    def refresh(self) -> TokenResponse:
        """Exchange the cached refresh token for a fresh access + refresh pair."""
        if not self._refresh_token:
            if self._client_id and self._client_secret:
                return self.client_credentials_login(
                    self._client_id, self._client_secret
                )
            raise AuthClientError("no refresh_token available")
        r = self.http.post(
            "/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": self._refresh_token,
            },
        )
        r.raise_for_status()
        token = TokenResponse(**r.json())
        self._access_token = token.access_token
        self._refresh_token = token.refresh_token
        self._access_claims = self._parse_unverified(token.access_token)
        return token

    @property
    def access_token(self) -> Optional[str]:
        """The currently-cached access token, or None if not logged in."""
        return self._access_token

    def get_access_token(self) -> str:
        """Return a non-expired access token, refreshing transparently."""
        with self._lock:
            if self._access_token is None:
                raise AuthClientError("no access token; call login() first")
            if self._near_expiry():
                self.refresh()
            return self._access_token

    def _near_expiry(self) -> bool:
        if self._access_claims is None:
            return False
        now = int(datetime.now(timezone.utc).timestamp())
        return self._access_claims.exp - now <= self._refresh_buffer

    # ------------------------------------------------------------------
    # JWKS / verify
    # ------------------------------------------------------------------

    def jwks(self, *, force_refresh: bool = False) -> dict:
        """Return the JWKS document, fetching from the Auth Manager if the cache is stale."""
        with self._lock:
            now = time.time()
            if (
                force_refresh
                or self._jwks is None
                or (now - self._jwks_fetched_at) > self._jwks_ttl
            ):
                r = self.http.get("/.well-known/jwks.json")
                r.raise_for_status()
                self._jwks = r.json()
                self._jwks_fetched_at = now
            return self._jwks

    def verify_jwt(self, token: str) -> JWTClaims:
        """Verify a JWT against the cached JWKS and the cached deny-list.

        On signature failure, the JWKS cache is force-refreshed and verification
        is retried once.
        """
        # Reject anything that isn't on our allowlist before joserfc touches it.
        self._enforce_algorithm(token)
        for attempt in range(2):
            jwks_dict = self.jwks(force_refresh=attempt > 0)
            try:
                key_set = KeySet.import_key_set(jwks_dict)
                decoded = jose_jwt.decode(
                    token, key_set, algorithms=list(self.ALLOWED_ALGORITHMS)
                )
                JWTClaimsRegistry(leeway=self._clock_skew).validate(decoded.claims)
                claims = JWTClaims(**decoded.claims)
                # Deny-list enforcement
                self._poll_deny_list_if_due()
                if claims.jti in self._deny_set:
                    raise AuthClientError("token revoked")
                return claims
            except AuthClientError:
                raise
            except Exception:
                if attempt == 1:
                    raise
        raise AuthClientError("verify_jwt: unreachable")

    def _enforce_algorithm(self, token: str) -> None:
        """Reject tokens whose JWS header alg is not in ALLOWED_ALGORITHMS."""
        try:
            header_b64 = token.split(".", maxsplit=1)[0]
            padding = 4 - (len(header_b64) % 4)
            if padding != 4:
                header_b64 += "=" * padding
            header = json.loads(base64.urlsafe_b64decode(header_b64))
            alg = header.get("alg")
        except Exception as e:
            raise AuthClientError("invalid_token: malformed header") from e
        if alg not in self.ALLOWED_ALGORITHMS:
            raise AuthClientError(f"invalid_token: disallowed alg {alg!r}")

    def _parse_unverified(self, token: str) -> Optional[JWTClaims]:
        """Parse JWT claims without signature verification. Used for refresh-buffer logic."""
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None
            payload_segment = parts[1]
            padding = 4 - (len(payload_segment) % 4)
            if padding != 4:
                payload_segment += "=" * padding
            payload = json.loads(base64.urlsafe_b64decode(payload_segment))
            return JWTClaims(**payload)
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Introspect / revoke
    # ------------------------------------------------------------------

    def introspect(self, token: str) -> dict:
        """Call the RFC 7662 introspection endpoint for ``token``."""
        r = self.http.post("/introspect", json={"token": token})
        r.raise_for_status()
        return r.json()

    def revoke(
        self,
        *,
        token: Optional[str] = None,
        refresh_token: Optional[str] = None,
    ) -> None:
        """Revoke an access token and/or refresh token at the Auth Manager."""
        body: dict[str, Any] = {}
        if token is not None:
            body["token"] = token
        if refresh_token is not None:
            body["refresh_token"] = refresh_token
        r = self.http.post("/revoke", json=body)
        r.raise_for_status()

    # ------------------------------------------------------------------
    # Deny-list polling
    # ------------------------------------------------------------------

    def _poll_deny_list_if_due(self) -> None:
        now = time.time()
        if (now - self._deny_fetched_at) < self._deny_list_poll:
            return
        self._fetch_deny_list()

    def _fetch_deny_list(self) -> None:
        headers = {}
        if self._deny_etag:
            headers["If-None-Match"] = f'"{self._deny_etag}"'
        try:
            r = self.http.get("/deny-list", headers=headers)
        except Exception:
            return
        if r.status_code == 304:
            self._deny_fetched_at = time.time()
            return
        if r.status_code != 200:
            return
        body = r.json()
        self._deny_etag = body.get("etag")
        self._deny_set = {e["jti"] for e in body.get("entries", [])}
        self._deny_fetched_at = time.time()

    def force_deny_list_refresh(self) -> None:
        """Force an immediate deny-list fetch (used after on-401 retries)."""
        self._deny_fetched_at = 0.0
        self._fetch_deny_list()

    # ------------------------------------------------------------------
    # Admin surface (auth required)
    # ------------------------------------------------------------------

    def _admin_headers(self) -> dict[str, str]:
        if self._access_token:
            return {"Authorization": f"Bearer {self._access_token}"}
        return {}

    # --- Users
    def create_user(
        self, username: str, password: str, email: Optional[str] = None
    ) -> dict:
        """Create a new user (``POST /users``)."""
        r = self.http.post(
            "/users",
            json={"username": username, "password": password, "email": email},
            headers=self._admin_headers(),
        )
        r.raise_for_status()
        return r.json()

    def list_users(self) -> list[dict]:
        """List all users (``GET /users``)."""
        r = self.http.get("/users", headers=self._admin_headers())
        r.raise_for_status()
        return r.json()

    def update_user(self, user_id: str, **fields: Any) -> dict:
        """Patch a user (``PATCH /users/{user_id}``)."""
        r = self.http.patch(
            f"/users/{user_id}", json=fields, headers=self._admin_headers()
        )
        r.raise_for_status()
        return r.json()

    # --- Projects
    def create_project(self, name: str, description: Optional[str] = None) -> dict:
        """Create a new project (``POST /projects``)."""
        r = self.http.post(
            "/projects",
            json={"name": name, "description": description},
            headers=self._admin_headers(),
        )
        r.raise_for_status()
        return r.json()

    def list_projects(self) -> list[dict]:
        """List all projects (``GET /projects``)."""
        r = self.http.get("/projects", headers=self._admin_headers())
        r.raise_for_status()
        return r.json()

    def add_project_member(self, project_id: str, user_id: str, role_id: str) -> dict:
        """Add a user to a project with a role (``POST /projects/{id}/members``)."""
        r = self.http.post(
            f"/projects/{project_id}/members",
            json={"user_id": user_id, "role_id": role_id},
            headers=self._admin_headers(),
        )
        r.raise_for_status()
        return r.json()

    # --- Roles
    def create_role(
        self, name: str, permissions: list[str], description: Optional[str] = None
    ) -> dict:
        """Create a new role with permissions (``POST /roles``)."""
        r = self.http.post(
            "/roles",
            json={
                "name": name,
                "permissions": permissions,
                "description": description,
            },
            headers=self._admin_headers(),
        )
        r.raise_for_status()
        return r.json()

    def list_roles(self) -> list[dict]:
        """List all roles (``GET /roles``)."""
        r = self.http.get("/roles", headers=self._admin_headers())
        r.raise_for_status()
        return r.json()

    def grant_role(self, **kwargs: Any) -> dict:
        """Grant a role to a principal (``POST /roles/grant``)."""
        r = self.http.post("/roles/grant", json=kwargs, headers=self._admin_headers())
        r.raise_for_status()
        return r.json()

    # --- Service accounts / nodes
    def register_service_account(
        self, manager_id: str, role_ids: Optional[list[str]] = None
    ) -> dict:
        """Register a service account (``POST /service-accounts``).

        The plaintext ``client_secret`` is returned exactly once.
        """
        r = self.http.post(
            "/service-accounts",
            json={"manager_id": manager_id, "role_ids": role_ids or []},
            headers=self._admin_headers(),
        )
        r.raise_for_status()
        return r.json()

    def register_node(
        self,
        node_id: str,
        workcell_id: Optional[str] = None,
        role_ids: Optional[list[str]] = None,
    ) -> dict:
        """Register a node identity (``POST /node-identities``).

        The plaintext ``client_secret`` is returned exactly once.
        """
        r = self.http.post(
            "/node-identities",
            json={
                "node_id": node_id,
                "workcell_id": workcell_id,
                "role_ids": role_ids or [],
            },
            headers=self._admin_headers(),
        )
        r.raise_for_status()
        return r.json()

    def rotate_credentials(self, client_id: str) -> dict:
        """Rotate a service-account or node-identity secret (``POST /credentials/{id}/rotate``)."""
        r = self.http.post(
            f"/credentials/{client_id}/rotate", headers=self._admin_headers()
        )
        r.raise_for_status()
        return r.json()

    # --- Keys
    def rotate_keys(self) -> dict:
        """Generate a new signing keypair (``POST /keys/rotate``)."""
        r = self.http.post("/keys/rotate", headers=self._admin_headers())
        r.raise_for_status()
        return r.json()

    def list_keys(self) -> list[dict]:
        """List all signing keys (``GET /keys``)."""
        r = self.http.get("/keys", headers=self._admin_headers())
        r.raise_for_status()
        return r.json()

    def retire_key(self, kid: str) -> dict:
        """Retire a signing key (``DELETE /keys/{kid}``)."""
        r = self.http.delete(f"/keys/{kid}", headers=self._admin_headers())
        r.raise_for_status()
        return r.json()


__all__ = ["AuthClient", "AuthClientError"]
