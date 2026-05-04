# MADSci Auth Manager

The Auth Manager (port 8007) is MADSci's authentication and authorization service.

It is responsible for:

- **Identity** — User accounts (Argon2id-hashed passwords), Projects, Service
  Accounts (managers), and Node Identities.
- **Tokens** — RS256 JWT access tokens + opaque, server-stored refresh tokens.
  Standard OAuth 2.0 grants: `password`, `refresh_token`, `client_credentials`.
- **JWKS** — Rotating signing keypairs published at `/.well-known/jwks.json`
  for stateless verification at every consuming manager.
- **RBAC** — Roles, role-permission mappings, and project-scoped grants.
- **Audit log** — Append-only record of every security-relevant event.
- **Deny-list** — Persistent revoked-`jti` table polled by consuming managers
  for bounded-SLA access-token revocation.

## Layout

- `auth_server.py` — `AuthManager(AbstractManagerBase[AuthManagerSettings])`
- `tables.py` — SQLModel tables (users, projects, memberships, roles,
  role_permissions, service_accounts, node_identities, refresh_tokens,
  revoked_access_tokens, signing_keys, audit_log)
- `services/` — `SigningKeyService`, `TokenService`, `PasswordService`,
  `AuditLogger`, `DenyListService`
- `alembic/` — schema migrations
- `migration_tool.py` — startup migration runner with auto-backup

## Quick Start

```bash
# Bootstrap (creates admin user, first signing key, built-in roles)
madsci auth bootstrap --username admin

# Start the server
python -m madsci.auth_manager.auth_server
```

See `docs/guides/auth.md` and `docs/guides/auth_operator.md` for the full
architecture, token model, RBAC concepts, and operator runbook.
