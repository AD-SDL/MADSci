## 1. Package scaffolding and dependencies

- [ ] 1.1 Create `src/madsci_auth_manager/` package with `pyproject.toml`, `madsci/auth_manager/__init__.py`, and `tests/` directory matching the existing manager-package layout
- [ ] 1.2 Add `Authlib`, `argon2-cffi`, and `cryptography` to `madsci_auth_manager` dependencies; add `Authlib` and `argon2-cffi` to `madsci_client` and `madsci_common` as needed
- [ ] 1.3 Reserve port 8007 in `CLAUDE.md`, `docs/Configuration.md`, `examples/example_lab/compose.yaml`, and any other port-allocation references; verify any `madsci start` port-collision logic is updated to recognize 8007
- [ ] 1.4 Update root `.justfile` and CI workflows so the new package is included in `pdm install`, `pytest`, `ruff check`, and coverage runs

## 2. Common types and ownership extensions

- [ ] 2.1 Extend `madsci.common.types.auth_types` with `Role`, `Permission`, `ProjectMembership`, `ServiceAccount`, `NodeIdentity`, `Principal`, `TokenResponse`, and `JWTClaims` Pydantic models
- [ ] 2.2 Add a `principal: Principal | None` field accessor pattern to the request-state contract used by middleware
- [ ] 2.3 Update `OwnershipInfo` documentation and add helper `OwnershipInfo.from_jwt_claims(claims)` constructor (no behavior change to existing fields)
- [ ] 2.4 Write unit tests in `src/madsci_common/tests/` for the new types, including ULID validation and serialization

## 3. Auth Manager settings and database schema

- [ ] 3.1 Implement `AuthManagerSettings(MadsciBaseSettings)` with `AUTH_` prefix, fields for `database_url`, `signing_key_ttl`, `access_token_ttl`, `refresh_token_ttl`, `argon2_*` tuning, plus the standard `server_url`/`manager_id`
- [ ] 3.2 Define SQLModel tables: `users`, `projects`, `project_memberships`, `roles`, `role_permissions`, `service_accounts`, `node_identities`, `refresh_tokens`, `signing_keys`, `audit_log`
- [ ] 3.3 Set up Alembic migration directory and initial migration creating all tables with proper indexes and foreign keys
- [ ] 3.4 Wire integration with `SQLAlchemyHandler` so the in-memory `SQLiteHandler` works for tests (handle SQLite-specific DDL via `_create_table_sqlite_compat()` where needed)

## 4. Token service core

- [ ] 4.1 Implement `SigningKeyService` with RSA keypair generation via `cryptography`, persistence with `kid`/`active`/`active_for_signing` flags, and rotation/retire helpers
- [ ] 4.2 Implement `TokenService` with `issue_access_token(principal, ttl)`, `issue_refresh_token(principal)`, `verify_token(jwt)`, `introspect(jwt)`, and `revoke(jti_or_refresh)` using Authlib's JWT module
- [ ] 4.3 Implement `PasswordService` wrapping argon2-cffi for `hash_password()`/`verify_password()` with tunable parameters from settings
- [ ] 4.4 Implement `AuditLogger` with append-only writes for the security-relevant events listed in the identity-model spec
- [ ] 4.5 Implement `DenyListService` maintaining the in-memory revoked-`jti`+`exp` set, exposing it via the `/deny-list` endpoint with `ETag`/`If-None-Match` support and automatic eviction on `exp`

## 5. AuthManager FastAPI server

- [ ] 5.1 Implement `AuthManager(AbstractManagerBase[AuthManagerSettings])` server class with the standard `initialize()`, `setup_logging()`, and lifespan hooks
- [ ] 5.2 Implement token endpoints: `POST /token` (password, refresh_token, client_credentials grants), `POST /introspect`, `POST /revoke`
- [ ] 5.3 Implement JWKS endpoint: `GET /.well-known/jwks.json` (no auth required)
- [ ] 5.4 Implement user endpoints: `POST /users`, `GET /users`, `GET /users/{id}`, `PATCH /users/{id}` (deactivate, password change)
- [ ] 5.5 Implement project endpoints: `POST /projects`, `GET /projects`, `POST /projects/{id}/members`, `DELETE /projects/{id}/members/{user_id}`
- [ ] 5.6 Implement role endpoints: `POST /roles`, `GET /roles`, role-grant/revoke for users, service accounts, and node identities
- [ ] 5.7 Implement service-account and node-identity endpoints: `POST /service-accounts`, `POST /node-identities`, `POST /credentials/{client_id}/rotate`
- [ ] 5.8 Implement key-management endpoints: `POST /keys/rotate`, `GET /keys`, `DELETE /keys/{kid}`
- [ ] 5.9 Implement `/health/keys` endpoint returning active key count and oldest-key age
- [ ] 5.10 Implement `GET /deny-list` endpoint with `ETag` / `If-None-Match` conditional fetch
- [ ] 5.11 Apply `RateLimitMiddleware` to `/token` and add the `unsupported_grant_type` (HTTP 400, RFC 6749 §5.2) error response

