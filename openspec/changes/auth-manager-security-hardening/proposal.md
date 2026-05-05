## Why

A senior security review of `auth-manager-foundation` (PR #310) identified five merge-blocking issues and six significant follow-ups. The Auth Manager's own admin endpoints are unauthenticated, JWT verification doesn't pin algorithms, refresh-token reuse detection has a TOCTOU race, the introspect/revoke endpoints leak token claims to anyone on the network, and the audience claim defaults to a value that two unbound labs would mutually trust. These flaws would let any actor with network reach to port 8007 mint admin users, rotate signing keys, and forge tokens — defeating the entire foundation. The hardening must land before any operator turns `auth_enabled=True`.

## What Changes

- **BREAKING**: All Auth Manager admin endpoints (`POST /users`, `/projects`, `/roles`, `/roles/grant`, `/service-accounts`, `/node-identities`, `POST /credentials/{id}/rotate`, `POST /keys/rotate`, `DELETE /keys/{kid}`, `GET /users`, `GET /projects`, `GET /roles`, `GET /keys`) require an authenticated caller with the appropriate `auth.*` permission. The Auth Manager mounts `AuthMiddleware` on itself with an explicit unauthenticated allowlist (`/token`, `/.well-known/jwks.json`, `/health*`, `/settings`, `/deny-list` GET).
- **BREAKING**: `/introspect` and `/revoke` require client authentication. `/introspect` returns `{active: false}` to unauthenticated callers per RFC 7662; `/revoke` requires the caller to be the token's `sub` or hold an `auth.token.revoke` permission.
- **BREAKING**: The Auth Manager refuses to start (and refuses to issue tokens) when `lab_id` is unset. The literal `"lab-unbound"` audience is removed.
- JWT verification on both server (`token_service.verify_token`) and client (`AuthClient`) pins `algorithms=["RS256"]`. Verification accepts a configurable clock-skew leeway (default 30 s).
- Refresh-token consumption uses an atomic `UPDATE ... WHERE revoked_at IS NULL RETURNING ...` (or row lock for SQLite) so concurrent refreshes cannot both succeed. The `rotated_to` column is populated for forensics.
- Bootstrap CLI removes `--password` as a positional/flag argument; password comes from interactive prompt or `MADSCI_AUTH_BOOTSTRAP_PASSWORD` env var only. argv is no longer a leak vector.
- Audit log writes for token issuance, revocation, and admin mutations are committed in the same transaction as the underlying state change. If audit write fails, the operation fails (failure-closed). The consumer-side `auth_audit_fallback` mechanism is extended to the issuer for transient DB errors.
- `_client_ip` no longer trusts `X-Forwarded-For` unconditionally; a `auth_trust_forwarded_for` setting (default `False`) gates it.
- `consume_refresh_token` populates `RefreshTokenTable.rotated_to` linking parent → child for reuse-detection forensics.
- `auth_server.py` is split into per-resource routers (`token_router`, `users_router`, `projects_router`, `roles_router`, `principals_router`, `keys_router`, `deny_list_router`) under `auth_manager/routers/`.
- New tests cover: alg-confusion rejection (HS256 forgery using public key as HMAC secret must fail), refresh-token concurrent-consume race, every admin endpoint rejecting unauthenticated and under-privileged callers, `aud` mismatch rejection, expired-token replay, deny-list eviction on jti revoke.
- **Library swap (Authlib → joserfc).** Authlib 1.7+ deprecates `authlib.jose` in favor of `joserfc` (same author's successor). `TokenService` and `AuthClient` are migrated to `joserfc.jwt.encode`/`decode`, `joserfc.jwk.RSAKey`/`KeySet`, and `JWTClaimsRegistry`. The dependency declaration in `madsci.auth_manager` and `madsci.client` swaps `Authlib>=1.3.0` for `joserfc>=1.0.0`. JWT format and verification semantics are unchanged.

## Capabilities

### New Capabilities

_None._ All changes modify capabilities introduced by `auth-manager-foundation`.

### Modified Capabilities

- `auth-manager-service`: admin endpoint authorization, lab_id-required bootstrap, router refactor, audit-log failure-closed semantics, `X-Forwarded-For` gating.
- `auth-token-lifecycle`: algorithm pinning, clock-skew leeway, atomic refresh-token consumption, `rotated_to` linkage, introspect/revoke authentication.
- `auth-client-integration`: `AuthClient` algorithm pinning on verification, CLI bootstrap password no longer accepted via argv.

## Impact

- **Code:** `src/madsci_auth_manager/madsci/auth_manager/auth_server.py` (split into routers), `services/token_service.py`, `services/audit_logger.py`, `services/signing_key_service.py`, `server_types.py` (new settings field), `tables.py` (potential index for `(token_hash, revoked_at)`), `src/madsci_common/madsci/common/auth_middleware.py` (mount on Auth Manager, allowlist), `src/madsci_common/madsci/common/auth_decorators.py` (harden `project_from`), `src/madsci_client/madsci/client/auth_client.py` (alg pinning), `src/madsci_client/madsci/client/cli/commands/auth.py` (drop `--password` argv).
- **Operators:** Anyone running the Auth Manager with `auth_enabled=True` must now hold a token with `auth.*` permission to call admin endpoints. Bootstrap CLI now prompts for password instead of accepting `--password`. Operators behind a load balancer must explicitly set `auth_trust_forwarded_for=true`. Deployments without `lab_id` will fail to start.
- **Database:** Possible new partial unique index on `refresh_tokens(token_hash) WHERE revoked_at IS NULL` (Alembic migration `0002_*`). No data migration required.
- **Tests:** ~25 new tests in `src/madsci_auth_manager/tests/` and `src/madsci_common/tests/test_auth_*.py`.
- **Docs:** `docs/guides/auth.md` documents the admin permission model; `docs/guides/auth_operator.md` updates the bootstrap flow and the trusted-proxy setting.
- **Dependencies:** `Authlib>=1.3.0` replaced with `joserfc>=1.0.0` in `madsci.auth_manager` and `madsci.client`. `joserfc` was already pulled in transitively by Authlib 1.7+, so no install footprint change.
- **Sequencing:** This change MUST land after `auth-manager-foundation` (PR #310) merges, ideally in the same release.
