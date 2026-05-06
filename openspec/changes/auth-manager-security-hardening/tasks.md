## 1. Algorithm pinning (C3)

- [x] 1.1 Add `algorithms=["RS256"]` to `jwt.decode(...)` in `src/madsci_auth_manager/madsci/auth_manager/services/token_service.py:226`
- [x] 1.2 Add `algorithms=["RS256"]` to `jose_jwt.decode(...)` in `src/madsci_client/madsci/client/auth_client.py:230`
- [x] 1.3 Add a unit test that constructs an HS256 token using the lab's RS256 public key as HMAC secret and asserts both verification paths reject it (`tests/test_auth_server.py` and `tests/test_auth_client.py`)
- [x] 1.4 Add a unit test that constructs an `alg=none` token and asserts both verification paths reject it

## 2. Refuse unbound lab_id (C5)

- [x] 2.1 Remove the `"lab-unbound"` literal from `src/madsci_auth_manager/madsci/auth_manager/auth_server.py:191` and any other references
- [x] 2.2 In `AuthManager.initialize` (or startup hook), raise `RuntimeError` with a clear message if `settings.lab_id` is unset/empty
- [x] 2.3 In every token-issuance path, defensive-check `lab_id` and respond HTTP 503 with `{"error": "lab_id_unbound"}` if it has become unset
- [x] 2.4 Update test fixtures in `src/madsci_auth_manager/tests/` to pass an explicit `lab_id` (use `new_ulid_str()`)
- [x] 2.5 Add a test asserting the manager refuses to start without `lab_id`

## 3. Atomic refresh-token consumption (C4)

- [x] 3.1 Replace the read-then-write pattern in `consume_refresh_token` (`token_service.py:149-180`) with a single `UPDATE refresh_tokens SET revoked_at = now(), rotated_to = <new_jti> WHERE token_hash = ? AND revoked_at IS NULL RETURNING ...`
- [x] 3.2 If 0 rows updated, re-fetch by `token_hash` to distinguish unknown vs already-revoked, and fire `_revoke_all_for_principal` on already-revoked
- [x] 3.3 Generate the new refresh-token jti before the UPDATE so it can be passed into `rotated_to` in one statement
- [x] 3.4 Create Alembic migration `0002_refresh_token_partial_unique_index` adding a partial unique index `refresh_tokens(token_hash) WHERE revoked_at IS NULL`
- [x] 3.5 Add a concurrency test using `concurrent.futures.ThreadPoolExecutor` (or equivalent) firing N parallel `consume_refresh_token` calls against the same token; assert exactly one returns success, all others raise `TokenError`, and the principal's family was revoked
- [x] 3.6 Verify SQLite ≥ 3.35 in CI (test fixture asserts `sqlite3.sqlite_version >= "3.35"`)

## 4. Auth Manager admin authorization (C1)

- [x] 4.1 Define the permission strings in one place (e.g., `src/madsci_auth_manager/madsci/auth_manager/permissions.py`): `auth.user.read`, `auth.user.write`, `auth.project.read`, `auth.project.write`, `auth.role.read`, `auth.role.write`, `auth.role.grant`, `auth.principal.write`, `auth.credentials.rotate`, `auth.key.read`, `auth.key.rotate`, `auth.key.retire`, `auth.token.introspect`, `auth.token.revoke`
- [x] 4.2 Seed the built-in `admin` role with all `auth.*` permissions in the bootstrap path
- [x] 4.3 Mount `AuthMiddleware` on the Auth Manager's FastAPI app via `AbstractManagerBase` (verify it picks up the manager's own `auth_enabled`/`auth_required` settings)
- [x] 4.4 Define the unauthenticated allowlist (`/token`, `/.well-known/jwks.json`, `/health`, `/health/keys`, `/settings`, `/deny-list`) — confirm the middleware supports an exemption list, and add one if not
- [x] 4.5 Decorate every admin route in `auth_server.py` (lines 673-1080) with `@requires(permission=...)` per the mapping in design D9
- [x] 4.6 Add tests that, for each admin endpoint, assert: (a) HTTP 401 with no token, (b) HTTP 403 with a token lacking the permission, (c) HTTP 200 with the right permission

## 5. Introspect/revoke authentication (C2)

- [x] 5.1 Add `@requires(permission="auth.token.introspect")` to `/introspect`; on 401/403 return `{"active": false}` (HTTP 200) instead of the usual error response, per RFC 7662
- [x] 5.2 Update `/revoke` to require authentication; allow self-revocation when `request.state.principal.sub == token.sub`; otherwise require `auth.token.revoke`
- [x] 5.3 Tests: unauthenticated `/introspect` returns `{"active": false}`; unauthenticated `/revoke` returns 401; cross-principal `/revoke` without permission returns 403; self-revocation succeeds