## 6. Bootstrap CLI

- [ ] 6.1 Add `auth` command group to `madsci.client.cli` with lazy loading via `_LAZY_COMMANDS`
- [ ] 6.2 Implement `madsci auth bootstrap` (creates admin user, generates first signing key, seeds built-in roles, idempotent on re-run)
- [ ] 6.3 Implement `madsci auth user create|deactivate|grant|revoke|password`
- [ ] 6.4 Implement `madsci auth project create|list|members`
- [ ] 6.5 Implement `madsci auth manager register|list` and `madsci auth node register|list`
- [ ] 6.6 Implement `madsci auth credentials rotate <client_id>` returning new secret exactly once
- [ ] 6.7 Implement `madsci auth keys rotate|list|retire`
- [ ] 6.8 Add CLI smoke tests that exercise every subcommand against an in-memory Auth Manager

## 7. AuthClient (client library)

- [ ] 7.1 Implement `AuthClient` class in `src/madsci_client/madsci/client/auth_client.py` with `login()`, `refresh()`, `client_credentials_login()`, `introspect()`, `verify_jwt()`, and `close()` methods
- [ ] 7.2 Implement TTL-based JWKS cache with forced-refresh on verify failure
- [ ] 7.3 Implement transparent auto-refresh before expiry using a configurable refresh-buffer
- [ ] 7.4 Add an async-friendly variant where applicable, mirroring the pattern used by other clients
- [ ] 7.5 Implement deny-list polling (configurable interval, default 30s) using conditional fetch; enforce locally-cached deny-list during `verify_jwt()`
- [ ] 7.6 Write unit tests covering happy path, expired-token refresh, refresh-token reuse detection, JWKS cache invalidation, deny-list polling and enforcement, and connection close

## 8. Ambient credential propagation

- [ ] 8.1 Add `auth_client_context()` context manager and `get_current_auth_client()` accessor to `madsci.common.context` (or a new `madsci.common.auth_context` module if preferred)
- [ ] 8.2 Modify `create_httpx_client()` in `madsci.common.http_client` to add an outbound-request hook that injects `Authorization: Bearer <token>` from the ambient `AuthClient` when present
- [ ] 8.3 Implement the on-401 force-refresh-and-retry-once policy in the same hook
- [ ] 8.4 Verify behavior is unchanged when no ambient client is set (no header added, no retries)

## 9. AuthMiddleware on AbstractManagerBase

