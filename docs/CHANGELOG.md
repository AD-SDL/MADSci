# Changelog

All notable changes to the MADSci framework are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

#### `.madsci/` Sentry Directory
- Canonical `madsci.common.sentry` module for all `.madsci/` directory path resolution
- Walk-up resolution: `.madsci/` sentinel -> `.git/` boundary -> `~/.madsci/` fallback
- `madsci init` scaffolds `.madsci/` with standard subdirs and `registry.json`
- `.git/` now acts as a walk-up boundary for settings file discovery

#### Settings Directory with Walk-Up Discovery
- `_settings_dir` keyword argument on all `MadsciBaseSettings` subclasses for walk-up config file resolution
- `MADSCI_SETTINGS_DIR` environment variable for activating walk-up discovery
- `--settings-dir` CLI option on `madsci start`, `madsci start manager`, `madsci start node`, and `madsci config export`
- Walk-up resolves each filename independently: shared `settings.yaml` in a parent dir coexists with `node.settings.yaml` in a child dir
- Backward compatible: without `_settings_dir` or `MADSCI_SETTINGS_DIR`, existing CWD-relative behavior is preserved exactly

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
- `madsci config` - Configuration management (export, create, show)
- `madsci backup` - Database backup creation (PostgreSQL and MongoDB)
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
- In-memory drop-in backends for all database operations
- Ephemeral data storage for development and testing

#### Configuration Management
- `madsci config export` for exporting configuration to YAML with secret redaction
- `madsci config create` for generating configuration files from defaults
- Secret classification with `json_schema_extra={"secret": True}`
- `model_dump_safe()` method on MadsciBaseModel and MadsciBaseSettings for secret redaction
- Explicit configuration management (no auto-writing of config files)

#### Experiment Application
- `ExperimentBase` propagates lab context URLs to instance attributes for robust client creation across async boundaries and Jupyter cells
- `ExperimentTUI` thread-safe pause/cancel controls using `threading.Event` for safe cross-thread state management
- Example experiments: `example_experiment.py` (ExperimentScript) and `example_experiment_tui.py` (ExperimentTUI) in `examples/`

#### Node Module Framework
- `NodeInfo.from_config()` for creating node info from configuration
- Migration tools for database schema management
- Service registry for dynamic service discovery

#### Testing
- 2600+ automated tests
- 150+ template validation tests
- CLI tests using Click's CliRunner
- E2E test harness with tutorial validation

#### Observability
- OpenTelemetry integration for distributed tracing
- Structured logging with hierarchical context propagation
- `event_client_context()` and `get_event_client()` for context management
- Per-manager OTEL configuration via environment variables

### Changed
- Default paths for manager runtime data (PIDs, logs, backups, workcell files, datapoints) now resolve to a project-local `.madsci/` directory via walk-up instead of always `~/.madsci/`. If no `.madsci/` or `.git/` directory is found in the directory tree, `~/.madsci/` is still used as the fallback. Set `MADSCI_SETTINGS_DIR` to override the resolution start directory.
- Backup subdirectory layout changed: `.madsci/mongodb/backups` -> `.madsci/backups/mongodb`, `.madsci/postgresql/backups` -> `.madsci/backups/postgresql`
- Definition files fully purged from runtime code: all managers now use settings-only configuration (`AbstractManagerBase[Settings]` pattern)
- `update_node_files` defaults to `False` (was `True`)
- `load_definition()` replaces `load_or_create_definition()` as the primary API
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

### Removed
- `WorkcellManagerDefinition` replaced by `WorkcellInfo` for runtime state and `WorkcellManagerSettings` for configuration
- `example_app.py` removed (used deprecated `ExperimentApplication` and `NodeDefinition`)
- `lab_definition_path` parameter removed from `LocalRunner` (was accepted but never used)

### Deprecated
- Definition files hard-deprecated in v0.7.0 (previously soft-deprecated with removal planned for v0.8.0)
- `NodeDefinition` files (use `NodeInfo.from_config()` instead)
- `ManagerDefinition` files (use `ManagerSettings` instead)
- `load_or_create_definition()` (use `load_definition()` instead)
