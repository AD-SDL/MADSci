# Changelog

All notable changes to the MADSci framework are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Removed
- **`madsci new workcell` subcommand**: The workcell template generated an orphaned YAML format that didn't correspond to any Pydantic model. Workcell configuration is handled by `WorkcellManagerSettings` via `settings.yaml`.
- **`LabClient.get_definition()`**: The Lab Manager no longer serves a `/definition` endpoint. Use `get_lab_context()` or `get_lab_health()` instead.
- **`WORKCELL` template category**: Removed from `TemplateCategory` enum.
- **`NodeLocationTemplateDefinition`**: Replaced by `NodeIntrinsicLocationDefinition` for declaring node-intrinsic locations. Location templates are now defined as `LocationTemplate` objects (via lab config file or API) rather than on node classes.
- **`seed_locations_file` setting**: Replaced by `lab_config_file` on `LocationManagerSettings`. The new `LabLocationConfig` format supports representation templates, location templates, training entries, and locations in a single reconcilable file.

### Deprecated
- **`LabManagerDefinition`**: Now emits `MadsciDeprecationWarning` on instantiation (v0.7.0 removal). Use `LabManagerSettings` for configuration.

### Added
- **`target_model` field on `TemplateManifest`**: Templates that generate YAML/JSON config can now declare which Pydantic model the output should validate against. Automated tests verify template output matches the declared model.
- **Settings file validation in `madsci validate`**: The validate command now supports `settings.yaml` and `*.settings.yaml` files, validating against per-manager settings classes (Lab, Event, Experiment, Resource, Data, Workcell, Location).
- **Pydantic-first data modeling guidance**: Added to CLAUDE.md, AGENTS.md, and agent skills to codify the rule that every YAML/JSON config format must have a corresponding Pydantic model.

#### Layered Location Ownership Model
- **`NodeIntrinsicLocationDefinition`**: Nodes declare locations intrinsic to their hardware via the `intrinsic_locations` ClassVar. Location names are auto-prefixed with `{node_name}.` for uniqueness (e.g., `deck_1` becomes `liquidhandler_1.deck_1`).
- **`LocationManagement` enum**: Every location now tracks whether it is managed by a node (`NODE`) or by the lab configuration (`LAB`) via the `managed_by` field on `Location`.
- **`owner` field on `Location`**: `OwnershipInfo` provenance tracking. Node-managed locations automatically set `owner.node_id`.
- **`POST /location/init` endpoint**: Idempotent get-or-create for location registration, used by nodes during startup.
- **`GET /locations?managed_by=node|lab` filtering**: Query locations by management type.
- **`GET /reconciliation/status` endpoint**: Returns last reconciliation timestamp, results, and configuration.
- **`LabLocationConfig`**: Reconcilable lab config file format (`locations.yaml`) with `representation_templates`, `location_templates`, `training`, and `locations` sections. Replaces the old `seed_locations_file` mechanism.
- **`RepresentationTrainingEntry`**: Teaches a node how to access locations it does not own (e.g., robot arm coordinates for a liquid handler deck slot). Defined in the `training` section of the lab config file.
- **`lab_config_file` setting**: `LocationManagerSettings` field (default: `locations.yaml`) for the lab config file path, discovered via walk-up search. Replaces `seed_locations_file`.
- **Health endpoint enrichment**: `LocationManagerHealth` now includes `num_node_managed_locations`, `num_lab_managed_locations`, and `last_reconciliation_at` fields.
- **`intrinsic_location_handler()` on `AbstractNode`**: Lifecycle method that registers intrinsic locations with the Location Manager at startup, after `template_handler()` and before `startup_handler()`.
- **`NodeInfo.intrinsic_locations` field**: Exposes a node's declared intrinsic locations through its `/info` endpoint.
- **Location Manager schema upgrade 2.0.0 to 3.0.0**: Adds `managed_by` (default `"lab"`) and `owner` (default `null`) fields to all existing location documents, plus a `managed_by_idx` index.

#### CLI/TUI Buildout
- **`madsci add` command** with 8 subcommands for adding components to existing module projects (docs, drivers, notebooks, gitignore, compose, dev_tools, agent_config, all)
- **8 addon templates** for optional project components: `addon/docs`, `addon/drivers`, `addon/notebooks`, `addon/gitignore`, `addon/compose`, `addon/dev_tools`, `addon/agent_config`, `addon/all`
- **8 new CLI command groups** for direct manager interaction, each with short aliases:
  - `madsci workflow` (`wf`): list, show, submit, pause, resume, cancel, retry, resubmit
  - `madsci resource` (`res`): list, get, create, delete, restore, tree, lock, unlock, quantity, template, history
  - `madsci location` (`loc`): list, get, create, create-from-template, delete, resources, attach, detach, set-repr, remove-repr, transfer-graph, plan-transfer, export, import, template, rep-template
  - `madsci node` (`nd`): list, info, status, state, log, admin, action, action-result, action-history, config, set-config, add, shell
  - `madsci experiment` (`exp`): list, get, start, run, pause, continue, cancel, end
  - `madsci campaign` (`camp`): create, get
  - `madsci data` (`dt`): list, get, metadata, submit, query
  - `madsci events` (`ev`): query, get, archive, purge, backup