- [ ] 9.1 Add `auth_enabled: bool = False`, `auth_required: bool = False`, and `auth_server_url: AnyUrl | None = None` to `MadsciBaseSettings`
- [ ] 9.2 Implement `AuthMiddleware` (Starlette middleware) verifying JWTs via cached JWKS from `auth_server_url`, populating `request.state.principal`, and entering an `ownership_context()` for the request
- [ ] 9.3 Wire the middleware into `AbstractManagerBase` so it is registered when `auth_enabled=True`
- [ ] 9.4 Implement the `auth_required=False` migration mode (allow unauth'd requests through, log a structured warning)
- [ ] 9.5 Add the body-vs-claims `OwnershipInfo` precedence rule with a mismatch warning
- [ ] 9.6 Implement sampled deprecation warning for caller-asserted `OwnershipInfo` when `auth_enabled=False` (default once per process per minute per call-site, pointing at the migration guide)
- [ ] 9.7 Implement local audit-log fallback: persist auth events to a configurable on-disk append-only log when the Auth Manager is unreachable, drain to the Auth Manager on recovery, bounded with rotation and a warning event when the bound is exceeded

## 10. `@requires` decorator and authorization helpers

- [ ] 10.1 Implement `@requires(permission=..., project_from=None)` decorator usable on `Routable` endpoint methods
- [ ] 10.2 Implement helper `current_principal(request)` and `current_ownership(request)` accessors
- [ ] 10.3 Document the canonical permission namespace (`<resource>.<action>`) and seed permissions for the built-in roles
- [ ] 10.4 Add example application in one read-only endpoint of an existing manager (e.g., `EventManager.get_events`) to validate the decorator end-to-end without making the whole manager require auth

## 11. End-to-end and integration tests

- [ ] 11.1 Build an in-memory Auth Manager fixture (PyTest) usable across packages
- [ ] 11.2 Write integration test: bootstrap → user login → password grant → access existing manager endpoint with `auth_enabled=True, auth_required=True`
- [ ] 11.3 Write integration test: service-account client_credentials → manager-to-manager call
- [ ] 11.4 Write integration test: refresh-token rotation, including the reuse-detection path that revokes all tokens
- [ ] 11.5 Write integration test: JWKS rotation while a previously-issued token is still in flight (verifies in-flight token still validates)
- [ ] 11.6 Write integration test: project-scoped `@requires` denies a principal whose token claims don't include the target project
- [ ] 11.7 Write a docker-compose end-to-end test in `examples/example_lab/` that boots Auth Manager + one other manager + one node and exercises the full token lifecycle
- [ ] 11.8 Write integration test exercising the deny-list flow: revoke a token at the Auth Manager and verify the consuming manager rejects it within `deny_list_poll_interval + max_clock_skew`
- [ ] 11.9 Write integration test exercising the local audit-log fallback: take down the Auth Manager mid-request, confirm the event is persisted locally, restart the Auth Manager, confirm the event drains

## 12. Documentation

- [ ] 12.1 Write `docs/guides/auth.md` covering the architecture, token model, RBAC concepts, and integration points
- [ ] 12.2 Write `docs/guides/auth_operator.md` covering bootstrap, secret distribution (including required `0600` file mode on `.madsci/secrets/*` and `.gitignore` treatment in templates), key rotation, HTTPS termination, reverse-proxy `X-Forwarded-For` handling for accurate audit-log source IPs, audit-log retention/PII guidance, and the migration plan (auth_enabled → auth_required)
- [ ] 12.3 Update `docs/Configuration.md` with the new `AUTH_*` settings and the per-manager `auth_enabled`/`auth_required`/`auth_server_url` fields
- [ ] 12.4 Update `README.md` and `CHANGELOG.md` with a summary of the Auth Manager addition and migration guidance
- [ ] 12.5 Update `CLAUDE.md` agent guidance: new manager exists, port 8007, AuthClient pattern, ambient-context propagation rule

## 13. Example lab and templates

- [ ] 13.1 Add `madsci_auth_manager` service to `examples/example_lab/compose.yaml`
- [ ] 13.2 Add an `auth` template under `src/madsci_common/madsci/common/bundled_templates/manager/` using the existing template pattern (manifest + Jinja2)
- [ ] 13.3 Demonstrate the bootstrap flow in the example lab's `README.md`
- [ ] 13.4 Provide a sample `auth_enabled=True, auth_required=False` configuration showing a deployment in migration mode

## 14. Cross-project coordination

- [ ] 14.1 Review with the SiLA2 migration owner (#293/#294) to confirm the `NodeIdentity` model is compatible with the SiLA2 trust model and that the future `mtls_cert_fingerprint` field is correctly placed
- [ ] 14.2 Review with the layered-location-ownership owner (#210) to confirm the `OwnershipInfo`-from-claims model unblocks their requirements
- [ ] 14.3 Capture any required follow-on OpenSpec change names in `docs/guides/auth.md` (e.g., `auth-globus-orcid-federation`, `auth-node-mtls`, `auth-per-manager-rbac-rollout`)

## 15. Security review and release prep

- [ ] 15.1 Run the `security-review` skill against the change branch
- [ ] 15.2 Run the `madsci-release-audit` skill before merge
- [ ] 15.3 Confirm test coverage thresholds for `madsci_auth_manager`, the `AuthClient`, and the `AuthMiddleware` paths (default to project-wide threshold; raise the bar in a follow-on if the security-review surfaces specific risk areas)
- [ ] 15.4 Open a follow-up tracking issue listing the deferred items: Globus/ORCID upstream-IdP federation (which addresses cross-lab user identity), mTLS for nodes, per-manager `@requires` rollout, per-principal `aud` narrowing, node enrollment-token flow, optional `madsci registry add` + `madsci auth node register` atomic-add CLI convenience, and the deprecation timeline for `auth_required=False` and caller-asserted `OwnershipInfo`