## 6. Bootstrap CLI password handling (S1)

- [x] 6.1 Remove the `--password` Click option from `src/madsci_client/madsci/client/cli/commands/auth.py`
- [x] 6.2 Source the password from `os.environ.get("MADSCI_AUTH_BOOTSTRAP_PASSWORD")` if set
- [x] 6.3 Otherwise, call `click.prompt("Admin password", hide_input=True, confirmation_prompt=True)`
- [x] 6.4 If neither is available (non-TTY and no env var), exit non-zero with a clear error
- [x] 6.5 Update `tests/test_cli_auth.py` to cover env-var path and to assert `--password` is no longer a recognized option

## 7. Clock-skew leeway (S2)

- [x] 7.1 Add `token_clock_skew_seconds: int = 30` to `AuthManagerSettings` in `server_types.py`
- [x] 7.2 Pass `leeway=settings.token_clock_skew_seconds` to the JOSE library's claims validation in `verify_token`
- [x] 7.3 Pass the same leeway to `AuthClient`'s verification path (settable on the client; default 30)
- [x] 7.4 Tests: token with `iat` slightly in the future verifies; token with `exp` outside leeway is rejected

## 8. Failure-closed audit log (S4)

- [ ] 8.1 Refactor `audit_logger.py` so audit writes accept the active `Session` and run inside the caller's transaction _(deferred — out of scope; would require restructuring every handler to share a session. Current `AuditLogger.log()` raises on DB failure, which propagates through FastAPI — see 8.3.)_
- [ ] 8.2 Update `_handle_password_grant`, `_handle_refresh_grant`, `_handle_client_credentials_grant`, and every admin handler to share the same `Session` between operation and audit write _(deferred with 8.1)_
- [x] 8.3 On audit-write failure, raise — let the transaction roll back; do NOT silently swallow _(audit failures now propagate; FastAPI converts to 500. The issued access JWT is in-memory only at that point and never returned. The refresh-token row IS already persisted, but only its hash — the opaque token never leaves the server.)_
- [ ] 8.4 Wire `auth_audit_fallback` into the issuer side _(deferred — `auth_audit_fallback` remains a consumer-side mechanism. Out of scope for this PR; tracked as follow-up in `docs/guides/auth.md`.)_
- [x] 8.5 Tests: induce an audit-write failure (e.g., monkeypatch the audit insert to raise), assert the calling operation also fails and no token is returned

## 9. X-Forwarded-For trust gating (S5)

- [x] 9.1 Add `auth_trust_forwarded_for: bool = False` to `AuthManagerSettings`
- [x] 9.2 Update `_client_ip` (`auth_server.py:120`) to consult the setting; default returns socket peer
- [x] 9.3 When trusted, parse leftmost `X-Forwarded-For` value, normalize, validate as IP; on parse failure, fall back to socket peer
- [x] 9.4 Tests: default ignores `X-Forwarded-For`; opt-in honors it; malformed header falls back to socket peer

## 10. Refresh-token forensics: rotated_to (S3)

- [x] 10.1 Implementation already covered by 3.1 — verify the `rotated_to` column is populated by the atomic UPDATE
- [x] 10.2 Add a test asserting that after rotation, the parent row's `rotated_to` is the new token's identifier

## 11. Router refactor (S6 / D9)