- **4 new TUI main screens**: experiments, resources, locations, data browser — all with search/filter, detail panels, and action bars
- **5 TUI detail/modal screens**: resource tree, transfer graph, workflow detail, step detail, action executor
- **TUI node enhancements**: admin command panel and interactive action executor
- **TUI workflow enhancements**: retry, resubmit, step details, and filtering
- **Shared CLI/TUI utility layer**: `cli_utils.py` (formatting, health checks, output helpers) and reusable TUI widget library (7 widgets and screen mixins)
- **httpx client migration**: All 8 service clients migrated from `requests` to `httpx` with `DualModeClientMixin` for sync/async support, configurable retry transports, and rate-limit tracking via `httpx_factory.py`
- **ResourceClient async methods**: 16 new async methods for TUI integration
- **LocationClient async methods**: Missing async methods added for TUI integration

### Changed
- **`madsci validate` docstring**: Updated to reflect support for settings files alongside definitions and workflows.
- **CLI commands refactored** to use shared utility layer for consistent output formatting and error handling
- **TUI screens migrated** to shared widget library for consistent styling and behavior
- **Example lab location management**: Inline `location_locations` definitions in `settings.yaml` replaced by a standalone `locations.yaml` lab config file using `LabLocationConfig` format. Node-intrinsic locations (liquid handler deck slots) are now auto-created by nodes on startup. Lab-managed locations (storage rack, plate carriage) and training entries (robot arm coordinates for LH deck slots) are defined in `locations.yaml`.
- **Location Manager reconciliation**: Now processes the lab config file (`LabLocationConfig`) on each cycle, syncing representation templates, location templates, locations, and training entries with the live database.

### Fixed
- TUI UX improvements: scrollable layouts, clickable ActionBar, screen discoverability
- Dashboard scroll behavior and full ULID ID display
- Transfer graph names, delete confirmation dialog, inventory button label
- Double-slash URL bug in node client health checks
- httpx migration fixes: stale `requests` imports, config attribute access, response closing in retry transports, async health checks, broken sync `.close()` call

## [0.8.0] - 2026-03-31

### Added

#### Node Location Template System (PR #228, #258)
- `template_handler()` lifecycle method on `AbstractNode` for declarative registration of resource templates, location representation templates, and location templates at node startup
- `location_representation_templates` and `location_templates` class variables on `AbstractNode` for declarative template definitions
- `NodeInfo.location_templates` field exposing a node's registered location templates through its info endpoint
- Location Templates panel on the Squid Dashboard with schema-aware forms for creating locations from templates
- Resource Templates panel on the Squid Dashboard Resources tab
- Database auto-initialization for document database collections not yet tracked by the migration system

#### Agent Skills (PR #242)
- Four bundled agent skills (`madsci-cli`, `madsci-nodes`, `madsci-managers`, `madsci-experiments`) providing AI coding agents with MADSci domain knowledge
- Skills are automatically copied into generated projects via `madsci new` and `madsci init`

#### Dashboard Workflow and Node Modal Redesign (PR #259)
- Redesigned workflow modal with tabbed layout (Overview, Steps, Results tabs) and step indicators
- Workflow retry and resubmit UX with confirmation dialogs and snackbar notifications
- Redesigned node modal with tabbed layout (Overview, Info, Actions tabs)
- `resubmit_workflow` endpoint on workcell manager and corresponding client method

#### Experiment Ownership Propagation (PR #260)
- Experiment ownership context (experiment_id, campaign_id, user) is now automatically propagated to workflows started within `manage_experiment()`

#### FOSS Infrastructure Migration (Issue #212)
- New FOSS migration tool (`madsci.common.foss_migration`) for automated data migration from proprietary infrastructure (MongoDB, Redis, MinIO) to FOSS alternatives (FerretDB, Valkey, SeaweedFS)
  - `FossMigrationTool` orchestrator with 20+ methods covering prerequisite checks, Docker lifecycle management, database-specific migrations, and post-migration verification
  - `FossMigrationSettings` with environment variable support and customizable compose file/service names
  - `FossMigrationStepResult` and `FossMigrationReport` result models for structured migration reporting
