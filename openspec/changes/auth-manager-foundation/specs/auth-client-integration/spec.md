## ADDED Requirements

### Requirement: AuthClient class

A new `AuthClient` SHALL be added to `madsci_client` (`src/madsci_client/madsci/client/auth_client.py`) providing programmatic access to the Auth Manager. It MUST support: password login, refresh-token grant, client-credentials grant, token introspection, JWKS fetch with TTL caching, and explicit `close()` for connection-pool cleanup.

#### Scenario: Acquire a token via password grant
- **WHEN** application code calls `AuthClient(auth_server_url=...).login(username, password)`
- **THEN** the client SHALL POST to the token endpoint, store the resulting access and refresh tokens in memory, and return a typed `TokenResponse` Pydantic model

#### Scenario: Auto-refresh before expiry
- **WHEN** an `AuthClient` holds an access token whose `exp` is within a configurable refresh-buffer (default 60 seconds) of the current time
- **THEN** the next call requiring a token SHALL transparently invoke the refresh grant and update the cached tokens before returning

#### Scenario: JWKS cached with TTL
- **WHEN** an `AuthClient` is asked to verify a JWT
- **THEN** it SHALL fetch JWKS once, cache the keys for a TTL of at most 5 minutes, and reuse the cache for all subsequent verifications until the TTL elapses

### Requirement: Ambient AuthClient and credential propagation

An ambient `AuthClient` SHALL be installable into a contextvars-based scope (`auth_client_context()`) analogous to `event_client_context()`. When set, the existing `create_httpx_client()` factory in `madsci.common.http_client` SHALL automatically inject `Authorization: Bearer <token>` on every outbound request.

#### Scenario: Ambient client injects auth headers
- **GIVEN** `auth_client_context(client)` has been entered with a logged-in `AuthClient`
- **WHEN** any service client built on `create_httpx_client()` (e.g., `EventClient.async_log_event(...)`) issues a request
- **THEN** the request SHALL carry an `Authorization: Bearer <token>` header sourced from the ambient `AuthClient`

#### Scenario: No ambient client means no header
- **GIVEN** no `auth_client_context()` is active
- **WHEN** a service client issues a request
- **THEN** no `Authorization` header SHALL be added (preserving existing unauthenticated behavior)

#### Scenario: 401 triggers a refresh-and-retry once
- **WHEN** a request returns HTTP 401 and an ambient `AuthClient` is present
- **THEN** the client SHALL force a JWKS-cache refresh, attempt a refresh-grant, and retry the original request exactly once before surfacing the error

### Requirement: AuthMiddleware on AbstractManagerBase

`AbstractManagerBase` SHALL gain an `AuthMiddleware` that is installed on the FastAPI app whenever `auth_enabled=True` in the manager's settings. The middleware MUST: extract the `Authorization` header, verify the JWT signature against cached JWKS from `auth_server_url`, validate `iss`/`aud`/`exp`, populate `request.state.principal` with the validated claims, and enter an `ownership_context()` for the request lifetime sourced from those claims.

#### Scenario: Middleware installed only when auth_enabled
- **WHEN** `AbstractManagerBase` initializes with `auth_enabled=False`
- **THEN** `AuthMiddleware` SHALL NOT be added to the FastAPI app and request behavior SHALL be identical to today's

#### Scenario: Valid token populates principal and ownership
- **GIVEN** `auth_enabled=True`
- **WHEN** a request arrives with a valid `Authorization: Bearer <jwt>` header
- **THEN** the middleware SHALL set `request.state.principal` to a typed `Principal` model derived from the JWT claims and the request handler SHALL observe an `ownership_context()` whose fields are sourced from the token's ownership claims

#### Scenario: Missing or invalid token with auth_required=True
- **GIVEN** `auth_enabled=True` and `auth_required=True`
- **WHEN** a request arrives with no `Authorization` header or an invalid/expired/forged token
- **THEN** the middleware SHALL short-circuit the request with HTTP 401 and the audit log entry SHALL be emitted to the Auth Manager (or queued for later delivery if the Auth Manager is unreachable)

#### Scenario: Missing token with auth_required=False (migration mode)
- **GIVEN** `auth_enabled=True` and `auth_required=False`
- **WHEN** a request arrives with no `Authorization` header
- **THEN** the middleware SHALL allow the request to proceed with `request.state.principal = None`, no `ownership_context` is entered, and a structured warning event SHALL be logged so operators can identify unauth'd traffic during migration

### Requirement: OwnershipInfo binding from token claims

