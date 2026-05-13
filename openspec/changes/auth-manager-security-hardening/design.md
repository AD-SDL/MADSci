## Context

`auth-manager-foundation` (PR #310) shipped the first end-to-end Auth Manager: RS256 JWT issuance, opaque refresh tokens, JWKS, deny-list, audit log, RBAC, and `AuthMiddleware`. A senior security review found that the foundation was correct in its cryptographic primitives (RS256-only issuance, Argon2id, hashed refresh tokens, contextvars-based ambient propagation) but had a class of consistent gaps: the Auth Manager itself never bothered to authenticate its own callers, JWT verification trusted the JWKS algorithm field, refresh-token consumption was racy, and the audience claim defaulted to a literal string that two unbound labs would mutually trust.

The hardening must land before any operator turns `auth_enabled=True` — otherwise enabling auth does not improve security, it just adds latency. The change is small in surface area (one repo, one package, mostly the auth manager and middleware), but it is high-impact: each fix closes a class of attack rather than a single bug.

This design describes the technical approach for each fix; the proposal lists what changes and why, and `tasks.md` enumerates the work.

## Goals / Non-Goals

**Goals:**
- Eliminate the unauthenticated administrative surface on the Auth Manager.
- Make JWT verification refuse anything other than RS256 by configuration, not by accident.
- Make refresh-token consumption atomic and reuse detection unambiguous.
- Refuse to operate without an explicit `lab_id`; remove the `"lab-unbound"` literal.
- Remove the password-via-argv leak path.
- Make the audit log failure-closed for state-changing auth operations.
- Add the test coverage that would have caught the above.

**Non-Goals:**
- mTLS for nodes (deferred to `auth-node-mtls`).
- Per-principal `aud` narrowing (deferred to `auth-per-principal-aud-narrowing`).
- Federated identity / Globus / ORCID (deferred to `auth-globus-orcid-federation`).
- Rolling out `@requires` to every other manager's endpoints (`auth-per-manager-rbac-rollout`).
- Replacing pre-provisioned NodeIdentity registration (`auth-node-enrollment-tokens`).
- Splitting `auth_server.py` is in scope as a refactor, but only because it materially helps reviewers verify per-router authorization. If the refactor balloons in size, it can split out into its own change.

## Decisions

### D1: Mount `AuthMiddleware` on the Auth Manager itself, with an explicit allowlist.

The Auth Manager is the only manager today that does not install `AuthMiddleware` on its own FastAPI app. We will install it (with the same `auth_enabled`/`auth_required` settings as every other manager) and supply an explicit unauthenticated-allowlist for the routes that must be reachable without a token:

- `POST /token` — bootstrap path for credentials.
- `GET /.well-known/jwks.json` — public key publication.
- `GET /health`, `GET /health/keys`, `GET /settings` — operator/monitor endpoints.
- `GET /deny-list` — accessed by every consuming manager's `AuthClient`. (Authenticating it would be circular and offers no security benefit since the deny-list is a list of `jti` values that are already known to the issuer.)

Every other route — including `POST /introspect` and `POST /revoke` — requires authentication. `/introspect` follows RFC 7662: `{active: false}` for unauthenticated callers (no claim leak), full claims only for authenticated holders of `auth.token.introspect`. `/revoke` allows revocation of one's own tokens (sub matches) without an additional permission, and revocation of others' tokens with `auth.token.revoke`.

**Alternatives considered:**
- *Per-route `@requires` only, no middleware*: rejected — easy to forget on new routes, no centralized enforcement, no defense in depth.
- *Authenticate `/deny-list` too, with service-account tokens*: rejected — circular dependency (a manager needs the deny-list to verify tokens, but needs a token to fetch the deny-list). The deny-list is not sensitive.

### D2: Pin `algorithms=["RS256"]` on every JWT verification.

Both `token_service.verify_token` and `AuthClient` JWT verification call `decode(token, jwks, ...)` without an `algorithms=` allowlist. We will pass `algorithms=["RS256"]` everywhere. The set is hard-coded (not configurable) because adding non-RS256 algorithms is a breaking change to the issuer too, not a runtime knob. We also keep a defense-in-depth `_enforce_algorithm` helper that pre-parses the JWS header and rejects disallowed algs before the JOSE library touches the token, in case a malformed key were ever added to the verification keyset.

### D3: Atomic refresh-token consumption via `UPDATE ... WHERE revoked_at IS NULL RETURNING ...`.

The current read-then-write pattern allows two concurrent refreshes of the same token to both succeed. We will replace `consume_refresh_token` with a single statement: update the row setting `revoked_at = now()` and `rotated_to = <new jti>` only when `revoked_at IS NULL`, then check the affected-row count. If zero rows updated, either the token doesn't exist or it was already revoked — we then re-fetch to distinguish, and if revoked, fire the family-revocation as before. Postgres supports `RETURNING`; SQLite (used in tests) supports `RETURNING` since 3.35 — sufficient for our test environment. We will also add a partial unique index (`refresh_tokens (token_hash) WHERE revoked_at IS NULL`) as a belt-and-suspenders constraint, in a new alembic migration `0002_*`.

**Alternatives considered:**
- *Application-level lock on `principal_sub`*: rejected — contention bottleneck and doesn't help in multi-process deployments.
- *`SELECT ... FOR UPDATE`*: works but two round-trips. The `UPDATE ... RETURNING` approach is one round-trip and atomic.

### D4: Refuse to issue tokens (and refuse to start) without `lab_id`.

`AuthManagerSettings.lab_id` becomes effectively required when `auth_enabled=True`. The Auth Manager's startup hook checks: if `lab_id` is unset, log an error and refuse to start. The `"lab-unbound"` literal in `auth_server.py:191` is removed. Test fixtures that don't care about lab binding can pass an explicit ULID.

### D5: Bootstrap CLI accepts password only via interactive prompt or env var.

Click `--password` option is removed. The CLI prompts via `click.prompt(hide_input=True, confirmation_prompt=True)` if neither stdin nor `MADSCI_AUTH_BOOTSTRAP_PASSWORD` is set. CI/automation uses the env var. argv-leak via `ps` is no longer possible.

### D6: Audit log writes are failure-closed for state-changing operations.

Today, audit log writes happen in a separate session from the operation. We move them into the same SQLAlchemy session, so a failed audit insert rolls back the whole transaction. For token issuance, this means: if we cannot record that we issued a token, we don't issue it. The consumer-side `auth_audit_fallback.py` mechanism is also wired into the issuer for transient DB failures: write to a local append-only file, drain on next successful DB connection. This matches the consumer-side pattern and means a brief DB blip doesn't take down the issuer.

**Alternatives considered:**
- *Failure-open with monitoring*: rejected — silent audit gaps are exactly the failure mode an attacker would exploit (e.g., cause DB stress, then perform a privileged action knowing the audit will be dropped).

### D7: Optional `X-Forwarded-For` trust via explicit setting.

`AuthManagerSettings.trust_forwarded_for: bool = False`. When `True`, `_client_ip` reads `X-Forwarded-For`'s left-most value (after normalizing). When `False` (default), `_client_ip` returns the socket peer. Operators behind a real proxy must opt in. This matches industry practice (FastAPI + uvicorn `--proxy-headers`).

### D8: Refresh-token forensics: populate `rotated_to`.

The schema column already exists. `consume_refresh_token` will set `rotated_to = <new_token_jti>` on the parent row at consumption time, enabling reuse-detection forensic queries (find the leaked token's family).

### D10: Migrate from `authlib.jose` to `joserfc`.

Authlib 1.7+ emits `AuthlibDeprecationWarning: authlib.jose module is deprecated, please use joserfc instead. It will be compatible before version 2.0.0.` `joserfc` is the same author's (Hsiaoming Yang) successor library, narrowly scoped to JOSE/JWT/JWK/JWA/JWE/JWS RFCs (Authlib remains the umbrella for OAuth/OIDC). `joserfc` is already pulled in as a transitive dependency by Authlib 1.7+, so no install footprint change.

We migrate all three call sites:

- `TokenService.issue_access_token` — `jwt.encode(header, claims_dict, RSAKey.import_key(pem, parameters={"kid": ...}), algorithms=["RS256"])`. Returns a `str` directly (Authlib returned `bytes`, requiring a `.decode()`).
- `TokenService.verify_token` — `jwt.decode(token, KeySet([RSAKey.import_key(pub_pem, parameters={"kid": ...}) for row in active_keys]), algorithms=["RS256"])`. Claim validation is a separate call: `JWTClaimsRegistry(iss=..., aud=..., exp={"essential": True}, leeway=...).validate(decoded.claims)`.
- `AuthClient.verify_jwt` — `jwt.decode(token, KeySet.import_key_set(jwks_dict), algorithms=["RS256"])` followed by `JWTClaimsRegistry(leeway=...).validate(...)`. The JWKS is fetched as a dict from `/.well-known/jwks.json` and `KeySet.import_key_set` parses it directly.

`joserfc` enforces the algorithm allowlist via the `algorithms=` argument to both `encode` and `decode`, which complements (not replaces) D2's defense-in-depth header check.

The dependency declarations swap `Authlib>=1.3.0` for `joserfc>=1.0.0` in both `madsci.auth_manager/pyproject.toml` and `madsci.client/pyproject.toml`. JWT format and verification semantics are identical; no operator-visible change.

**Alternatives considered:**
- *Pin to a pre-deprecation Authlib version (≤1.6).* Rejected — would freeze us out of CVE patches in Authlib's transitive crypto bumps.
- *Defer the swap to a follow-on change.* Rejected — the deprecation warning is loud, the migration is small (3 call sites), and bundling it with the hardening keeps the JWT-path churn in one PR.

### D9: Router refactor in scope but bounded.

We will split `auth_server.py` into:
- `routers/token_router.py` — `/token`, `/introspect`, `/revoke`
- `routers/users_router.py` — `/users/*`
- `routers/projects_router.py` — `/projects/*`
- `routers/roles_router.py` — `/roles/*`
- `routers/principals_router.py` — `/service-accounts`, `/node-identities`, `/credentials/*`
- `routers/keys_router.py` — `/keys/*`, `/.well-known/jwks.json`, `/health/keys`
- `routers/deny_list_router.py` — `/deny-list`

Each router declares its own permissions in one place, making it trivially auditable that, e.g., every `/users/*` route requires `auth.user.*`. The `AuthManager` class shrinks to a composition root (DI for services, mounting routers, lifecycle). If the refactor exceeds ~200 lines of churn beyond the per-route `@requires` additions, we land authorization without the refactor and split routers in a follow-up.

## Risks / Trade-offs

- **[Breaking change for already-deployed labs]** → mitigation: foundation has not shipped (PR draft); this lands before any production rollout. CHANGELOG and `docs/guides/auth_operator.md` document the new behavior.
- **[`UPDATE ... RETURNING` requires SQLite ≥ 3.35]** → mitigation: project's CI Python version ships with newer SQLite; pin in `pyproject.toml` if needed.
- **[Failure-closed audit could create availability dependency on DB for token issuance]** → mitigation: audit-log fallback file means a DB blip falls back to local append; drain on reconnect. Same pattern already used on consumer side.
- **[Router refactor risk of regressing wiring]** → mitigation: existing 65 tests + new authorization tests run against the refactored code; if green, wiring is preserved.
- **[Bootstrap UX regression — operators used to `--password` for scripts]** → mitigation: env var `MADSCI_AUTH_BOOTSTRAP_PASSWORD` provides the same automation hook without the argv leak.
- **[Partial unique index on `refresh_tokens` requires a migration]** → mitigation: standard Alembic migration; the foundation already ships Alembic infrastructure with auto-backup.

## Migration Plan

1. Land foundation PR #310 (with security-review skill green ignoring this PR's items).
2. Land this hardening change in the next PR. Single Alembic migration `0002_refresh_token_partial_unique_index`.
3. Operators who already ran `madsci auth bootstrap` from the foundation see no data migration. Operators with `lab_id` unset must set it before restarting. Operators who scripted `--password` must switch to env var.
4. Rollback: revert PR; the alembic migration is downgrade-safe (drop partial unique index). Removing `AuthMiddleware` from the Auth Manager is a one-line revert.

## Open Questions

- **Q1**: Should `/deny-list` require *some* auth (e.g., a shared HMAC token) to mitigate scraping? Current decision: no, the data is non-sensitive. Revisit if `auth-per-manager-rbac-rollout` reveals a different threat model.
- **Q2**: Is 30 s the right default leeway for `iat`/`exp` validation? RFC 7519 says "small", AWS uses 5 min, Azure uses 5 min. We pick 30 s as a balance between clock-skew tolerance and revocation freshness. Configurable via `AuthManagerSettings.token_clock_skew_seconds`.
- **Q3**: Should `auth.token.revoke` be a separate permission or fall under `auth.user.write`? Current decision: separate, since revocation is a discrete operation an operator may want to delegate without granting full user-write.