- New `madsci migrate foss` CLI command with `--dry-run`/`--apply` modes, per-step execution (`--step`), `--skip-backup`, `--skip-docker`, URL overrides, and Rich table output
- Docker Compose migration overlay (`compose.migration.yaml`) for running old containers on alternate ports during migration (MongoDB:27018, PostgreSQL:5433, Redis:6380, MinIO:9002)
- Automated Location Manager data migration from v0.7.x Redis to FerretDB document database as part of the FOSS migration pipeline — auto-discovers manager IDs, reads location data (resource attachments, node representations) from old Redis, and writes to FerretDB via `LocationMigrator`
- Comprehensive FOSS migration guide (`docs/guides/foss_migration.md`) with prerequisites, quick start, Location Manager migration, troubleshooting, and data directory reference
- FOSS migration test suites: CLI tests (129 lines) and tool unit tests (536 lines)

### Changed

#### Location Manager Dual-Handler Architecture (PR #228)
- Location Manager migrated from Redis-only to dual-handler architecture (document database + cache)
- Location data persisted in document database with cache-backed fast reads

#### Dashboard UX Improvements (PRs #255, #257)
- Copyable workflow step output now uses `js-yaml` for YAML formatting with scoped toggle per action
- JSON renderer for workflow steps has a depth limit to prevent browser freezes on deeply nested data
- Action argument values in the node modal are now initialized from their declared defaults

#### Default Infrastructure: FOSS Alternatives
- **MongoDB → FerretDB v2**: Default document database switched to FerretDB (MongoDB wire protocol, backed by PostgreSQL with DocumentDB extension); Python `pymongo` client unchanged
- **Redis → Valkey 8**: Default key-value store switched to Valkey (drop-in API-compatible); Python `redis` client unchanged
- **MinIO → SeaweedFS 4.17**: Default object storage switched to SeaweedFS (S3-compatible); Python `minio` SDK unchanged
- **PostgreSQL split**: Two separate PostgreSQL instances — `madsci_postgres` (port 5432, `postgres-documentdb-dev:17-ferretdb` for FerretDB) and `madsci_postgres_resources` (port 5434, `postgres:17` for Resource Manager) — replacing the single shared instance

#### FOSS Terminology Audit
- **BREAKING**: `DocumentDBBackupSettings` env prefix changed from `MONGODB_` to `DOCUMENT_DB_` (e.g., `MONGODB_BACKUP_DIR` → `DOCUMENT_DB_BACKUP_DIR`)
- **BREAKING**: `DocumentDBMigrationSettings` env prefix changed from `MONGODB_MIGRATION_` to `DOCUMENT_DB_MIGRATION_` (e.g., `MONGODB_MIGRATION_DATABASE` → `DOCUMENT_DB_MIGRATION_DATABASE`)
- **BREAKING**: Settings fields `redis_host`, `redis_port`, `redis_password` renamed to `cache_host`, `cache_port`, `cache_password` on `WorkcellManagerSettings` and `LocationManagerSettings` (old names accepted via `validation_alias` for backward compatibility)
- **BREAKING**: Health model fields `redis_connected` renamed to `cache_connected` on `WorkcellManagerHealth` and `LocationManagerHealth`
- **BREAKING**: Docker types field `REDIS_PORT` renamed to `CACHE_PORT` (old name accepted via `validation_alias`)
- Default backup directory for document database migrations changed from `.madsci/backups/mongodb` to `.madsci/backups/document_db`
- Backup metadata `backup_type` value changed from `"mongodb"` to `"document_db"` for document database backups
- Comprehensive terminology updates across all comments, docstrings, schema descriptions, and documentation to use vendor-neutral terms ("document database" instead of "MongoDB", "cache" instead of "Redis")
- Deleted stale auto-generated API doc files referencing old module names (`mongo_cli.md`, `mongodb_backup.md`, `mongo_handler.md`, etc.)
- Test directory renamed: `test_mongodb_backup_tools/` → `test_document_db_backup_tools/`
- Manual test file renamed: `manual_test_minio.py` → `manual_test_object_storage.py`

