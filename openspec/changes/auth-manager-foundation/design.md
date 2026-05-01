## Context

MADSci is a microservices framework for autonomous laboratory automation. It currently runs seven manager services (Lab/Event/Experiment/Resource/Data/Workcell/Location), an arbitrary number of node servers, and experiment clients — all communicating over plain HTTP with no authentication, no authorization, and no validated identity propagation. The codebase already defines `OwnershipInfo`, `UserInfo`, and `ProjectInfo` Pydantic types in `madsci.common.types.auth_types`, plus an `ownership_context()` contextvars-based propagation system in `madsci.common.ownership`. These are used today only for logging provenance.

This change introduces the foundational identity, token, and authorization machinery — a new `madsci_auth_manager` service plus an `AuthClient`, plus the `AbstractManagerBase` middleware integration that lets every other manager opt into enforcement. It is the first phase of a multi-change roadmap (Issue #86); follow-on changes will add OIDC federation (Globus, ORCID), mTLS for nodes, the UI login flow, and per-manager authorization policies.

The work intersects with the in-flight SiLA2 migration (#293/#294) — the SiLA2 protocol uses TLS-based trust, so the node-identity model designed here must be compatible with handing a SiLA node a JWT, an mTLS cert, or both. It also unblocks the layered location ownership project (#210), which needs authoritative `OwnershipInfo`.

## Goals / Non-Goals

**Goals:**
- Establish a single, authoritative source of identity for users, projects, service accounts, and node identities across a MADSci deployment.
- Issue and verify short-lived JWT access tokens using audited libraries (Authlib + cryptography); never roll our own crypto.
- Provide an opt-in authentication enforcement path on `AbstractManagerBase` that defaults to disabled so existing deployments keep working.
- Bind validated JWT claims into `OwnershipInfo`, replacing today's caller-asserted ownership with claims-based ownership when auth is enabled.
- Define a clear permission model (Roles + per-Project membership) and a `@requires(...)` decorator pattern downstream managers can adopt.
- Provide a clean migration path: bootstrap CLI, default-disabled rollout, per-manager opt-in, deprecation of unauth'd mode in a future release.

**Non-Goals:**
- OIDC federation with Globus/ORCID — designed-for, not implemented in this change.
- mTLS for node→manager trust — left for a follow-on change once SiLA2 work lands.
- UI login flows / dashboard auth — out of scope; Vue UI integration follows separately.
- Multi-lab / federated Auth Manager topology — single-Auth-Manager-per-deployment for now.
- Per-action authorization policies inside individual managers — this change provides the *mechanism* (`@requires`, ownership claims) and a small number of canonical examples; comprehensive enforcement across every existing endpoint is staged across follow-on changes.
- Encryption-at-rest of refresh tokens / sensitive Auth Manager data — out of scope; we rely on PostgreSQL/disk-level encryption operators already configure.

## Decisions

### Decision 1: Use Authlib + PyJWT-compatible JWTs (not custom tokens, not opaque sessions)

We will issue **JWT access tokens** signed with **RS256** (rotating asymmetric keypair) and **opaque refresh tokens** stored server-side. Token validation in client services uses `Authlib`'s JWT module, fetching the public JWKS from the Auth Manager's `/.well-known/jwks.json` endpoint with a TTL-based cache.

**Why JWT over opaque-only tokens:** Stateless verification at every manager — no per-request introspection round-trip to the Auth Manager. Critical for the high-throughput inter-service traffic (workcell → nodes during workflow execution).

**Why RS256 over HS256:** Asymmetric signing means downstream managers verify with the public key only; they never hold a secret that could be exfiltrated to forge tokens. Key rotation is also straightforward via JWKS.

**Why Authlib over PyJWT alone:** Authlib gives us JWT issuance, JWKS, OAuth 2.0 grant flows, and the OIDC client all from one battle-tested library — reducing the surface area we maintain and prepping us for Phase 5 (Globus/ORCID).

**Alternatives considered:**
- *Opaque tokens with introspection on every request*: rejected — too much latency and creates a single-point hotspot at the Auth Manager.
- *PASETO*: rejected — newer, smaller ecosystem, no clear advantage over correctly-implemented JWT + Authlib.
- *Roll our own*: explicitly rejected per project guidance and well-known security pitfalls.

### Decision 2: Argon2 (via argon2-cffi) for password hashing

Local-user passwords use Argon2id with sensible defaults (time_cost=3, memory_cost=64 MiB, parallelism=4 — tunable in settings). Argon2 is the OWASP-recommended modern KDF and is the winner of the Password Hashing Competition.

**Alternatives considered:** bcrypt (older, no memory hardness), scrypt (less actively maintained Python bindings), PBKDF2 (allowed by NIST but weaker than Argon2 against GPU attacks).

### Decision 3: PostgreSQL via SQLModel for persistence

The Auth Manager uses **PostgreSQL via SQLModel**, matching the Resource Manager's pattern. Auth data is intrinsically relational (users ↔ memberships ↔ projects ↔ roles) and we want strong ACID guarantees, foreign keys, and unique constraints — all things document storage handles poorly.

We will reuse the existing `SQLAlchemyHandler` abstraction from `madsci.common.db_handlers`, including the in-memory `SQLiteHandler` for tests.

**Alternatives considered:** FerretDB (used by Event/Workcell/Data) — rejected because relational integrity matters here far more than schema flexibility.

### Decision 4: AuthMiddleware on AbstractManagerBase, opt-in via setting

We add `auth_enabled: bool = False` and `auth_required: bool = False` settings to `MadsciBaseSettings`, plus an `auth_server_url` pointing at the Auth Manager. When `auth_enabled` is true, `AbstractManagerBase` registers an `AuthMiddleware` that:

1. Extracts `Authorization: Bearer <jwt>` from the request.
2. Verifies signature against cached JWKS.
3. Checks `exp`, `iss`, `aud`.
4. Populates `request.state.principal` with the validated subject + ownership claims.
5. Enters an `ownership_context()` for the request lifetime, sourced from token claims.

When `auth_required=True`, requests without a valid token return 401. When `auth_required=False` (the migration mode), unauth'd requests are allowed but `request.state.principal` is None and `OwnershipInfo` is unset — letting deployments roll out gradually.

**Alternatives considered:** Per-manager middleware duplication — rejected, hugely error-prone. Implicit always-on after first release — rejected, breaks every existing deployment.

### Decision 5: Permission model — RBAC with project-scoped grants (not pure ABAC)

A user is granted **roles** within the **scope of a project** (or globally, for system roles like `admin`). Each role has a set of **permissions** (e.g., `experiment.write`, `node.execute_action`, `resource.read`). Service accounts and node identities also have role grants but typically scoped globally or to a workcell.

Authorization checks compose: `@requires(permission="experiment.write", project_from="experiment_id")` reads the project from the experiment's ownership and checks the principal's roles within that project.

**Why RBAC + project scoping (not pure ABAC):** It maps cleanly onto the existing `OwnershipInfo` hierarchy (project_id is already a first-class field), is widely understood by operators, and avoids the policy-language complexity of ABAC (OPA/Cedar) for a first foundation. ABAC can be layered later as a Phase 6 enhancement if needed.

### Decision 6: Service identity via OAuth 2.0 client-credentials grant

Each manager and node has a **ServiceAccount** (for managers) or **NodeIdentity** (for nodes) record in the Auth Manager. At startup the service exchanges a `client_id` + `client_secret` for a JWT via the standard OAuth 2.0 client-credentials grant. The `AuthClient` handles refresh transparently before expiry.

Bootstrap secrets are issued by `madsci auth manager register <manager_id>` / `madsci auth node register <node_id>` and stored in `.madsci/secrets/`. Operators can rotate them with `madsci auth credentials rotate`.

### Decision 7: New port allocation — 8007

Auth Manager runs on **port 8007**, slotted in after Location Manager (8006). Reserved in port-allocation docs.

## Risks / Trade-offs

- **[Risk] Adding auth to a previously-open system breaks every script in the wild.** → Mitigation: default `auth_enabled=False`; operators opt in. Two-stage rollout per manager (`auth_enabled=True, auth_required=False` first to observe, then flip `auth_required=True`). Migration guide in docs.
- **[Risk] Compromise of the Auth Manager signing key forges tokens for the entire deployment.** → Mitigation: RS256 + key rotation via JWKS (multiple active keys at once). Operator runbook for emergency rotation. Document encrypted-at-rest storage of the private key.
- **[Risk] JWKS cache staleness causes valid tokens to be rejected (or revoked keys to be accepted).** → Mitigation: short TTL (5 min) + on-401 forced refresh in `AuthClient`. Document max revocation lag.
- **[Risk] Refresh-token theft enables persistent compromise.** → Mitigation: refresh tokens are opaque + server-side stored + bound to a session; revocation endpoint flushes them; rotation on every refresh.
- **[Risk] Performance hit on inter-service calls from JWT verification.** → Mitigation: verification is local + cached; benchmark in CI. If this becomes hot, switch to caching verified-claim results per-token-hash.
- **[Trade-off] Stateless JWTs make instant revocation hard.** → Accepted — short access-token TTL (15 min) bounds blast radius; long-term blocking is via refresh-token revocation + a small in-memory `jti` deny-list synced from the Auth Manager when needed.
- **[Trade-off] Bootstrap secrets on disk for service accounts/nodes.** → Accepted — same trust model as today's compose-mounted secrets; documented; mTLS in a follow-on change improves this for nodes.
- **[Risk] Incompatible identity model with SiLA2 node trust.** → Mitigation: Coordinate explicitly with SiLA2 owner; define `NodeIdentity` to carry both `client_credentials` *and* (future) `mtls_cert_fingerprint`; design review with SiLA2 work before merge.
- **[Risk] Scope creep — every manager wants its own permissions modeled now.** → Mitigation: this change ships the *mechanism* + Auth Manager itself + ownership-claim binding; per-manager `@requires` rollout is staged in follow-on changes (one per manager).

## Migration Plan

**Per-deployment rollout:**
1. Operator deploys Auth Manager service; runs `madsci auth bootstrap` (creates initial admin user + signing keys).
2. Operator registers each manager and node, distributes client secrets to each service.
3. Operator sets `auth_enabled=True, auth_required=False` on each manager → middleware runs but doesn't block. Logs validate that real traffic carries valid tokens.
4. Once green, operator flips `auth_required=True` per manager.
5. Subsequent MADSci release deprecates `auth_required=False`; release after that removes it.

**Rollback:** Set `auth_enabled=False` per-manager and restart. Auth Manager can remain running idle.

**Tests / CI:** New end-to-end test that boots the Auth Manager + one consuming manager + one node in compose, exercises the full bootstrap → token → call → revoke flow.

## Open Questions

1. **Token audience scoping** — Should access tokens carry a single `aud` (the deployment) or an array (`event-manager`, `workcell-manager`, …) for tighter blast-radius? Recommend single `aud=lab_id` for v1, revisit if needed.
2. **Node-identity issuance UX** — Do nodes self-register at startup against an enrollment token (Kubernetes-style), or are they pre-provisioned by the operator? Recommend pre-provisioned for v1; enrollment-token flow is a Phase 4 follow-on.
3. **OwnershipInfo back-compat** — When auth is disabled, do we keep accepting caller-asserted `OwnershipInfo`? Recommend yes, behind a deprecation warning, with removal scheduled for the same release that removes `auth_required=False`.
4. **`enable_registry_resolution` interaction** — The registry resolves manager/node identities by ULID today. Does the registry need to gain auth awareness, or is auth fully orthogonal? Likely orthogonal in v1; revisit if the registry starts vending bootstrap data.
5. **Lab vs. deployment as the security boundary** — The current `lab_id` looks like the right tenant boundary for token `iss`/`aud`. Confirm with stakeholders before locking in the claim schema.
