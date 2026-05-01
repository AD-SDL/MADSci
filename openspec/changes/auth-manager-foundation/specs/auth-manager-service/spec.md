## ADDED Requirements

### Requirement: Auth Manager package layout and base class

A new package `madsci_auth_manager` SHALL exist at `src/madsci_auth_manager/`. The server class SHALL inherit from `AbstractManagerBase[AuthManagerSettings]` and SHALL be importable as `madsci.auth_manager.AuthManager`. The settings class SHALL inherit from `MadsciBaseSettings` and use the `AUTH_` environment-variable prefix.

#### Scenario: Package follows the manager pattern
- **WHEN** the test suite imports `madsci.auth_manager`
- **THEN** the package SHALL expose `AuthManager`, `AuthManagerSettings`, and a server entry point usable from `madsci start manager auth`

#### Scenario: Settings respect prefixed alias system
- **WHEN** the operator sets `AUTH_SERVER_URL` and `AUTH_DATABASE_URL` environment variables
- **THEN** `AuthManagerSettings()` SHALL load these values into the `server_url` and `database_url` fields respectively

### Requirement: Default port allocation

The Auth Manager SHALL default to listening on port 8007 (the next port after Location Manager at 8006). Port allocation documentation in `CLAUDE.md` and the Configuration guide SHALL be updated to reflect this.

#### Scenario: Default port is 8007
- **WHEN** an `AuthManagerSettings()` is constructed without overriding `server_url`
- **THEN** the resolved URL SHALL bind to port 8007

### Requirement: PostgreSQL persistence via SQLAlchemyHandler

The Auth Manager SHALL persist all entities (users, projects, memberships, roles, role_permissions, service_accounts, node_identities, refresh_tokens, signing_keys, audit_log) in PostgreSQL using the existing `SQLAlchemyHandler` abstraction from `madsci.common.db_handlers`. Tests SHALL be runnable against the in-memory `SQLiteHandler` without Docker.

#### Scenario: In-memory handler injection for tests
- **WHEN** an `AuthManager` is constructed with a `SQLiteHandler` instance
- **THEN** all server endpoints SHALL function without a real PostgreSQL connection

#### Scenario: Schema migrations managed via Alembic
- **WHEN** the Auth Manager starts against a PostgreSQL database whose schema is older than the current code
- **THEN** it SHALL automatically run Alembic migrations to bring the schema current, after taking a backup via `PostgreSQLBackupTool`

### Requirement: Bootstrap flow

The Auth Manager SHALL provide a bootstrap CLI command `madsci auth bootstrap` that creates an initial admin user (prompting for username/password if not provided), generates the first signing keypair, and seeds the built-in role set.

#### Scenario: Bootstrap on an empty database
- **WHEN** an operator runs `madsci auth bootstrap --username admin` against an empty database
- **THEN** the system SHALL prompt for a password, create the `admin` user with the `admin` role, generate an RSA keypair and persist it, seed built-in roles, and emit the password to be stored only by the operator

#### Scenario: Bootstrap is idempotent and safe
- **WHEN** `madsci auth bootstrap` runs against an already-bootstrapped database
- **THEN** it SHALL detect existing state, take no destructive action, and report what already exists

### Requirement: Secret material storage and protection

The Auth Manager SHALL persist signing keys in the database with the private key material stored such that operator-supplied disk/database encryption protects it. The bootstrap command SHALL NOT print private key material to stdout. Service-account and node-identity bootstrap secrets returned to the operator SHALL be returned exactly once and never re-displayable.

#### Scenario: Secret returned only at issuance
- **WHEN** an operator registers a new service account or node identity
- **THEN** the bootstrap secret SHALL be returned exactly once in the CLI output, only the Argon2 hash SHALL be persisted, and any subsequent attempt to retrieve the original secret SHALL fail

### Requirement: Health and observability endpoints

The Auth Manager SHALL implement the standard `/health` and `/settings` endpoints provided by `AbstractManagerBase`, plus a `/health/keys` endpoint reporting the count of active signing keys and the time-to-rotation of the oldest. OpenTelemetry tracing SHALL be enabled per the manager pattern.

#### Scenario: Health endpoint reports key status
- **WHEN** a monitoring system calls `/health/keys`
- **THEN** the Auth Manager SHALL return HTTP 200 with `{ active_keys: <int>, oldest_key_age_seconds: <int>, signing_kid: <str> }`

### Requirement: CLI surface

The MADSci CLI SHALL gain an `auth` command group with at minimum the following subcommands: `bootstrap`, `user create`, `user deactivate`, `user grant <role> <project>`, `user revoke <role> <project>`, `project create`, `manager register <manager_id>`, `node register <node_id>`, `credentials rotate <client_id>`, `keys rotate`, `keys list`, `keys retire <kid>`.

#### Scenario: CLI commands route to the Auth Manager
- **WHEN** an operator runs any `madsci auth` subcommand
- **THEN** the CLI SHALL invoke the corresponding Auth Manager endpoint via `AuthClient` using admin credentials sourced from the operator's configured profile