#### Vendor-Neutral Renames
- Handler files: `mongo_handler.py` → `document_storage_handler.py`, `minio_handler.py` → `object_storage_handler.py`
- Handler classes: `PyMongoHandler` → `PyDocumentStorageHandler`, `InMemoryMongoHandler` → `InMemoryDocumentStorageHandler`, `RealMinioHandler` → `RealObjectStorageHandler`, `InMemoryMinioHandler` → `InMemoryObjectStorageHandler`
- Backup tools: `mongodb_backup.py` → `document_db_backup.py`, `mongo_cli.py` → `document_db_cli.py`, `MongoDBBackupTool` → `DocumentDBBackupTool`, `MongoDBBackupSettings` → `DocumentDBBackupSettings`
- Migration tools: `mongodb_migration_tool.py` → `document_db_migration_tool.py`, `mongodb_version_checker.py` → `document_db_version_checker.py`
- Helper function: `create_minio_client()` → `create_object_storage_client()` (with new `_normalise_endpoint()` for URL scheme stripping)
- Manager constructor parameters: `mongo_handler` → `document_handler`, `minio_handler` → `object_storage_handler`
- Settings fields: `mongo_db_url` → `document_db_url` across all managers (backward-compatible via `AliasChoices` validation aliases)
- Docker types: `MONGODB_PORT` → `DOCUMENT_DB_PORT`, `MINIO_PORT` → `OBJECT_STORAGE_PORT` (8333), `MINIO_CONSOLE_PORT` → `OBJECT_STORAGE_CONSOLE_PORT` (9333)
- CLI entry point: `madsci-mongodb-backup` → `madsci-document-db-backup`
- Backup settings files: now check for both `document_db_backup.*` and legacy `mongodb_backup.*` filenames

#### Configuration and Port Changes
- Default object storage ports changed from MinIO conventions (9000/9001) to SeaweedFS defaults (8333/9333)
- Resource Manager PostgreSQL moved to port 5434 (FerretDB backend occupies 5432)
- Default `POSTGRES_DB` changed from `resources` to `postgres` (FerretDB requirement)
- SeaweedFS S3 credentials configured via `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` environment variables
- New `public_endpoint` field on `ObjectStorageSettings` for customizable public-facing URLs (replaces hardcoded port rewriting)

#### Templates
- Lab templates (`standard`, `distributed`) updated: service names (`mongodb` → `ferretdb`, `redis` → `valkey`), environment variables, and dependencies aligned with FOSS stack

#### Documentation
- Operator guides updated for FOSS stack: backup/recovery, troubleshooting, updates/maintenance
- Manager READMEs updated with FerretDB/Valkey/SeaweedFS references and new handler names
- Tutorials updated with new service names, ports, and compose configuration
- `madsci_common` README updated with new backup tool class names

### Fixed

#### Dashboard and UI Fixes (PRs #255, #256, #257, #259)
- Fixed dashboard freeze caused by `@vue:updated` event handler creating infinite update loops; replaced with `@update:modelValue`
- Typed action endpoints now return a failed `ActionResult` instead of HTTP 500 when actions raise exceptions
- Action argument checkbox and input values in the node modal now correctly initialized from their declared defaults
- Workflow steps that error before execution now show failed status instead of remaining pending

#### Experiment Ownership (PR #260)
- Restricted ownership context overrides to experiment-level fields only (`experiment_id`, `campaign_id`, `user`), preventing unintended overwrites of workflow-level ownership

#### Template Import Fixes
- Fixed `RestNodeConfig` import in all 6 module templates (was importing from `madsci.node_module` which does not export it; now imports from `madsci.common.types.node_types`)
- Fixed `SquidServer`/`SquidSettings` imports in all 3 lab templates (classes do not exist; replaced with `LabManager` from `madsci.squid.lab_server` and `LabManagerSettings` from `madsci.common.types.lab_types`)

#### FOSS Migration Location Data Loss
- Fixed FOSS migration tool silently skipping Location Manager data stored in Redis, treating it as ephemeral; v0.7.x Location Manager stores primary location data (resource attachments, node representations, transfer state) in Redis, which is now automatically migrated to the document database during `madsci migrate foss --apply`

#### Documentation URL Fixes
- Fixed broken GitHub Pages documentation URLs in CLI output and generated project files

#### CLI Scaffolding Fixes (`madsci new`)
- Fixed `--template` argument being ignored in `madsci new module` (template selection prompt was always shown even when `--template` was explicitly provided)
- Fixed default module name `my_module` creating a `my_module_module` directory; default changed to `my_device`
- Fixed agent skills being placed in the current working directory instead of inside the generated project directory (e.g., `my_device_module/.agents/` instead of `./.agents/`)
- Fixed next-steps output using hardcoded fallback names (e.g., `your_module_module`) instead of the actual names entered during interactive prompts; `generate_from_template` now returns the `GeneratedProject` result
- Fixed documentation link in `madsci new module` pointing to non-existent URL

### Removed
- `workcell_manager.compose.yaml` (redundant compose file)
- MongoDB data volume from `compose.yaml` (FerretDB uses PostgreSQL backend)
- Hardcoded MinIO console port rewriting logic in `object_storage_helpers.py` (replaced by configurable `public_endpoint`)

## [0.7.1] - 2026-03-10

### Added

