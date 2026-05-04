# Auth Manager — Operator Runbook

Practical operational guide for deploying and running the MADSci Auth Manager.

## Bootstrap

```bash
# 1. Start the Auth Manager service (port 8007)
python -m madsci.auth_manager.auth_server

# 2. Bootstrap (creates admin user, signing keypair, built-in roles)
madsci auth bootstrap --username admin --lab-id <lab_id>
# You will be prompted for the admin password.
```

`bootstrap` is idempotent — re-running against a populated database is a no-op.

## Secret distribution

When you register a service account or node identity, the Auth Manager returns the `client_secret` in plaintext **exactly once**. Capture it immediately and write it to disk under `.madsci/secrets/`:

```bash
madsci auth manager register --manager-id <ulid>
# {
#   "client_id": "sa-...",
#   "client_secret": "...",
#   ...
# }
```

**Required filesystem hygiene:**

| Path                              | Owner       | Mode    | `.gitignore`?    |
|-----------------------------------|-------------|---------|------------------|
| `.madsci/secrets/`                | service uid | `0700`  | yes              |
| `.madsci/secrets/<client_id>.txt` | service uid | `0600`  | (covered by dir) |

The bundled `manager` and `node` templates ship `.gitignore` entries that exclude `.madsci/secrets/`. Verify yours does the same before committing.

If you suspect a secret has leaked, rotate immediately:

```bash
madsci auth credentials rotate <client_id>
```

The old secret is invalidated atomically; only the new one will work for `client_credentials` token exchange after the call returns.

## Key rotation

```bash
# Add a new active signing key (current key remains in JWKS for verification)
madsci auth keys rotate

# Once all tokens issued by the old key have expired (≥ access_token_ttl after the rotation):
madsci auth keys retire <old_kid>
```

`madsci auth keys list` shows all keys, their `active_for_signing` flag, and creation time. `GET /health/keys` reports `active_keys`, `signing_kid`, and `oldest_key_age_seconds` for monitoring.

## HTTPS termination & reverse proxy

Run the Auth Manager behind a TLS-terminating reverse proxy (Caddy, nginx, Envoy). The Auth Manager uses `X-Forwarded-For` to record the source IP in audit-log entries, so the proxy MUST be configured to forward real client IPs:

```nginx
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Real-IP $remote_addr;
```

Without this, every audit row will show the proxy's loopback IP and the audit log will be useless for incident response.

## Audit-log retention & PII

The `audit_log` table holds: timestamps, principal IDs, grant types, JTIs, and source IPs. It deliberately does NOT hold passwords, secrets, or full request bodies (per Decision 1's rate-limiting requirement and the related spec).

Operators are responsible for:

- **Retention policy.** No automatic deletion; size with the deployment's auth volume.
- **PII review.** Source IPs and usernames may be PII under your jurisdiction's regulations (GDPR Art. 4, CCPA, etc.). Document handling in your Records of Processing Activities.
- **Read-access auditing.** Anyone with database read can inspect the table; layer DB-level auth separately.

## Local audit-log fallback

If a consuming manager cannot deliver an authentication-related audit event to the Auth Manager (network partition, 5xx), the event is appended to a local on-disk fallback at `local_audit_log_path` (default `.madsci/audit/auth-fallback.log`). A drain task retries delivery on a configurable interval; events are removed locally only after the Auth Manager confirms persistence.

The fallback is bounded by `local_audit_log_max_bytes` (default **100 MB**). When exceeded, the oldest segment is rotated out and a structured warning event is emitted.

> **Strong recommendation:** alert on the rotation warning event (event_type `auth_fallback_rotation`) so you upsize `local_audit_log_max_bytes` *before* the bound bites at high request rates and you start dropping events.

## Migration plan (auth_enabled → auth_required)

Per-manager rollout:

1. Set `auth_enabled=True, auth_required=False` (migration mode).
2. Watch logs for "AuthMiddleware: unauth'd request" warnings. They tell you which callers still need credentials.
3. Update those callers (CI/CD, scripts, notebooks) to acquire and present tokens.
4. When the warnings dry up, flip `auth_required=True` and restart.
5. The future MADSci release deprecates `auth_required=False`; the release after that removes it.

This is also when caller-asserted `OwnershipInfo` is removed (Decision 10 couples the two deprecations to keep operators on a single migration jump).

## Disaster recovery

- **Backup the Auth Manager database.** Use `madsci-postgres-backup` (`madsci.common.backup_tools.PostgreSQLBackupTool`). Take backups before key rotations and at the same cadence as your other PostgreSQL DBs.
- **Lost signing key.** Generate a new signing key (`madsci auth keys rotate`); existing tokens issued by the lost key keep validating until expiry (≤ `access_token_ttl`). Retire the lost key once expired.
- **Compromised admin secret.** `madsci auth user password <user_id>` to rotate; revoke any active access tokens with `POST /revoke`.
