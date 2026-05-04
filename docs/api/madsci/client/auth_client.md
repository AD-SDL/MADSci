Module madsci.client.auth_client
================================
Client library for the MADSci Auth Manager.

Provides programmatic access to the Auth Manager: token acquisition (password,
refresh, client_credentials), introspection, JWKS-cached JWT verification,
deny-list polling, and the admin surface (users, projects, roles,
service-accounts, node identities, signing keys).

The ``AuthClient`` is also installable into the ambient context via
``auth_client_context()`` so other service clients pick up bearer tokens
automatically (see ``madsci.common.auth_context``).

Classes
-------

`AuthClient(auth_server_url: AnyUrl | str, *, access_token: Optional[str] = None, refresh_token: Optional[str] = None, client_id: Optional[str] = None, client_secret: Optional[str] = None, jwks_ttl_seconds: int = 300, deny_list_poll_interval: int = 30, refresh_buffer_seconds: int = 60, timeout: float = 10.0)`
:   Synchronous client for the Auth Manager.
    
    The client is intentionally synchronous to mirror the rest of MADSci's
    service clients. Concurrency-sensitive call sites can wrap it with their
    own thread pool / asyncio.to_thread.
    
    Initialize the client with optional pre-existing tokens / credentials.

    ### Instance variables

    `access_token: Optional[str]`
    :   The currently-cached access token, or None if not logged in.

    `async_http: httpx.AsyncClient`
    :   Lazily-initialized async httpx client (mirrors ``http``).

    `http: httpx.Client`
    :   Lazily-initialized synchronous httpx client.

    ### Methods

    `add_project_member(self, project_id: str, user_id: str, role_id: str) ‑> dict`
    :   Add a user to a project with a role (``POST /projects/{id}/members``).

    `client_credentials_login(self, client_id: str, client_secret: str) ‑> madsci.common.types.auth_types.TokenResponse`
    :   Exchange client_id/client_secret for an access token (no refresh token).

    `close(self) ‑> None`
    :   Release the synchronous HTTP connection pool. Idempotent.

    `create_project(self, name: str, description: Optional[str] = None) ‑> dict`
    :   Create a new project (``POST /projects``).

    `create_role(self, name: str, permissions: list[str], description: Optional[str] = None) ‑> dict`
    :   Create a new role with permissions (``POST /roles``).

    `create_user(self, username: str, password: str, email: Optional[str] = None) ‑> dict`
    :   Create a new user (``POST /users``).

    `force_deny_list_refresh(self) ‑> None`
    :   Force an immediate deny-list fetch (used after on-401 retries).

    `get_access_token(self) ‑> str`
    :   Return a non-expired access token, refreshing transparently.

    `grant_role(self, **kwargs: Any) ‑> dict`
    :   Grant a role to a principal (``POST /roles/grant``).

    `introspect(self, token: str) ‑> dict`
    :   Call the RFC 7662 introspection endpoint for ``token``.

    `jwks(self, *, force_refresh: bool = False) ‑> dict`
    :   Return the JWKS document, fetching from the Auth Manager if the cache is stale.

    `list_keys(self) ‑> list[dict]`
    :   List all signing keys (``GET /keys``).

    `list_projects(self) ‑> list[dict]`
    :   List all projects (``GET /projects``).

    `list_roles(self) ‑> list[dict]`
    :   List all roles (``GET /roles``).

    `list_users(self) ‑> list[dict]`
    :   List all users (``GET /users``).

    `login(self, username: str, password: str) ‑> madsci.common.types.auth_types.TokenResponse`
    :   Exchange username/password for access + refresh tokens (password grant).

    `refresh(self) ‑> madsci.common.types.auth_types.TokenResponse`
    :   Exchange the cached refresh token for a fresh access + refresh pair.

    `register_node(self, node_id: str, workcell_id: Optional[str] = None, role_ids: Optional[list[str]] = None) ‑> dict`
    :   Register a node identity (``POST /node-identities``).
        
        The plaintext ``client_secret`` is returned exactly once.

    `register_service_account(self, manager_id: str, role_ids: Optional[list[str]] = None) ‑> dict`
    :   Register a service account (``POST /service-accounts``).
        
        The plaintext ``client_secret`` is returned exactly once.

    `retire_key(self, kid: str) ‑> dict`
    :   Retire a signing key (``DELETE /keys/{kid}``).

    `revoke(self, *, token: Optional[str] = None, refresh_token: Optional[str] = None) ‑> None`
    :   Revoke an access token and/or refresh token at the Auth Manager.

    `rotate_credentials(self, client_id: str) ‑> dict`
    :   Rotate a service-account or node-identity secret (``POST /credentials/{id}/rotate``).

    `rotate_keys(self) ‑> dict`
    :   Generate a new signing keypair (``POST /keys/rotate``).

    `update_user(self, user_id: str, **fields: Any) ‑> dict`
    :   Patch a user (``PATCH /users/{user_id}``).

    `verify_jwt(self, token: str) ‑> madsci.common.types.auth_types.JWTClaims`
    :   Verify a JWT against the cached JWKS and the cached deny-list.
        
        On signature failure, the JWKS cache is force-refreshed and verification
        is retried once.

`AuthClientError(*args, **kwargs)`
:   Raised on auth-client failures.

    ### Ancestors (in MRO)

    * builtins.Exception
    * builtins.BaseException