#### Database Handler Abstractions
- New `madsci.common.db_handlers` package with abstract base classes (`DocumentStorageHandler`, `CacheHandler`, `PostgresHandler`, `ObjectStorageHandler`) and both real and in-memory implementations
- Real implementations: `PyMongoHandler`, `PyCacheHandler`, `SQLAlchemyHandler`, `RealObjectStorageHandler`
- In-memory implementations: `InMemoryDocumentStorageHandler`, `InMemoryCacheHandler`, `SQLiteHandler`, `InMemoryObjectStorageHandler`
- All 6 database-backed managers now accept optional handler constructor parameters (`document_handler`, `object_storage_handler`, `cache_handler`, `postgres_handler`), enabling dependency injection for testing
- `LocalRunner` updated to use handler abstractions instead of raw in-memory clients
- `InMemoryCollection` gained projection support, `replace_one()`, `client` property, and `list_collection_names()`

#### Node Registry Resolution
- Nodes now resolve stable IDs from the ID Registry at startup, matching the manager pattern
- Added `enable_registry_resolution`, `registry_lock_timeout`, and `lab_url` fields to `NodeConfig`
- `AbstractNode.__init__()` calls `IdentityResolver.resolve_with_info()` to look up or create a stable `node_id`
- `atexit` handler releases the registry lock on node shutdown for graceful handoff
- Nodes that fail registry resolution fall back to a generated ULID (non-fatal) unless lock contention exhausts the retry window (fatal `RegistryLockError`)

#### Node Lifecycle Management
- `AbstractNode.close()` method for explicit registry lock cleanup, recommended for notebook users who reassign node variables
- `AbstractNode.__del__()` and `AbstractManagerBase.__del__()` for GC-based identity release as a fallback

### Changed

#### EventClient Retry Removal
- Removed the async retry queue from `EventClient` (background thread, `_event_buffer`, `_retrying`, `_shutdown` state, OTEL buffer-size gauge and retry counter metrics)
- Event delivery is now synchronous and fire-once; callers should handle failures explicitly
- Added `madsci.eventclient.send_failures` OTEL counter and upgraded failure logging from `warning` to `error` with structured kwargs (`event_type`, `event_id`)

#### DataManager Object Storage Handler Consolidation
- All object storage operations now routed through `ObjectStorageHandler` abstraction; removed direct `self.minio_client` usage
- `_setup_object_storage()` wraps legacy `Minio` clients in `RealObjectStorageHandler` (same pattern as other managers wrapping raw connections)

#### Legacy Constructor Parameter Deprecation
- Legacy database connection parameters (`db_connection`, `db_client`, `redis_connection`, `mongo_connection`) now emit `DeprecationWarning` across all 6 managers and 2 state handlers

#### OpenTelemetry Logging Migration
- Migrated from deprecated `opentelemetry.sdk._logs.LoggingHandler` to `LoggingInstrumentor` from the `opentelemetry-instrumentation-logging` package
- Added `opentelemetry-instrumentation-logging` as a dependency of `madsci_common`
- Eliminates 44+ deprecation warnings from the OTEL SDK

#### Test Infrastructure
- Isolated test suite from shared registry via root `conftest.py` that patches `enable_registry_resolution` defaults to `False` and redirects `MADSCI_REGISTRY_PATH` to a temp file
- Replaced `nbconvert` with `papermill` for notebook validation; CI workflow renamed from `e2e_tests` to `validate_notebooks`
- Testcontainer fixtures now skip gracefully (`pytest.skip()`) when Docker containers are unavailable instead of hard-failing
- Added `PortWaitStrategy` to fix testcontainer host port-forwarding race condition on macOS/Rancher Desktop
- Removed `pytest-mock-resources` dependency; all tests use in-memory database handlers (no Docker required for unit/integration tests)

### Fixed

#### Weakref atexit Handlers
- Manager and node `atexit` handlers now use `weakref.ref` to avoid preventing GC of discarded instances (e.g. in notebook scenarios)
- Added `_atexit_registered` guard to prevent accumulating duplicate handlers on repeated calls

#### LoggingInstrumentor Double-Instrumentation Guard
- `configure_otel()` now checks `is_instrumented_by_opentelemetry` before calling `LoggingInstrumentor().instrument()`, preventing duplicate instrumentation when called multiple times (e.g. in test suites)

#### EventManager Lazy pymongo Imports
- Moved top-level `import pymongo` and `from pymongo import errors` behind `TYPE_CHECKING` guard and into methods, allowing the module to be imported without pymongo installed (in-memory-only usage)

#### InMemoryDocumentStorageHandler `_client` Safety
- `InMemoryDocumentStorageHandler.__init__` now sets `self._client = None` when an external `database` is provided, preventing `AttributeError` on `_client` access

