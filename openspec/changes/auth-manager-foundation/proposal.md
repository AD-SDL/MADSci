## Why

MADSci has no authentication or authorization on any of its services — every manager endpoint is open to anyone with network access, and the existing `OwnershipInfo` metadata is propagated only as in-process Python contextvars, never validated against requests. As MADSci moves toward shared/multi-tenant lab deployments, federated experiments, and external integrations (Globus, ORCID), this gap blocks downstream features and presents a real security risk. Issue #86 has been open since the early days; the work is now a dependency for layered location ownership, federated experiments, and the SiLA2 migration's node trust model.

## What Changes

- **NEW** `madsci_auth_manager` package: a new manager service (port 8007) implementing user, project, service-account, and node-identity records, plus token issuance/introspection endpoints.
- **NEW** `AuthClient` in `madsci_client` providing token acquisition, automatic refresh, JWKS-based verification, and ambient-context binding so other clients pick up credentials transparently.
- **NEW** Pluggable `AuthMiddleware` for `AbstractManagerBase` that validates bearer tokens and populates `OwnershipInfo` from JWT claims (default-off behind `auth_enabled` setting for backwards compat).
- **NEW** Local user accounts with Argon2 password hashing; **OPTIONAL** OIDC federation hooks (Globus, ORCID) deferred to follow-on changes but designed-for in this foundation.
- **NEW** Capability/role model: `Role`, `Permission`, project membership, and a `@requires(...)` decorator usable on manager endpoints.
- **NEW** Service-to-service identity via OAuth 2.0 client-credentials grant for managers and nodes; bootstrap tokens issued by the Auth Manager at startup.
- **MODIFIED** All existing service clients (`EventClient`, `ExperimentClient`, etc.) gain optional auth-header injection driven by an ambient `AuthClient`.
- **MODIFIED** `OwnershipInfo` semantics: when auth is enabled, fields like `user_id`/`project_id` MUST come from validated token claims rather than caller-supplied values.
- **NEW** Operator documentation covering bootstrap (initial admin user, signing key generation), HTTPS termination patterns, and a backwards-compat migration path.
- **NOT IN SCOPE for this change** (called out so reviewers don't expect them): mTLS for nodes, full Globus/ORCID federation, UI login flows, distributed/multi-lab Auth Manager federation. These will be follow-on changes built on this foundation.

This is a **non-breaking** change at the deployment level (auth defaults to disabled), but **forward-incompatible** for code paths that assume `OwnershipInfo` is freely caller-asserted: once a deployment enables auth, callers must hold valid tokens and ownership claims become authoritative.

## Capabilities

### New Capabilities

- `auth-identity-model`: User, Project, ServiceAccount, NodeIdentity, Role, and Permission entities, including project membership and role grants.
- `auth-token-lifecycle`: Token issuance (password grant, refresh grant, client-credentials grant), introspection, revocation, JWKS publication, and signing-key rotation.
- `auth-manager-service`: The `madsci_auth_manager` HTTP service surface — endpoints, settings, persistence, bootstrap, and lifecycle — built on `AbstractManagerBase`.
- `auth-client-integration`: The `AuthClient`, the `AuthMiddleware` for `AbstractManagerBase`, and the contract by which existing service clients and middleware acquire/verify/propagate credentials and bind validated claims into `OwnershipInfo`.

### Modified Capabilities

<!-- No existing OpenSpec capabilities have requirements that change as part of this foundation. The existing `OwnershipInfo` type and ambient context are reused without spec-level changes; downstream managers will gain auth enforcement in follow-on changes. -->

## Impact

- **New package**: `src/madsci_auth_manager/` (settings, server, persistence, token service, bootstrap CLI).
- **Modified packages**: `madsci_common` (auth types extension, `OwnershipInfo` claim binding, `AuthMiddleware` hook on `AbstractManagerBase`), `madsci_client` (new `AuthClient`, optional auth-header injection in `create_httpx_client`).
- **New dependencies**: `Authlib` (OIDC client + JWT issuance), `argon2-cffi` (password hashing), `cryptography` (signing key management). All are mature, audited, and FOSS-licensed.
- **New database**: PostgreSQL schema for users, projects, memberships, roles, service accounts, node identities, refresh tokens, and audit log. Reuses existing PostgreSQL infrastructure.
- **New port**: 8007 reserved for the Auth Manager (slots in after Location Manager at 8006).
- **Operator surface**: New CLI subcommands (`madsci auth bootstrap`, `madsci auth user create`, `madsci auth keys rotate`); new compose service in example lab; new docs page.
- **Backwards compatibility**: All managers default to `auth_enabled=False`; existing labs continue to operate unchanged. A deployment opts into auth by enabling the Auth Manager and flipping per-manager settings.
- **Coordination**: Intersects with the in-flight SiLA2 migration project (#293/#294) — node-identity decisions in this change must be compatible with SiLA2's TLS-based trust model. Also intersects with Issue #210 (layered location ownership), which becomes implementable once `OwnershipInfo` is authoritative.
- **Risk**: This is a security-critical subsystem; test coverage and a security review are required before enabling by default in any release.
