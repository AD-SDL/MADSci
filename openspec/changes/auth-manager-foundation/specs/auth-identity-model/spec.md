## ADDED Requirements

### Requirement: User entity

The system SHALL define a `User` entity representing an individual human principal of the lab. Users MUST have a globally unique ULID `user_id`, a unique `username`, an optional `email`, an `is_active` flag, an Argon2 `password_hash` field for local accounts, and creation/update timestamps.

#### Scenario: Create a local user with a password
- **WHEN** an admin invokes `madsci auth user create --username alice --password <secret>`
- **THEN** a User row is persisted with a freshly generated ULID, `is_active=True`, an Argon2id hash of the password, and the timestamps populated to the time of creation

#### Scenario: Reject duplicate usernames
- **WHEN** a request to create a user with an existing `username` is submitted
- **THEN** the Auth Manager SHALL return HTTP 409 Conflict and SHALL NOT create a duplicate row

#### Scenario: Deactivate a user
- **WHEN** an admin sets `is_active=False` on a user
- **THEN** subsequent password-grant token requests for that user SHALL fail with HTTP 401 and any active refresh tokens SHALL be revoked

### Requirement: Project entity and membership

The system SHALL define a `Project` entity (`project_id` ULID, `name`, `description`, `created_at`) and a `ProjectMembership` join entity linking `user_id` to `project_id` with one or more `role_id` grants scoped to that project.

#### Scenario: Add a user to a project with a role
- **WHEN** an admin grants user `alice` the `experimenter` role within project `proj_X`
- **THEN** a ProjectMembership row SHALL exist with `(user_id=alice, project_id=proj_X, role_id=experimenter)` and Alice's tokens SHALL include `proj_X` in their project-membership claims

#### Scenario: Remove a user from a project
- **WHEN** an admin revokes Alice's membership in `proj_X`
- **THEN** the ProjectMembership row SHALL be deleted and Alice's next-issued token SHALL NOT include `proj_X` in its claims

### Requirement: ServiceAccount entity for managers

The system SHALL define a `ServiceAccount` entity representing a non-human principal (a manager service). Each ServiceAccount MUST have a unique `client_id`, a hashed `client_secret`, a `manager_id` it represents, an `is_active` flag, and one or more `role_id` grants (typically global, not project-scoped).

#### Scenario: Register a new manager service account
- **WHEN** an operator runs `madsci auth manager register --manager-id event_manager_01`
- **THEN** the Auth Manager SHALL create a ServiceAccount with a generated `client_id`/`client_secret`, return the secret to the operator exactly once, and persist only the hash

#### Scenario: Service account authenticates via client credentials
- **WHEN** the manager submits its `client_id`/`client_secret` to the token endpoint with `grant_type=client_credentials`
- **THEN** the Auth Manager SHALL issue a JWT whose `sub` references the ServiceAccount and whose claims include the granted roles

### Requirement: NodeIdentity entity

The system SHALL define a `NodeIdentity` entity representing a node principal. Each NodeIdentity MUST have a unique `client_id`, a hashed `client_secret`, the `node_id` ULID it represents, an optional `workcell_id` scope, an `is_active` flag, and (forward-compat) an optional `mtls_cert_fingerprint` field reserved for the future mTLS follow-on.

#### Scenario: Register a node
- **WHEN** an operator runs `madsci auth node register --node-id arm_01 --workcell-id wc_main`
- **THEN** a NodeIdentity row SHALL be created scoped to `wc_main` and the bootstrap secret SHALL be returned exactly once

#### Scenario: Node-issued tokens carry node and workcell claims
- **WHEN** a NodeIdentity exchanges its credentials for a JWT
- **THEN** the issued token's claims SHALL include `node_id` and `workcell_id` so downstream managers can bind these into `OwnershipInfo`

### Requirement: Node and service-account identities are pre-provisioned

In this foundation change, NodeIdentity and ServiceAccount records SHALL be created exclusively by an authenticated operator action (CLI or API call by an admin principal) BEFORE the corresponding node or manager process starts. The Auth Manager SHALL NOT expose any unauthenticated registration or self-enrollment endpoint.

#### Scenario: Self-registration is not supported in v1
- **WHEN** a node process attempts to create its own NodeIdentity record without admin credentials
- **THEN** the request SHALL be rejected with HTTP 401 or 403 and no NodeIdentity SHALL be created

#### Scenario: NodeIdentity schema is forward-compatible with enrollment tokens
- **WHEN** the NodeIdentity table is created
- **THEN** its schema SHALL be designed so a future migration can add an `enrolled_via_token` field and an associated `enrollment_tokens` table without restructuring existing columns or breaking foreign keys

### Requirement: Role and Permission entities

The system SHALL define a `Role` entity (`role_id`, `name`, `description`) and a many-to-many `RolePermission` mapping linking roles to permission strings drawn from a documented namespace (e.g., `experiment.write`, `node.execute_action`, `resource.read`).

#### Scenario: Define a role with permissions
- **WHEN** an admin creates role `experimenter` with permissions `{experiment.write, experiment.read, workflow.submit}`
- **THEN** the role and its permission grants SHALL be persisted and any user/service-account/node granted this role SHALL receive these permissions in their token claims

#### Scenario: Built-in roles seeded at bootstrap
- **WHEN** `madsci auth bootstrap` runs against an empty database
- **THEN** the system SHALL seed at minimum these built-in roles: `admin` (all permissions), `experimenter` (experiment + workflow + resource read/write), `operator` (workcell + node operation), and `read_only` (read of all observable state)

### Requirement: Audit log

The system SHALL persist an append-only audit log row for each security-relevant event: user create/deactivate/password-change, role grant/revoke, token issue/refresh/revoke, service-account/node register/rotate, and bootstrap.

#### Scenario: Token issuance is audited
- **WHEN** a token is issued via any grant
- **THEN** an audit log row SHALL be written including `timestamp`, `principal_id`, `grant_type`, `token_jti`, and the source IP address

#### Scenario: Audit log is append-only
- **WHEN** any actor (including admin) attempts to modify or delete an audit log row
- **THEN** the operation SHALL fail and SHALL itself produce a new audit log entry recording the attempt

### Requirement: Local audit-log fallback at consuming managers

When a consuming manager cannot deliver an authentication-related audit event to the Auth Manager (e.g., the Auth Manager is unreachable, the network is partitioned, or the request hit a 5xx), the manager SHALL persist the event to a local append-only audit log on disk before returning the request response. The local audit log SHALL be retried for delivery to the Auth Manager on a configurable interval (default 60 seconds) and SHALL only be removed locally after successful delivery is confirmed. Loss of an authentication-related audit event SHALL never be silent.

#### Scenario: Auth Manager unreachable does not silently drop audit events
- **GIVEN** a consuming manager has rejected a request with HTTP 401 and the Auth Manager is unreachable
- **WHEN** the manager attempts to write the audit event
- **THEN** the event SHALL be persisted to the local fallback audit log file before the manager finishes handling the request

#### Scenario: Local audit log drains on Auth Manager recovery
- **GIVEN** locally-persisted audit events exist
- **WHEN** the Auth Manager becomes reachable again
- **THEN** the manager SHALL deliver the queued events in original order and SHALL only remove each event from the local log after the Auth Manager confirms persistence

#### Scenario: Local audit log is bounded
- **WHEN** the local fallback audit log exceeds a configurable maximum size (default 100 MB)
- **THEN** the manager SHALL emit a structured warning event AND SHALL continue persisting new events (rotating the oldest segment), so that loss is loud and auditable rather than silent