#### Handler ABC Return Type Annotations
- Improved return type annotations on handler ABC methods: `DocumentStorageHandler.get_collection() -> Collection | Any`, `CacheHandler.create_dict() -> MutableMapping`, `CacheHandler.create_lock() -> ContextManager`, `PostgresHandler.get_engine() -> Engine | Any`

#### Manager Registry Lock Retry + Shutdown Release
- `AbstractManagerBase._resolve_identity_from_registry()` now retries lock acquisition for `registry_lock_timeout` seconds (default 60s) before raising, surviving ungraceful container restarts where the previous lock hasn't expired yet
- Added `registry_lock_timeout` field to `ManagerSettings` (default 60.0s, should be at least 2x the lock TTL of 30s)
- `RegistryLockError` is now fatal (re-raised) — managers cannot start without a stable identity
- `atexit.register(self.release_identity)` ensures the registry lock is released on process exit
- `IdentityResolver.resolve()` and `resolve_with_info()` now accept a `retry_timeout` parameter, passed through to `LocalRegistryManager.resolve()`
- `LocalRegistryManager.resolve()` implements retry loop: on `RegistryLockError`, retries every 2s until `retry_timeout` elapses

#### Other Fixes
- Fixed timezone-naive datetime comparison bug in `ResourceInterface` lock checks
- Fixed `DatabaseVersionChecker` to only create `SchemaVersionTable` (not all tables) during version checks

## [0.7.0] - 2026-03-04

### Added

#### `.madsci/` Sentry Directory
- Canonical `madsci.common.sentry` module for all `.madsci/` directory path resolution
- Walk-up resolution: `.madsci/` sentinel -> `.git/` boundary -> `~/.madsci/` fallback
- `madsci init` scaffolds `.madsci/` with standard subdirs and `registry.json`
- `.git/` now acts as a walk-up boundary for settings file discovery

#### Settings Directory with Walk-Up Discovery
- `_settings_dir` keyword argument on all `MadsciBaseSettings` subclasses for overriding the walk-up starting directory
- `MADSCI_SETTINGS_DIR` environment variable for overriding the walk-up starting directory
- `--settings-dir` CLI option on `madsci start`, `madsci start manager`, `madsci start node`, and `madsci config export`
- Walk-up resolves each filename independently: shared `settings.yaml` in a parent dir coexists with `node.settings.yaml` in a child dir
- Walk-up discovery is always active from CWD by default; `_settings_dir` and `MADSCI_SETTINGS_DIR` override the starting directory for walk-up, not whether walk-up is used

#### CLI (17 commands)
- `madsci init` - Interactive lab initialization wizard
- `madsci new` - Component scaffolding from templates (module, interface, node, experiment, workflow, workcell, lab subcommands)
- `madsci start` - Start lab services (Docker Compose or local mode)
  - `madsci start manager <name>` - Start a single manager as a subprocess
  - `madsci start node <path>` - Start a node module as a subprocess
  - `--wait/--no-wait` flag for health polling after detached start
- `madsci stop` - Stop lab services
  - `madsci stop manager <name>` - Stop a background manager process
  - `madsci stop node <name>` - Stop a background node process
- `madsci status` - Service health checking with `--watch` and `--json` support
- `madsci doctor` - Environment diagnostic checks (python, docker, ports)
- `madsci logs` - Event log viewing with `--follow`, `--level`, `--grep`, `--since` filters
- `madsci run` - Workflow and experiment execution
- `madsci validate` - Configuration and definition file validation
- `madsci config` - Configuration management (export, create)
- `madsci backup` - Database backup creation (PostgreSQL and document database)
- `madsci registry` - Service registry management
- `madsci migrate` - Database migration tooling
- `madsci tui` - Interactive terminal user interface
- `madsci completion` - Shell completion generation (bash, zsh, fish)
- `madsci commands` - Command listing
- `madsci version` - Version display
- Command aliases: `n`, `s`, `l`, `doc`, `val`, `ui`, `cmd`, `cfg`
- Lazy command loading for fast CLI startup

#### Templates (26 templates)
- 6 module templates: basic, device, instrument, liquid_handler, camera, robot_arm
- 4 interface templates: fake, real, sim, mock
- 1 node template: basic
- 4 experiment templates: script, notebook, tui, node
- 2 workflow templates: basic, multi_step
- 1 workcell template: basic
- 3 lab templates: minimal, standard, distributed
- 5 communication templates: serial, socket, rest, sdk, modbus
- Template engine with Jinja2, parameter validation, conditional files, and post-generation hooks
- Template registry with bundled, user, and remote template sources

