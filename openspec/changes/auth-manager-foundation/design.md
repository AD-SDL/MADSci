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

### Decision 8: Single audience (`aud = lab_id`) for v1

All access tokens — for users, service accounts, and node identities alike — SHALL be issued with a single `aud` claim equal to the deployment's `lab_id`. Every manager verifies `aud == lab_id` during JWT validation.

**Why single aud for v1:** Simplest possible client and verification logic for the foundation. One token per principal, one refresh path, one cache entry. Aligns with the typical single-tenant lab deployment where every manager and node trusts every other manager and node within the same `lab_id` boundary. Avoids upfront-declaration ergonomic problems (especially for users, who interact with everything).

**Trade-off accepted:** A token leaked from any service can be replayed against every other service in the same lab. The mitigations are short access-token TTL (15 min) and the `jti` deny-list for incident response — same controls that bound any single-token compromise.

**Follow-on path (not in this change):** A future change SHALL add per-principal `aud` scoping — primarily for service accounts and node identities, where audiences are declared at registration time (`madsci auth node register --audiences workcell_manager,event_manager`). User tokens would likely remain broad. RFC 8693 token exchange is a possible further evolution if dynamic narrowing becomes desirable. This is captured in the follow-up issue list created in Task 15.4.

**Alternatives considered:**
- *Multi-audience array from day one*: rejected — requires every caller to declare intent upfront, complicates the AuthClient cache, and forces users (who hit everything) into either broad scoping anyway or per-target refresh. Better to layer this in once the foundation has settled.
- *Per-resource-server tokens (classic OAuth)*: rejected — too much token churn for a workflow execution that fans out across many managers.

### Decision 9: Pre-provisioned node identities for v1

NodeIdentity (and ServiceAccount) records SHALL be created by an operator action ahead of node startup. The operator runs `madsci auth node register --node-id <id> --workcell-id <wc>`; the Auth Manager returns the `client_id` + plaintext `client_secret` exactly once; the operator distributes the secret to the node host (typically via `.madsci/secrets/` mounted into the container or as an env var). At startup the node exchanges the secret for a JWT via the standard OAuth 2.0 client-credentials grant.

**Why pre-provisioned for v1:** Smallest delta from the existing static compose / config-file deployment model that real MADSci labs use today. No new endpoint, no node-side keypair generation, no enrollment-token bookkeeping. The NodeIdentity row exists before the node ever runs, which makes the trust model unambiguous and easy to audit.

**Trade-off accepted:** Operators have to manually shuffle a secret from the CLI output to the node host. At small node counts this is fine; it does not scale to dozens of ephemeral nodes or to autoscaled / CI environments. The on-disk secret is also long-lived until rotated.

**Follow-on path (not in this change):** A future change SHALL add an enrollment-token flow modeled on Kubernetes kubelet bootstrap / Tailscale auth keys / Nomad ACL bootstrap. Operators would create short-lived, optionally multi-use enrollment tokens scoped to a workcell with name-pattern constraints; nodes would self-generate a keypair, present the enrollment token to a `/enroll` endpoint, and persist their issued long-lived credentials locally. The NodeIdentity schema designed here is forward-compatible — a follow-on adds an `enrolled_via_token` field and the `/enroll` endpoint without restructuring existing tables. Captured in Task 15.4.

**Alternatives considered:**
- *Enrollment tokens from day one*: rejected — meaningful additional surface area (new endpoint, name-pattern enforcement, single-use accounting, node-side persistent credential store, key-binding semantics) that would dilute the foundation change. Value primarily shows at scale and in dynamic environments, neither of which is the typical MADSci lab today.
- *Trust-on-first-use with no operator action*: rejected — would require some other mechanism (mTLS, network position) to establish trust, all of which are larger projects than pre-provisioning.

### Decision 10: OwnershipInfo back-compat — accept caller-asserted values when auth is disabled

When `auth_enabled=False`, the existing behavior SHALL be preserved: `OwnershipInfo` continues to be sourced from caller-supplied request bodies and the `ownership_context()` machinery, with no validation against tokens. When `auth_enabled=True`, caller-supplied `OwnershipInfo` is accepted only when no contradicting JWT claim exists, and the middleware-derived (claims-sourced) values always win on conflict — with a structured warning logged on mismatch.

A deprecation warning SHALL be emitted on every successful caller-asserted `OwnershipInfo` write when `auth_enabled=False`, on a sampled basis (default once per process per minute per call-site, to avoid log floods). The warning text SHALL point operators at the migration guide.

**Removal timeline:** Caller-asserted `OwnershipInfo` SHALL be removed in the same MADSci release that removes the `auth_required=False` migration mode. This couples the two deprecations so deployments make a single jump rather than two.

