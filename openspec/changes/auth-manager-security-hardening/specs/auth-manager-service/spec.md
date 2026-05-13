## ADDED Requirements

### Requirement: Auth Manager enforces authentication on its own admin endpoints

The Auth Manager SHALL install `AuthMiddleware` on its own FastAPI application whenever `auth_enabled=True`. Every administrative endpoint (every route under `/users`, `/projects`, `/roles`, `/service-accounts`, `/node-identities`, `/credentials`, and `/keys`, plus `GET /users` / `GET /projects` / `GET /roles` / `GET /keys` listing endpoints) SHALL additionally carry a `@requires(permission=...)` decorator that names the required permission and rejects unauthenticated or under-privileged callers.

The unauthenticated allowlist SHALL be limited to: `POST /token`, `GET /.well-known/jwks.json`, `GET /health`, `GET /health/keys`, `GET /settings`, and `GET /deny-list`. No other route SHALL be reachable without a valid bearer token.

#### Scenario: Unauthenticated request to admin endpoint is rejected
- **GIVEN** the Auth Manager is running with `auth_enabled=True`
- **WHEN** a client calls `POST /users`, `POST /roles/grant`, `POST /service-accounts`, `POST /node-identities`, `POST /credentials/{id}/rotate`, `POST /keys/rotate`, `DELETE /keys/{kid}`, or any `GET` listing endpoint without an `Authorization` header
- **THEN** the Auth Manager SHALL return HTTP 401 and SHALL NOT execute the handler

#### Scenario: Authenticated but under-privileged request is rejected
- **GIVEN** a caller with a valid token whose `permissions` claim does not include the required `auth.*` permission for the route
- **WHEN** the caller invokes that route
- **THEN** the Auth Manager SHALL return HTTP 403 and SHALL NOT execute the handler

#### Scenario: Allowlisted routes remain reachable without a token
- **WHEN** a client calls `POST /token`, `GET /.well-known/jwks.json`, `GET /health`, `GET /health/keys`, `GET /settings`, or `GET /deny-list` without an `Authorization` header
- **THEN** the Auth Manager SHALL serve the response normally

### Requirement: Auth Manager refuses to operate without a bound lab_id

The Auth Manager SHALL refuse to start when `lab_id` is unset or empty. The literal `"lab-unbound"` audience value SHALL NOT appear anywhere in issued tokens or in code. If `lab_id` becomes unset after startup (for example, via configuration reload), token issuance SHALL fail with HTTP 503 until `lab_id` is restored.

#### Scenario: Startup fails without lab_id
- **GIVEN** an `AuthManagerSettings` whose `lab_id` is unset
- **WHEN** the operator runs `madsci start manager auth`
- **THEN** the process SHALL exit non-zero with a clear error message naming `lab_id` as required

#### Scenario: No "lab-unbound" tokens are issued
- **WHEN** any token is issued by any code path
- **THEN** the `aud` claim SHALL be the deployment's bound `lab_id` and SHALL NEVER be the string `"lab-unbound"`

### Requirement: Audit log writes are failure-closed for state-changing operations

For every state-changing auth operation (token issuance, refresh, revocation, user/project/role/principal creation or modification, key rotation or retirement), the audit log row SHALL be written in the same database transaction as the underlying state change. If the audit write fails for any reason, the transaction SHALL be rolled back and the operation SHALL fail. For transient database errors only, the issuer SHALL fall back to writing to the local `auth_audit_fallback` append-only file, deferring the database write to the next successful reconnection.

#### Scenario: Failed audit write rolls back the operation
- **GIVEN** a database state that causes the audit insert to raise (e.g., constraint violation, schema mismatch)
- **WHEN** any state-changing auth operation runs
- **THEN** the operation SHALL fail with HTTP 500, the underlying state SHALL NOT be persisted, and no token SHALL be returned

#### Scenario: Transient DB error falls back to local audit file
- **WHEN** a state-changing auth operation encounters a transient DB error and the operation must succeed
- **THEN** the audit row SHALL be written to the local `auth_audit_fallback` file, the operation SHALL succeed, and the row SHALL be drained to the database on the next successful connection

### Requirement: X-Forwarded-For trust is opt-in

The Auth Manager SHALL NOT trust the `X-Forwarded-For` header by default. A new setting `auth_trust_forwarded_for: bool = False` SHALL gate trust. When `False`, `_client_ip` SHALL return the socket peer address. When `True`, `_client_ip` MAY use the leftmost `X-Forwarded-For` value after normalization.

#### Scenario: Default deployment ignores X-Forwarded-For
- **GIVEN** an Auth Manager with `auth_trust_forwarded_for=False`
- **WHEN** a request arrives carrying `X-Forwarded-For: 1.2.3.4`
- **THEN** audit log entries for that request SHALL record the socket peer address, NOT `1.2.3.4`

#### Scenario: Behind-proxy deployment honors X-Forwarded-For
- **GIVEN** an Auth Manager with `auth_trust_forwarded_for=True`
- **WHEN** a request arrives via a trusted proxy carrying `X-Forwarded-For: 1.2.3.4`
- **THEN** audit log entries SHALL record `1.2.3.4` as the client IP

### Requirement: Auth Manager FastAPI server is organized by resource router

The Auth Manager SHALL organize its endpoints into per-resource FastAPI routers under `madsci/auth_manager/routers/`: `token_router`, `users_router`, `projects_router`, `roles_router`, `principals_router`, `keys_router`, `deny_list_router`. Each router SHALL declare its required permissions in a single auditable location.

#### Scenario: Routers are discoverable and per-resource
- **WHEN** a reviewer reads `madsci/auth_manager/routers/users_router.py`
- **THEN** every `/users/*` route and its `@requires(permission=...)` decorator SHALL be visible in that one file