#### TUI (Terminal User Interface)
- Dashboard screen with service overview and quick actions
- Status screen with detailed service health and auto-refresh
- Logs screen with filterable log viewer
- Nodes screen with node status and management
- Workflows screen with workflow monitoring and control
- CSS theming with light/dark mode support
- Trogon integration for CLI-to-TUI command exploration

#### Local Mode
- `madsci start --mode=local` runs all managers in-process without Docker
- In-memory drop-in backends for document database and Valkey operations; SQLite drop-in for PostgreSQL (Resource Manager)
- Local data storage for development and testing without external database dependencies

#### Configuration Management
- `madsci config export` for exporting configuration to YAML with secret redaction
- `madsci config create` for generating configuration files from defaults
- Secret classification with `json_schema_extra={"secret": True}`
- `model_dump_safe()` method on MadsciBaseModel and MadsciBaseSettings for secret redaction
- Explicit configuration management (no auto-writing of config files)

#### Experiment Application
- `ExperimentBase` propagates lab context URLs to instance attributes for robust client creation across async boundaries and Jupyter cells
- `ExperimentScript` for run-once experiment scripts
- `ExperimentNotebook` for Jupyter-friendly experiments with cell-based execution
- `ExperimentTUI` thread-safe pause/cancel controls using `threading.Event` for safe cross-thread state management
- `ExperimentNode` REST node modality for workcell-managed experiment execution
- Example experiments: `example_experiment.py` (ExperimentScript) and `example_experiment_tui.py` (ExperimentTUI) in `examples/`

#### Node Module Framework
- `NodeInfo.from_config()` for creating node info from configuration
- Migration tools for database schema management

#### Context and Ownership Systems
- `MadsciContext` settings class replacing `MadsciCLIConfig` for unified server URL configuration
- `madsci_context()` context manager for propagating server URL configuration across components
- `GlobalMadsciContext` singleton for application-wide server URL configuration
- `@with_madsci_context` and `@madsci_context_class` decorators for function and class-level context
- `madsci.common.ownership` module for tracking ownership metadata (user, experiment, workflow, node)
- `ownership_context()` context manager for hierarchical ownership propagation
- `@with_ownership` and `@ownership_class` decorators for function and class-level ownership context

#### Registry Subsystem
- `IdentityResolver` for resolving component names to stable ULIDs (local registry -> lab registry -> generate new)
- `LocalRegistryManager` with walk-up `.madsci/` discovery for file-based identity persistence
- `LockManager` with heartbeat-based stale lock detection for process-level coordination

#### Event Manager Analytics and Retention
- Event archiving via `/events/archive` endpoint (by event IDs or date cutoff)
- Document database TTL index for automatic hard-deletion of archived events
- Background retention task for periodic event archiving
- `UtilizationAnalyzer` for session-based system and node utilization analysis
- `TimeSeriesAnalyzer` for timezone-aware time-series utilization reports (daily, hourly, weekly)
- `CSVExporter` for exporting utilization, user, and session reports to CSV

#### Workflow Admin Commands
- `pause_workflow()` and `cancel_workflow()` workflow engine utilities
- `AdminCommands` enum expanded with PAUSE, RESUME, CANCEL, LOCK, UNLOCK
- Workflow cancellation retries until reaching a cancellable node or timeout
- Retry workflow from last failed step

#### Testing
- 2600+ automated tests
- 150+ template validation tests
- CLI tests using Click's CliRunner
- E2E test harness with tutorial validation
- YAML-driven `E2ETestRunner` framework in `madsci.common.testing` with validator registry and conditional step execution

#### Observability
- OpenTelemetry integration for distributed tracing, metrics, and log correlation
- `structlog` integration for per-instance structured logging in EventClient
- Structured logging with hierarchical context propagation
- `event_client_context()` and `get_event_client()` for context management
- Per-manager OTEL configuration via environment variables
- `structlog_config.py` module with configurable processor pipelines (JSON/console output, OTEL context, hierarchy context)

#### Workflow Status Display
- New `WorkflowDisplay` class in `madsci.client.workflow_display` with three rendering backends:
  - **Rich Live** (default terminal): In-place updating table with progress bar, step icons, and colored status panels
  - **Jupyter/IPython**: HTML table with styled status cells and CSS progress bar, updated in-place via `display_id`
  - **Plain text**: Simple line-based output for environments without Rich or IPython
- Auto-detection of display environment (Jupyter notebook vs terminal vs plain), overridable via `display_mode` parameter
- Per-step timing: running steps show live elapsed time, completed steps show final duration
- Step key annotations shown alongside step names when available
- Paused/queued workflow indicators in all three backends
- Formatted error prompts for workflow failure/cancellation with retry options