**Why:** Hard-cutting this would break every existing script and notebook in the wild on day one. The deprecation/coupling lets operators migrate at their own pace while making the eventual end-state unambiguous.

**Trade-off accepted:** The grace period means we ship a release in which `OwnershipInfo` semantics differ depending on `auth_enabled`. This is documented in the operator guide.

### Decision 11: Registry is orthogonal to auth in v1

The existing identity registry (`enable_registry_resolution`, `MADSCI_REGISTRY_PATH`, `madsci.common.registry`) SHALL remain unchanged. It continues to resolve manager and node ULIDs to URLs without any auth awareness — a registry lookup is a directory operation, not an authentication operation.

Auth credentials (NodeIdentity / ServiceAccount records) live in the Auth Manager's PostgreSQL database; the registry continues to live in its JSON file or its own resolution path. The two subsystems share `manager_id` / `node_id` ULIDs as join keys but have no other coupling in v1.

**Why:** Conflating directory and identity concerns is a classic anti-pattern; keeping them separate lets each evolve independently. The registry's current concerns (URL resolution, ULID lookup) are not auth concerns. A future change MAY explore whether the registry should vend bootstrap material (e.g., the Auth Manager URL itself, JWKS bootstrap) but that is a separate design question.

**Trade-off accepted:** Operators have to keep registry entries and Auth Manager registrations consistent (e.g., when adding a new node, both `madsci registry add` and `madsci auth node register` are required). The CLI MAY offer a convenience that does both atomically; this is captured as an optional follow-on.

### Decision 12: Lab-scoped Auth Manager (`lab_id` is the tenant boundary)

The Auth Manager and the Lab Manager have a **1:1 relationship**. Each MADSci lab runs exactly one Auth Manager. `lab_id` is the security and tenancy boundary: `aud = lab_id` (per Decision 8) and `iss` is the URL of that lab's Auth Manager. Users, projects, service accounts, node identities, role grants, signing keys, and audit logs all live in that single Auth Manager's PostgreSQL database and are implicitly scoped to its `lab_id`. The schema is single-tenant — there is no `tenant_id` foreign key and no cross-lab queries.

**Why lab-scoped for v1:**
- Smallest delta from how MADSci is deployed today (one lab ≈ one deployment).
- Schema and operations stay single-tenant, eliminating an entire class of cross-tenant data-isolation bugs in a security-critical subsystem.
- Trust boundary is unambiguous: a token from lab A's Auth Manager has no semantic meaning in lab B until/unless an explicit federation mechanism is added.
- Bootstrap is clean — `madsci auth bootstrap` operates against a single lab.

**Cross-lab user identity is intentionally deferred to the upstream-IdP layer.** Researchers who work across labs will, in v1, hold multiple lab-scoped tokens — one per lab. The follow-on Globus/ORCID OIDC federation work resolves this at the right layer: each lab's Auth Manager OIDC-trusts a shared upstream IdP, so a researcher's external identity is one record but lab-local role grants and project membership remain lab-autonomous. This is the same pattern used by every modern federated scientific computing system (JupyterHub, Globus-aware HPC schedulers, etc.) and avoids forcing multi-tenant complexity into the foundation.

**Trade-offs accepted:**
- Orgs running N labs operate N Auth Managers (N PostgreSQL DBs to back up, N sets of signing keys to rotate). Acceptable given typical AD-SDL/RPL deployment scale.
- Cross-lab researchers manage multiple tokens until the upstream-IdP follow-on lands. Annoying but workable — and the upstream-IdP work is already on the roadmap.
- Cross-lab token validation (lab B trusting lab A's tokens directly) is not supported in v1. If two labs want to share resources, the path is via the shared upstream IdP, not via direct cross-issuer trust.

**Forward-compatibility:** Nothing in this decision precludes a later multi-tenant Auth Manager mode or direct cross-issuer trust. Both can be added in follow-on changes without breaking what v1 ships, because the schema is already keyed on globally-unique ULIDs and `iss`/`aud` are already explicit.

**Alternatives considered:**
- *Multi-tenant Auth Manager (one per organization, `tenant_id` on every row)*: rejected — adds isolation bugs to a security-critical foundation, and the cross-lab-user UX problem is better solved at the IdP layer anyway.
- *Workcell-scoped Auth Manager (sub-lab tenants)*: rejected — within a lab, isolation belongs at the Project layer (project membership), not at the auth tenancy layer.

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

_All open questions have been resolved into Decisions 8–12 above. Future questions surfaced during implementation will be tracked here or as separate follow-on changes._