- [ ] 11.1 Create routers/ package _(deferred per 11.5 — refactor would exceed the design's 200-line bound)_
- [ ] 11.2 Move route handlers _(deferred per 11.5)_
- [ ] 11.3 Update `create_server` _(deferred per 11.5)_
- [x] 11.4 Re-run the full auth test suite; all 65 prior tests + new tests SHALL pass _(91 tests pass — 65 baseline + 24 new hardening tests + 2 new CLI tests)_
- [x] 11.5 Decision: defer the refactor. Authorization landed without the split. Follow-up tracked in `docs/guides/auth.md`.

## 12. Documentation updates

- [x] 12.1 Update `docs/guides/auth.md` with the admin-permission model and the full list of `auth.*` permissions
- [x] 12.2 Update `docs/guides/auth_operator.md` bootstrap section: env-var-or-prompt password, `lab_id` required, `auth_trust_forwarded_for` opt-in
- [x] 12.3 Add a CHANGELOG entry under "Unreleased" / "Changed" + "Security"
- [x] 12.4 Regenerate `docs/Configuration.md` (auto-generated) so the new settings appear

## 14. JOSE library migration (D10)

- [x] 14.1 Swap `from authlib.jose import jwt` for `from joserfc import jwt` in `services/token_service.py`; add `RSAKey`, `KeySet`, `JWTClaimsRegistry` imports
- [x] 14.2 Update `issue_access_token` to construct `RSAKey.import_key(pem, parameters={"kid": ...})` and call `jwt.encode(...)` (returns `str` directly; drop the `.decode()`)
- [x] 14.3 Update `verify_token` to build a `KeySet` from active public keys, call `jwt.decode(token, key_set, algorithms=["RS256"])`, then validate via `JWTClaimsRegistry(...).validate(decoded.claims)` with `leeway`
- [x] 14.4 Swap `from authlib.jose import jwt as jose_jwt` for `from joserfc import jwt as jose_jwt` in `client/auth_client.py`; update `verify_jwt` to use `KeySet.import_key_set(jwks_dict)`, `jose_jwt.decode(...)`, and `JWTClaimsRegistry`
- [x] 14.5 Update `tests/test_security_hardening.py` token-construction helpers to use `joserfc`'s `jwt.encode` + `RSAKey.import_key`
- [x] 14.6 Replace `Authlib>=1.3.0` with `joserfc>=1.0.0` in `src/madsci_auth_manager/pyproject.toml` and `src/madsci_client/pyproject.toml`
- [x] 14.7 Run the auth test suite; confirm 92/92 pass and the `AuthlibDeprecationWarning` is gone

## 15. Security-review HIGH mitigation (post-implementation review)

The first `/security-review` pass after implementation found one HIGH issue plus
two filtered defense-in-depth findings. Mitigations:

- [x] 15.1 **HIGH (Vuln 1):** Override `auth_enabled` and `auth_required` defaults to `True` on `AuthManagerSettings`. Mitigates the foundational issue that `@requires` no-ops when middleware isn't installed and `AuthManagerSettings` inherited `auth_enabled=False` from `ManagerSettings` — leaving every admin route unauthenticated on a fresh deployment.
- [x] 15.2 **HIGH (defense in depth):** `AuthManager._setup_auth_middleware` override installs a self-verifying `AuthMiddleware` (uses local `TokenService` rather than a remote `AuthClient`), avoiding the prefixed-alias collision that prevented the base-class path from picking up `auth_server_url`.
- [x] 15.3 **HIGH (defense in depth):** `AuthManager.run_server()` override refuses to bind unless both `auth_enabled` and `auth_required` are `True`. Catches misconfiguration at the startup boundary.
- [x] 15.4 **Filtered (`AuthClient` skips `iss`/`aud` validation):** Added `expected_issuer` and `expected_audience` constructor args to `AuthClient`; `verify_jwt` includes them in `JWTClaimsRegistry` when set. `manager_base._setup_auth_middleware` plumbs the manager's `auth_server_url` and `lab_id` through automatically.
- [x] 15.5 **Filtered (`/revoke` refresh-token branch lacks self-vs-other check):** `revoke_endpoint` now probes the refresh-token row's `principal_sub` and applies the same self-vs-other rule before revoking.
- [x] 15.6 Updated test fixtures in `test_auth_server.py`, `test_integration.py` (via `testing.make_auth_manager`'s new `auth_enforced=False` default), `test_auth_client.py`, `test_cli_auth.py`, and `test_security_hardening.py::server` to explicitly opt out of enforcement (preserves their unit-test semantics with the new safe defaults).
- [x] 15.7 New tests pin the invariants: `test_auth_manager_settings_default_to_auth_enabled`, `test_auth_manager_run_server_refuses_unsafe_config`, `test_cross_principal_refresh_token_revoke_requires_permission`, `test_auth_client_rejects_token_with_wrong_audience`.
- [x] 15.8 Re-ran auth suite (96/96) + full pytest (4202/4202) + project-wide `ruff check .` (clean).

## 13. Verification & release gates

- [x] 13.1 `pytest src/madsci_auth_manager src/madsci_common/tests/test_auth_*.py src/madsci_client/tests/test_auth_*.py src/madsci_client/tests/test_cli_auth.py` — all green (96/96)
- [x] 13.2 Full `pytest` — no regressions (4202/4202)
- [x] 13.3 `ruff check .` clean
- [x] 13.4 First `security-review` skill pass complete; HIGH finding + two filtered findings mitigated in Section 15. _(Re-review still recommended pre-merge.)_
- [x] 13.5 First `madsci-release-audit` skill pass complete: stale `--password` in example lab README fixed, stale `Authlib` dep removed from `madsci_common`, stale "authlib's decoder" comment fixed in `token_service.py`. Audit findings recorded in `.scratch/auth_manager_security_hardening_audit.md`.
- [ ] 13.6 Manual smoke against example lab: `just up`, then `madsci auth bootstrap` (env-var path), exercise `/token`, `/.well-known/jwks.json`, and assert admin endpoints reject unauthenticated calls _(operator to perform pre-merge — Docker required)_