#### Developer Experience
- Automatic Rich traceback handler installed on `madsci.common` import for prettier exception output
- `MadsciDeveloperSettings` with `MADSCI_DISABLE_RICH_TRACEBACKS` and `MADSCI_RICH_TRACEBACKS_SHOW_LOCALS` environment variables
- OpenAPI spec auto-export and Redoc REST API documentation for all 7 managers (`docs/api-specs/`)
- `devbox.json` for reproducible development environments via Nix-based devbox

#### New Type Modules
- `interface_types.py`: Base settings for hardware interfaces (Serial, Socket, USB)
- `module_types.py`: Module and node settings hierarchy for module development
- `registry_types.py`: Registry entries, locks, and component type definitions
- `migration_types.py`: Migration status and output format types
- `backup_types.py`: PostgreSQL and document database backup settings
- `client_types.py`: `MadsciClientConfig` with standardized retry, timeout, and pooling configuration
- `context_types.py`: `MadsciContext` unified server URL settings

### Changed

- Minimum Python version raised from 3.9.1 to 3.10.0 across all packages

#### Workcell Node Reconnect Behavior
- Replaced disruptive `reset_disconnects()` (which reset **all** nodes to `initializing`) with a non-disruptive `reconnect_disconnected_nodes()` daemon thread that retries only disconnected nodes
- Reconnect attempts run in a separate background thread, so the main engine loop is never blocked by reconnect activity
- On a successful reconnect, `update_node()` naturally restores the node's status from the node's own response; on failure, the node stays disconnected and is retried on the next interval
- Default `reconnect_attempt_interval` reduced from 1200 s → 30 s, safe now that retries are non-disruptive

#### Workcell Client
- `WorkcellClient.await_workflow()` now uses `WorkflowDisplay` for rich progress output instead of raw `print()` calls with flush hacks
- New `display_mode` parameter on `await_workflow()` (default `"auto"`) to control rendering backend
- `_handle_workflow_error()` uses display-aware prompt formatting when a display instance is available
- All changes are backward-compatible; existing method signatures are preserved

- Default paths for manager runtime data (PIDs, logs, backups, workcell files, datapoints) now resolve to a project-local `.madsci/` directory via walk-up instead of always `~/.madsci/`. If no `.madsci/` or `.git/` directory is found in the directory tree, `~/.madsci/` is still used as the fallback. Set `MADSCI_SETTINGS_DIR` to override the resolution start directory.
- Backup subdirectory layout changed: `.madsci/mongodb/backups` -> `.madsci/backups/mongodb`, `.madsci/postgresql/backups` -> `.madsci/backups/postgresql`
- Definition files fully purged from runtime code: all managers now use settings-only configuration (`AbstractManagerBase[Settings]` pattern)
- `update_node_files` setting removed from production code (was `True` by default; remains only in test mocks)
- Settings consolidation for structural config overrides
- Opt-in registry resolution in manager base
- Docker reorganization: Dockerfiles and entrypoint scripts moved to `docker/` directory; compose files split into `compose.yaml`, `compose.infra.yaml`, and `compose.otel.yaml`
- Reorganized repository documentation and examples:
  - Moved `example_lab/` to `examples/example_lab/`
  - Moved example notebooks to `examples/notebooks/`
  - Moved general-purpose guides (Node Development, Workflow Development, Observability, Troubleshooting) from `example_lab/` to `docs/guides/`
  - Updated MyST TOC, compose files, and all cross-references
- Example lab now uses modern `settings.yaml` + `.env` dual-layer configuration instead of `*_MANAGER_DEFINITION` environment variables
- Example lab definition files fully deprecated: structural data (locations, transfer capabilities, resource templates, workcell nodes) extracted into standalone YAML files and inline settings; `*_manager_definition` keys removed from `settings.yaml`
- Migration tests decoupled from the live example lab using versioned fixture data (`fixtures/migration/v0.6/`)
- Added required dependencies: `structlog`, `rich`, `opentelemetry-api`, `httpx`
- Added optional dependency groups: `otel-exporters` and `tui` (madsci.client), `otel` and `otel-instrumentation` (madsci.common)

### Removed
- `example_app.py` removed (used deprecated `ExperimentApplication` and `NodeDefinition`)
- `lab_definition_path` parameter removed from `LocalRunner` (was accepted but never used)
- `load_or_create_definition()` and `load_definition()` removed entirely from the codebase

### Deprecated
- Definition files hard-deprecated in v0.7.0
- `NodeDefinition` files (use `NodeInfo.from_config()` instead)
- `NodeConfig` replaces `NodeDefinition` as the primary node configuration type
- `ManagerDefinition` files (use `ManagerSettings` instead)
- `WorkcellManagerDefinition` deprecated in favor of `WorkcellInfo` for runtime state and `WorkcellManagerSettings` for configuration