When `AuthMiddleware` is active and a valid token is present, code that calls `get_current_ownership_info()` SHALL receive an `OwnershipInfo` whose `user_id`, `project_id` (drawn from `project_ids` claim — see project-scoped scenario), `node_id`, `workcell_id`, and `lab_id` fields are sourced exclusively from the validated JWT claims. The body-supplied value of any ownership field that has a corresponding claim SHALL be ignored entirely (no fallback when the claim is absent). The body-supplied value of any field that has NO corresponding claim slot (e.g., `experiment_id`, `workflow_id`, `step_id`, `campaign_id`) is accepted as today, since these are operational identifiers, not principal-bound identifiers. Mismatches between body and claim SHALL emit a warning event.

#### Scenario: Token claims override body-supplied ownership
- **GIVEN** a request whose body declares `user_id=mallory` but whose validated token claims `user_id=alice`
- **WHEN** the request handler reads `get_current_ownership_info()`
- **THEN** the returned `OwnershipInfo.user_id` SHALL be `alice` and a warning event SHALL be logged noting the mismatch

#### Scenario: Absent claim does not fall back to body
- **GIVEN** a service-account token whose claims do NOT include `user_id` and a request body declaring `user_id=mallory`
- **WHEN** the request handler reads `get_current_ownership_info()`
- **THEN** `OwnershipInfo.user_id` SHALL be `None` (not `mallory`) and a warning event SHALL be logged noting the body-supplied principal-bound field was discarded

#### Scenario: Operational identifiers from body are preserved
- **GIVEN** a request whose body declares `experiment_id=exp_123` and `workflow_id=wf_456`
- **WHEN** the request handler reads `get_current_ownership_info()`
- **THEN** `OwnershipInfo.experiment_id` SHALL be `exp_123` and `OwnershipInfo.workflow_id` SHALL be `wf_456`, since these are operational identifiers without corresponding token claims

#### Scenario: Claim-to-OwnershipInfo field mapping
- **WHEN** `OwnershipInfo.from_jwt_claims(claims)` is called with a verified `JWTClaims` instance
- **THEN** the returned `OwnershipInfo` SHALL be populated as follows: `user_id ← claims.user_id` (when `principal_type=user`), `node_id ← claims.node_id` (when `principal_type=node`), `workcell_id ← claims.workcell_id` (when present), `lab_id ← claims.aud`, `manager_id ← claims.manager_id` (when `principal_type=service_account` — sourced from the dedicated `manager_id` claim, NOT from `sub`, since `sub` is the principal record's `client_id` and not the operational manager identity); `project_id` is left unset on the returned object (project context is established per-operation via `@requires(project_from=...)`, not as ambient ownership); all other `OwnershipInfo` fields SHALL be left unset

#### Scenario: Project membership enforced for project-scoped operations
- **WHEN** a request handler attempts to act within `project_id=proj_X` (e.g., create an experiment under it) and the validated principal's claims do NOT include `proj_X` in `project_ids`
- **THEN** the handler SHALL receive an authorization error (HTTP 403) and the operation SHALL NOT be performed

#### Scenario: Caller-asserted OwnershipInfo accepted when auth is disabled
- **GIVEN** `auth_enabled=False` on the manager
- **WHEN** a request body includes an `OwnershipInfo` (or equivalent caller-asserted fields)
- **THEN** the values SHALL be accepted as today and a deprecation warning SHALL be emitted on a sampled basis (default once per process per minute per call-site) pointing at the auth migration guide

### Requirement: `@requires` decorator for endpoint authorization

The system SHALL provide a `@requires(permission=...)` decorator usable on `Routable` endpoint methods. The decorator MUST consult `request.state.principal.permissions` and return HTTP 403 when the required permission is absent. It MUST also support an optional `project_from=<field_name>` argument that resolves the relevant project id from the request and additionally verifies project membership.

#### Scenario: Decorator allows authorized request
- **GIVEN** a principal whose token claims include the `experiment.write` permission
- **WHEN** a request hits an endpoint decorated with `@requires(permission="experiment.write")`
- **THEN** the handler SHALL execute normally

#### Scenario: Decorator rejects unauthorized request
- **GIVEN** a principal whose token claims do NOT include the `experiment.write` permission
- **WHEN** a request hits an endpoint decorated with `@requires(permission="experiment.write")`
- **THEN** the middleware SHALL return HTTP 403 and the handler SHALL NOT execute

#### Scenario: Project-scoped check
- **GIVEN** an endpoint decorated with `@requires(permission="experiment.write", project_from="experiment_id")`
- **WHEN** a request arrives for an experiment whose owning project is NOT in the principal's `project_ids` claim
- **THEN** the middleware SHALL return HTTP 403 even if the principal globally holds `experiment.write`
