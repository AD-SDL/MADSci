# MADSci UX Overhaul - Completion Plan

**Status**: In Progress (Phases A, B, C & D complete)
**Created**: 2026-02-12
**Related**: [UX Overhaul Plan](./ux_overhaul_plan.md) | [Implementation Progress](./ux_overhaul_progress.md)

## Context

The UX Overhaul (Phases 0-6 in the progress doc) is marked "100% Complete" but a systematic audit reveals significant gaps between what was delivered and what the original plan specified. The progress document's "Phase 6: Polish & Integration" is a *different* phase than the original plan's "Phase 6: Pure Python Mode" - the latter was never started. Additionally, several deliverables within Phases 1-5 were deferred or only partially implemented.

This plan provides a systematic approach to closing those gaps and bringing the UX overhaul to its full intended scope.

---

## Audit Summary: Gaps Identified

### 1. CLI Commands (16 of 16 implemented — 100%)

| Command | Status | Impact |
|---------|--------|--------|
| `init` | NOT IMPLEMENTED | Critical for onboarding - interactive lab setup wizard |
| `start` (lab/manager/node) | NOT IMPLEMENTED | Critical for daily operations |
| `stop` | NOT IMPLEMENTED | Critical for daily operations |
| `validate` | NOT IMPLEMENTED | Important for troubleshooting config issues |
| `run` (workflow/experiment) | NOT IMPLEMENTED | Important convenience command |
| `completion` | NOT IMPLEMENTED | Nice-to-have for shell completion |
| `backup` | NOT EXPOSED | Exists as separate CLI, not integrated into `madsci` |

**Testing gaps**: `registry`, `migrate`, and `tui` commands have zero dedicated tests.

### 2. Templates (26 of ~26 planned — 100%) ✅ COMPLETE (Phase C)

| Category | Implemented | Missing |
|----------|-------------|---------|
| Module | basic, device, instrument, liquid_handler, robot_arm, camera | - |
| Node | basic | - |
| Interface | fake, real, sim, mock | - |
| Lab | minimal, standard, distributed | - |
| Experiment | ALL 4 | - |
| Workflow | ALL 2 | - |
| Workcell | basic | - |
| Comm patterns | serial, socket, rest, sdk, modbus | - |

### 3. TUI (Phase D features complete) ✅ COMPLETE (Phase D)

**Implemented**: Dashboard, Status, Logs, Nodes, Workflows screens + keyboard navigation + auto-refresh + CSS theming + Trogon command palette
**Remaining (deferred)**:
- Interactive wizards for `madsci new` (Phase 3+ - significant UI work)
- Custom widgets (widgets/ dir is empty - can be extracted from screens as needed)

### 4. Integration Gaps

- **Managers still use old definition pattern**: All 7 managers still use `AbstractManagerBase[Settings, Definition]` with `manager_definition` pointing to YAML files. The new settings/registry system exists but is **not integrated** into any existing manager.
- **ID Registry is standalone**: The registry CLI works but no manager uses it for identity resolution at startup.
- **Migration tool untested against example_lab**: Scanner/converter exist but haven't been validated against the actual `example_lab/` definition files.
- **example_lab not migrated**: Still uses 8 manager definition YAML files (7 `*.manager.yaml` + 1 `example_workcell.yaml`) plus 6 node definitions and 7 node info files in the old format.

### 5. ExperimentCampaign (documented as "Future")

`ExperimentCampaign` was described in the plan with detailed design notes but explicitly marked as future work. No implementation exists.

### 6. Implicit Configuration File Writing (No explicit management)

Both managers and nodes automatically write configuration files to disk on startup:
- **Managers**: `load_or_create_definition()` (method at `manager_base.py:486`) unconditionally writes `definition.to_yaml()` (the write call at `manager_base.py:520`) with no opt-out flag
- **Nodes**: `_update_node_info_and_definition()` writes both `*.node.yaml` and `*.info.yaml` (`abstract_node_module.py:1208-1223`), controlled by `update_node_files` (default: `True`)
- **No explicit CLI commands** exist for creating, exporting, or managing configuration files
- **Secret handling is ad-hoc**: `get_settings_export()` uses runtime pattern matching against field names (`password`, `secret`, `token`, etc.) rather than field-level metadata
- **NodeInfo** inherits from `NodeDefinition` and will need redesigning once definition files are removed

### 7. Pure Python Mode (original Phase 6 - 0%)

The entire stretch goal is unstarted:
- No SQLite adapter for PostgreSQL managers
- No in-memory adapter for MongoDB managers
- No single-process mode
- No storage backend abstraction layer

---

## Proposed Completion Phases

### Phase A: Test Coverage & Stability (Foundation) [Overall: M] ✅ COMPLETE

**Goal**: Ensure everything that's already built actually works correctly and has test coverage.

**Rationale**: Before adding new features, we need confidence the existing code is solid. Several implemented commands have zero tests.

**Completed**: 2026-02-12

#### A.1 Add missing CLI command tests [S] ✅
- `registry` command tests (21 tests): list (empty/populated/filtered/json), resolve (found/not found/json), rename (success/nonexistent), clean (empty/dry-run), export (stdout/file), import
- `migrate` command tests (21 tests): scan (empty/manager yaml/node yaml/example_lab/json/verbose), convert (no mode/no files/dry-run empty), status, finalize (no mode/dry-run), rollback (no files/nothing to rollback)
- `tui` command tests (5 tests): help, screen choices, mocked launch, import error handling, `ui` alias

**Files created**:
- `src/madsci_client/tests/cli/test_registry.py` (21 tests)
- `src/madsci_client/tests/cli/test_migrate.py` (21 tests)
- `src/madsci_client/tests/cli/test_tui.py` (5 tests)

**Existing patterns followed**: `src/madsci_client/tests/cli/test_version.py` (uses `CliRunner`)

#### A.2 Validate migration tool against example_lab [M] ✅
- Scanner finds 20 definition files: 7 manager + 6 node + 7 workflow (note: `.info.yaml` and `example_workcell.yaml` are not scanned because they don't match `*.manager.yaml`/`*.node.yaml`/`*.workflow.yaml` patterns)
- All files have PENDING status, valid component IDs, and planned migration actions
- `convert --dry-run` produces correct output without modifying files
- 12 integration tests added

**Files created**:
- `src/madsci_client/tests/cli/test_migrate_example_lab.py` (12 tests)

**Files involved**:
- `example_lab/` definition files
- `src/madsci_common/madsci/common/migration/scanner.py`
- `src/madsci_common/madsci/common/migration/converter.py`

#### A.3 Verify test suite baseline [S] ✅
- 2063 tests pass (up from 2004+ baseline, with the 59 new tests)
- `madsci doctor` — 12/12 checks pass
- `madsci version` — works correctly
- `madsci new module --no-interactive` — scaffolds 10 files correctly
- Gate passed: Phase B is unblocked

**Done when**:
- ✅ All existing tests pass (`pytest` green) — 2063 passed
- ✅ `registry`, `migrate`, and `tui` commands each have dedicated test files with `--help` and basic invocation tests
- ✅ `madsci migrate scan` successfully finds all definition files in `example_lab/`
- ✅ `madsci doctor`, `madsci version`, and `madsci new module --no-interactive` work end-to-end

---

### Phase B: CLI Lifecycle Commands (Critical UX) [Overall: L] ✅ COMPLETE

**Goal**: Implement the most impactful missing CLI commands for daily operations.

**Rationale**: `start`, `stop`, and `init` are the biggest gaps for the "zero to working lab in an afternoon" goal. Without them, users must manually start services via `just up` / `docker compose`.

**Completed**: 2026-02-12

**Note — CLI help text cleanup**: The main `madsci` help text has been updated to reflect the actual `madsci start` command signature (no `lab` subcommand). The `val` alias now correctly resolves to the implemented `validate` command. All 7 new commands are registered in `_LAZY_COMMANDS`.

#### B.1 `madsci start` command (Docker Compose wrapper) [S-M] ✅

A thin wrapper around `docker compose up`. Today, users start the lab via `just up` (which runs `docker compose up` — see `.justfile:98-99`) or by running `docker compose` directly. Individual managers are started via `python -m madsci.<pkg>.<name>_server` (see `compose.yaml` service definitions). This command makes that workflow discoverable through the `madsci` CLI without reinventing process management.

**Scope**:
- `madsci start` — locate `compose.yaml` (current dir, parent, or via `--config` path) and run `docker compose up`
- `madsci start -d` / `--detach` — maps to `docker compose up -d`
- `madsci start --build` — maps to `docker compose up --build`
- `madsci start --services <svc ...>` — start only specific services (passed through to `docker compose up`)
- Friendly error messages: Docker not installed (reuse `shutil.which("docker")` pattern from `doctor.py:129`), compose file not found, port conflicts
- Rich console output showing what's starting

**Explicitly deferred** (see "Deferred: Extended Start/Stop" below):
- `madsci start manager <name>` — individual manager subprocess management
- `madsci start node <name|path>` — individual node startup
- `--mode=local` — Pure Python mode (Phase F)
- `--mode=hybrid` — mixed Docker/local mode
- PID files, process group management, health check polling

**Files to create**:
- `src/madsci_client/madsci/client/cli/commands/start.py`
- `src/madsci_client/tests/cli/test_start.py`

**Files to modify**:
- `src/madsci_client/madsci/client/cli/__init__.py` (add to `_LAZY_COMMANDS`)

**Design reference**: `docs/designs/cli_design.md` (section: "Start Command")

#### B.2 `madsci stop` command (Docker Compose wrapper) [S] ✅
Paired with B.1. Wraps `docker compose down`.

- `madsci stop` — `docker compose down`
- `madsci stop --remove` — `docker compose down --rmi local` (remove images)
- `madsci stop --volumes` — `docker compose down -v` (with confirmation prompt, since this destroys data)
- Same compose file location logic as B.1

**Files to create**:
- `src/madsci_client/madsci/client/cli/commands/stop.py`
- `src/madsci_client/tests/cli/test_stop.py`

#### B.3 `madsci init` command [L] ✅
- Interactive lab initialization wizard
- Template selection (minimal, standard)
- Generates lab configuration, docker-compose, .env files
- Sets up directory structure
- Registers components in local registry

**Files to create**:
- `src/madsci_client/madsci/client/cli/commands/init.py`
- `src/madsci_client/tests/cli/test_init.py`

**Design reference**: `docs/designs/cli_design.md` (section: "Init Command")

#### B.4 `madsci validate` command [M] ✅
- Validate configuration files (settings, workflows, workcell configs)
- Scan directory for issues
- JSON output for CI integration

**Files to create**:
- `src/madsci_client/madsci/client/cli/commands/validate.py`
- `src/madsci_client/tests/cli/test_validate.py`

#### B.5 `madsci run` command [S] ✅
- `madsci run workflow <path>` - Submit workflow to workcell
- `madsci run experiment <path>` - Run experiment script

**Files to create**:
- `src/madsci_client/madsci/client/cli/commands/run.py`
- `src/madsci_client/tests/cli/test_run.py`

#### B.6 `madsci completion` command [S] ✅
- Generate shell completion scripts (bash, zsh, fish)
- Uses Click's built-in shell completion support

**Files to create**:
- `src/madsci_client/madsci/client/cli/commands/completion.py`

#### B.7 `madsci backup` command integration [S] ✅
The backup functionality already exists as standalone CLIs (`madsci-backup`, `madsci-postgres-backup`, `madsci-mongodb-backup`) with well-tested `PostgreSQLBackupTool` and `MongoDBBackupTool` classes in `madsci.common.backup_tools`. This task simply wires those tools into the main `madsci` CLI for discoverability.

- Add `madsci backup` command group that delegates to existing backup tools
- `madsci backup create` — auto-detect database type and create backup
- `madsci backup list` — list available backups
- `madsci backup restore <path>` — restore from a backup file

**Files to create**:
- `src/madsci_client/madsci/client/cli/commands/backup.py`
- `src/madsci_client/tests/cli/test_backup.py`

**Files to modify**:
- `src/madsci_client/madsci/client/cli/__init__.py` (add to `_LAZY_COMMANDS`)

**Done when**:
- ✅ All 7 new commands (`start`, `stop`, `init`, `validate`, `run`, `completion`, `backup`) pass `--help` invocation tests — 47 new tests, all passing
- ✅ `madsci start` / `madsci stop` successfully wrap `docker compose up` / `docker compose down` (with `--config` for compose file location)
- ✅ `madsci init` generates a minimal working lab directory using the template engine
- ✅ `madsci backup create` delegates to the existing backup tools (`madsci.common.backup_tools.cli`)
- ✅ CLI help text in `cli/__init__.py` updated (`madsci start` instead of `madsci start lab`)
- ✅ `val` alias connected to working `validate` command

**Files created**:
- `src/madsci_client/madsci/client/cli/commands/start.py` (Docker Compose `up` wrapper)
- `src/madsci_client/madsci/client/cli/commands/stop.py` (Docker Compose `down` wrapper)
- `src/madsci_client/madsci/client/cli/commands/init.py` (Lab initialization wizard)
- `src/madsci_client/madsci/client/cli/commands/validate.py` (Config validation with schema checking)
- `src/madsci_client/madsci/client/cli/commands/run.py` (Workflow/experiment runner)
- `src/madsci_client/madsci/client/cli/commands/completion.py` (Shell completions for bash/zsh/fish)
- `src/madsci_client/madsci/client/cli/commands/backup.py` (Re-exports existing backup CLI)
- `src/madsci_client/tests/cli/test_start.py` (8 tests)
- `src/madsci_client/tests/cli/test_stop.py` (5 tests)
- `src/madsci_client/tests/cli/test_init.py` (5 tests)
- `src/madsci_client/tests/cli/test_validate.py` (7 tests)
- `src/madsci_client/tests/cli/test_run.py` (9 tests)
- `src/madsci_client/tests/cli/test_completion.py` (6 tests)
- `src/madsci_client/tests/cli/test_backup.py` (7 tests)

**Files modified**:
- `src/madsci_client/madsci/client/cli/__init__.py` (added 7 entries to `_LAZY_COMMANDS`, updated help text)

**Test results**: 2110 tests pass (up from 2063 baseline, +47 new tests)

#### Deferred: Extended Start/Stop

The following capabilities are deferred from the initial B.1/B.2 scope. They can be added incrementally as separate tasks once the Docker Compose wrapper is stable.

| Capability | Rationale for deferral |
|------------|----------------------|
| `madsci start manager <name>` | Users can already run `python -m madsci.<pkg>.<name>_server` directly. Wrapping this requires subprocess + PID management that isn't needed for v1. |
| `madsci start node <name or path>` | Same — nodes are started via `python <module>.py` with `NODE_DEFINITION` and `NODE_URL` env vars. |
| `--mode=local` (all managers as subprocesses) | Requires process group management, PID tracking, SIGINT handling, port availability checks. Belongs in Phase F (Pure Python Mode). |
| `--mode=hybrid` | Depends on both Docker and local modes being solid. |
| Health check polling | Nice-to-have for `madsci start -d` but not blocking. Can be added when `madsci status` (already implemented) can be called programmatically. |

---

### Phase C: Templates Expansion [Overall: L] ✅ COMPLETE

**Goal**: Build out the template library to cover the most common use cases.

**Rationale**: Templates are the primary mechanism for the "scaffolding" principle. More templates means fewer users copy-pasting and manually editing.

**Completed**: 2026-02-12

#### C.0 Template generator decision [S] ✅
- **Decision**: Copy-and-modify approach. A meta-template generator was not needed for 4 module templates. All module templates share identical `template.yaml` structure; only the `.j2` file content differs (domain-specific actions, types, interface methods).

#### C.1 Additional module templates [L] ✅
- `module/instrument` - Measurement devices (measure, calibrate, get_instrument_status, reset_instrument). Includes `Reading`, `CalibrationData`, and `Result` domain types.
- `module/liquid_handler` - Pipetting (aspirate, dispense, transfer, pick_up_tips, drop_tips, get_handler_status). Includes `AspirateCommand`, `DispenseCommand`, and `Result` domain types.
- `module/robot_arm` - Material handling (pick, place, move, home, get_arm_status). Includes `Position` and `Result` domain types.
- `module/camera` - Vision systems (capture, configure_camera, get_camera_status, reset_camera). Includes `CaptureResult` and `Result` domain types.

Each template has 10 `.j2` files following the `module/device/` pattern: rest_node, interface, fake_interface, types, __init__, tests/__init__, test_interface, pyproject.toml, README, Dockerfile.

**Files created** (4 templates x 11 files each = 44 files):
- `src/madsci_common/madsci/common/bundled_templates/module/instrument/` (template.yaml + 10 `.j2` files)
- `src/madsci_common/madsci/common/bundled_templates/module/liquid_handler/` (template.yaml + 10 `.j2` files)
- `src/madsci_common/madsci/common/bundled_templates/module/robot_arm/` (template.yaml + 10 `.j2` files)
- `src/madsci_common/madsci/common/bundled_templates/module/camera/` (template.yaml + 10 `.j2` files)

#### C.2 Additional interface templates [S-M] ✅
- `interface/real` - Generic hardware interface stub with TODO markers for connection lifecycle, error handling, and logging
- `interface/sim` - External simulator connection template
- `interface/mock` - Pytest mock wrapper template

**Files created** (3 templates x 2 files each = 6 files):
- `src/madsci_common/madsci/common/bundled_templates/interface/real/` (template.yaml + 1 `.j2` file)
- `src/madsci_common/madsci/common/bundled_templates/interface/sim/` (template.yaml + 1 `.j2` file)
- `src/madsci_common/madsci/common/bundled_templates/interface/mock/` (template.yaml + 1 `.j2` file)

#### C.3 Lab templates [M] ✅
- `lab/standard` - Standard lab with all managers, Docker compose, full infrastructure (7 `.j2` files)
- `lab/distributed` - Multi-host lab with Docker swarm/k8s configs (8 `.j2` files, includes `compose.nodes.yaml`)

**Files created**:
- `src/madsci_common/madsci/common/bundled_templates/lab/standard/` (template.yaml + 7 `.j2` files)
- `src/madsci_common/madsci/common/bundled_templates/lab/distributed/` (template.yaml + 8 `.j2` files)

#### C.4 Template validation [S] ✅
- All 26 templates covered by `TestTemplateCompleteness` tests (existence, defaults validation, render, Python syntax)
- All templates render successfully with default parameters
- All generated Python passes syntax check (`ast.parse`)
- Added `COMM` value to `TemplateCategory` enum in `template_types.py`
- Added detailed render+content tests for `instrument` and `liquid_handler` modules (matching existing `camera` and `robot_arm` test patterns)
- Added registry category filter tests for `comm` and `lab` categories

**Files modified**:
- `src/madsci_common/tests/test_templates/test_template_engine.py` (150 tests, up from ~85)
- `src/madsci_common/madsci/common/types/template_types.py` (added `COMM` to `TemplateCategory` enum)

#### C.5 Communication pattern templates [L] ✅
- `comm/serial` - pySerial-based serial port communication (open/close/read/write/flush)
- `comm/socket` - Raw TCP/UDP socket communication (connect/disconnect/send/receive)
- `comm/rest` - REST API client wrapping httpx/requests (GET/POST/PUT/DELETE with retry)
- `comm/sdk` - Vendor SDK wrapper pattern (load library, initialize, cleanup, wrap calls)
- `comm/modbus` - Modbus TCP/RTU communication via pymodbus (read/write registers and coils)

Each template includes: interface class, fake interface, test file, README.

**Files created** (5 templates x 5 files each = 25 files):
- `src/madsci_common/madsci/common/bundled_templates/comm/serial/` (template.yaml + 4 `.j2` files)
- `src/madsci_common/madsci/common/bundled_templates/comm/socket/` (template.yaml + 4 `.j2` files)
- `src/madsci_common/madsci/common/bundled_templates/comm/rest/` (template.yaml + 4 `.j2` files)
- `src/madsci_common/madsci/common/bundled_templates/comm/sdk/` (template.yaml + 4 `.j2` files)
- `src/madsci_common/madsci/common/bundled_templates/comm/modbus/` (template.yaml + 4 `.j2` files)

**Done when**:
- ✅ All 26 templates render successfully with default parameters (150 tests pass)
- ✅ Generated Python passes syntax check
- ✅ All templates covered by `TestTemplateCompleteness` tests (existence, defaults, render, syntax)
- ✅ `madsci new` can list and scaffold each new template type via `TemplateCategory` enum
- ✅ `TemplateCategory.COMM` added to enum for proper category filtering

---

### Phase D: TUI Enhancements [Overall: L] ✅ COMPLETE

**Goal**: Bring the TUI from MVP to the full feature set described in the TUI design document.

**Completed**: 2026-02-12

#### D.1 Trogon command palette integration [M] ✅
- Trogon was already a dependency (`>=0.6.0`)
- Since Trogon creates its own Textual App (can't nest Textual apps), implemented as:
  - `madsci commands` CLI command — standalone Trogon command palette
  - `cmd` alias registered
  - `Ctrl+P` in TUI exits and launches Trogon command palette
- Version compatibility confirmed: trogon 0.6.0 works with textual >=0.50.0

**Files created**:
- `src/madsci_client/madsci/client/cli/commands/commands.py` (Trogon command palette launcher)

**Files modified**:
- `src/madsci_client/madsci/client/cli/__init__.py` (added `commands` to `_LAZY_COMMANDS`, `cmd` alias)
- `src/madsci_client/madsci/client/cli/tui/app.py` (added `Ctrl+P` binding for command palette)
- `src/madsci_client/madsci/client/cli/commands/tui.py` (handle return code 2 to launch Trogon after TUI exit)

#### D.2 Auto-refresh on dashboard and status screens [S] ✅
- Added configurable timer-based refresh (5s default) to both Dashboard and Status screens
- Uses Textual's `set_interval()` for periodic updates
- `a` keybinding toggles auto-refresh on/off with visual feedback in footer
- Footer shows current auto-refresh state

**Files modified**:
- `src/madsci_client/madsci/client/cli/tui/screens/dashboard.py` (auto-refresh timer, toggle, footer)
- `src/madsci_client/madsci/client/cli/tui/screens/status.py` (auto-refresh timer, toggle, footer)

#### D.3 Node management screen [M] ✅
- New screen showing discovered nodes from Workcell Manager (`GET /nodes` on port 8005)
- DataTable with Status, Node name, URL, Action count, State columns
- NodeDetailPanel showing node URL, status, available actions list, admin capabilities, errors
- Row selection updates detail panel
- Auto-refresh with toggle (consistent with other screens)
- Keyboard shortcuts: `n` to navigate, `a` toggle auto-refresh, `r` manual refresh, `Esc` back

**Files created**:
- `src/madsci_client/madsci/client/cli/tui/screens/nodes.py` (247 lines)

#### D.4 Workflow visualization screen [L] ✅
- Active workflows table from `GET /workflows/active` and `GET /workflows/queue`
- DataTable with Status icon, Name, Progress (completed/total), Current Step, Started time, Duration
- WorkflowDetailPanel with:
  - Workflow header (name, ID, status with color)
  - Timing info (started, ended, duration)
  - Step progress bar (Unicode block characters, 20-char width, percentage)
  - Step list with icons (✓ completed, ► running, ○ pending) and node assignments
- Workflow control: `p` pause, `u` resume, `c` cancel (sends POST to workcell manager)
- Auto-refresh with toggle

**Files created**:
- `src/madsci_client/madsci/client/cli/tui/screens/workflows.py` (493 lines)

#### D.5 CSS theming [S] ✅
- Moved all inline CSS from `app.py` (60 lines) and screen `DEFAULT_CSS` blocks to external `.tcss` file
- Created `styles/theme.tcss` with consolidated styles for all components
- Uses Textual CSS variables (`$surface`, `$primary`, `$success`, `$warning`, `$error`) for theme compatibility
- Supports Textual's built-in light/dark theme toggling automatically

**Files created**:
- `src/madsci_client/madsci/client/cli/tui/styles/theme.tcss` (consolidated theme, 95 lines)

**Files modified**:
- `src/madsci_client/madsci/client/cli/tui/app.py` (replaced inline `CSS` with `CSS_PATH`)
- `src/madsci_client/madsci/client/cli/tui/screens/dashboard.py` (removed 3 `DEFAULT_CSS` blocks)
- `src/madsci_client/madsci/client/cli/tui/screens/status.py` (removed 1 `DEFAULT_CSS` block)
- `src/madsci_client/madsci/client/cli/tui/screens/logs.py` (removed 2 `DEFAULT_CSS` blocks)

#### Additional changes ✅

**App-level updates**:
- Registered 2 new screens (`nodes`, `workflows`) in `SCREENS` dict
- Added keybindings: `n` (Nodes), `w` (Workflows), `Ctrl+P` (Commands)
- Updated help text with all keybindings
- Updated `tui.py` `--screen` choices to include `nodes` and `workflows`
- Updated Quick Actions panel with new screen shortcuts

**Screens package**:
- Updated `screens/__init__.py` with `NodesScreen` and `WorkflowsScreen` exports

**Tests**:
- 14 tests total (up from 5): TUI command (5), Commands command (3), Screen imports (6)
- Tests cover: help output, screen choices, mocked launch, import error handling, aliases, screen imports, theme CSS existence and content

**Done when**:
- ✅ `madsci tui` launches without errors and all 5 screens are accessible via keyboard navigation (`d`, `s`, `l`, `n`, `w`)
- ✅ Dashboard and status screens auto-refresh on 5s interval with `a` toggle
- ✅ Node management screen displays nodes from Workcell Manager with detail panel
- ✅ Workflow visualization screen shows active workflows with step progress and control actions
- ✅ All styles in external CSS file (`styles/theme.tcss`); Textual theme variables used for light/dark support
- ✅ Trogon command palette accessible via `madsci commands` / `Ctrl+P` in TUI
- ✅ 14 tests pass, ruff check clean, ruff format clean

**Test results**: 2119 tests pass (up from 2110 baseline, +9 new tests)

---

### Phase E: Integration & Migration (Deferred Items) [Overall: XL]

**Goal**: Connect the new infrastructure (registry, settings, migration) to the actual managers.

**Rationale**: The registry, settings consolidation, and migration tools exist but are standalone. The original plan's intent was to replace definition files with the new pattern.

**Risk note**: E.2 and E.3 modify `AbstractManagerBase`, which is the base class for all 7 managers. Changes here have high blast radius. The migration strategy below is designed to minimize risk through gradual rollout.

**Sequencing constraint with Phase G**: Both Phase E and Phase G modify `load_or_create_definition()` in `manager_base.py`. Specifically, E.2 adds registry resolution as an alternative to definition file loading, while G.2 removes the auto-writing of definition files. **G.2 must not be applied to a manager until E.2 has been completed for that manager**, otherwise there is no fallback: the manager would neither auto-create a definition file nor resolve its identity from the registry. The per-manager rollout order (Location -> Event -> Data -> ... -> Lab) should be shared between E.2 and G.2, with each manager completing E.2 before G.2 is applied to it.

**Rollback plan**: Phase E changes to `AbstractManagerBase` (in `src/madsci_common/madsci/common/manager_base.py`) affect all 7 managers. Before each manager migration, use the existing backup tools (`madsci backup create` from B.7, or directly via `PostgreSQLBackupTool`/`MongoDBBackupTool`) to snapshot the manager's database. The opt-in flag in E.2 provides a code-level rollback (set `enable_registry_resolution: False` to revert), but this requires that the old definition YAML files still exist on disk — so G.2 (remove auto-writing) must not have been applied yet, or the definition files must have been preserved manually. Each manager migration should be a separate PR so it can be reverted independently.

#### E.1 example_lab migration [M] ✅
- Run migration tool against example_lab
- Validate all components register in local registry
- Update example_lab to work with both old and new patterns
- Document the migration process in `docs/guides/migration.md`

**Files created**:
- `docs/guides/migration.md` (migration guide)
- `src/madsci_client/tests/cli/test_migrate_apply.py` (8 integration tests)

**Files modified**:
- `example_lab/.env` (added commented-out settings equivalents)

#### E.2 Manager integration with ID Registry [XL]

**Migration strategy** (gradual rollout):
1. **Add opt-in support first**: Add an `enable_registry_resolution: bool = False` setting to `AbstractManagerBase`. When `True`, the manager resolves its ID from the registry at startup; when `False` (default), behavior is unchanged.
2. **Pilot with one low-risk manager**: Enable registry resolution on the **Location Manager** first (lowest downstream impact). Validate in example_lab.
3. **Roll out to remaining managers one at a time**: Event -> Data -> Experiment -> Resource -> Workcell -> Lab (ordered by increasing risk/complexity).
4. **Deprecation phase**: Once all managers work with registry resolution, emit deprecation warnings when `manager_definition` YAML files are used without a registry entry. Set a target version for removing the old pattern.
5. **Remove old pattern**: Flip default to `True`, then remove the flag entirely.

**Files to modify**:
- `src/madsci_common/madsci/common/manager_base.py`
- Individual manager settings classes (to add `enable_registry_resolution`)

#### E.3 Settings consolidation in managers [L]
- Gradually move structural config from definitions to settings
- Follow the same gradual rollout order as E.2 (Location -> Event -> Data -> ... -> Lab)
- Workcell nodes list moves from WorkcellManagerDefinition to WorkcellManagerSettings
- Update docker-compose/env files to match
- Each manager migration should be a separate, reviewable PR

**Done when**:
- `madsci migrate scan` finds all definition files in `example_lab/` and `madsci migrate convert --dry-run` produces correct output
- `example_lab/` works with both old and new configuration patterns
- At least the Location Manager successfully resolves its identity from the registry at startup
- All 7 managers have been migrated to registry resolution (E.2 rollout complete)
- Structural config has been moved from definitions to settings for all managers

---

### Phase F: Pure Python Mode (Stretch Goal) [Overall: XXL]

**Goal**: Run full MADSci stack without Docker.

**Rationale**: This was the original plan's Phase 6. It's the most impactful change for lowering the barrier to entry, especially on Windows. However, it requires significant architectural changes.

#### F.1 Storage backend abstraction [XL]
- Define `StorageBackend` protocol
- Implement `SQLiteBackend` for PostgreSQL managers
- Implement `InMemoryBackend` for MongoDB managers

#### F.2 Single-process mode [XL]
- `madsci start --mode=local` runs all managers in-process
- Use asyncio for concurrent manager execution
- SQLite-based queue as Redis alternative

#### F.3 Manager backend adapters [L]
- Resource Manager: SQLite adapter
- Event/Experiment/Workcell/Data/Location Managers: In-memory or TinyDB adapter

**Risk notes**:
- **SQLite concurrency**: SQLite does not support concurrent writes from multiple processes. If managers share a database or if multiple manager instances run simultaneously, this will require WAL mode, connection serialization, or a different approach.
- **Crash recovery**: In-memory backends lose all state on process crash. This is acceptable for development/testing but must be clearly documented as unsuitable for production use.
- **Abstraction overhead**: The `StorageBackend` protocol adds an indirection layer to every database operation. Care must be taken to ensure this does not degrade performance on the existing PostgreSQL/MongoDB paths that production labs rely on.

**Done when**:
- `madsci start --mode=local` starts all managers in a single process without Docker
- All manager operations work against SQLite/in-memory backends
- Existing PostgreSQL/MongoDB paths are unaffected (performance regression tests pass)
- Works on macOS, Linux, and Windows

---

### Phase G: Explicit Configuration Management [Overall: XL]

**Goal**: Replace implicit auto-writing of definition and info files with explicit CLI commands and secure secret handling for configuration exports.

**Rationale**: Currently, both managers and nodes silently write configuration files to disk on every startup. Managers unconditionally write definitions back in `load_or_create_definition()` (`manager_base.py:520`) with no opt-out. Nodes write both `*.node.yaml` and `*.info.yaml` via `_update_node_info_and_definition()` (`abstract_node_module.py:1208-1223`), controlled by `update_node_files` (default: `True`). This is problematic:

- **Surprising behavior**: files appear/change without user action, making it unclear what the "source of truth" is
- **Security risk**: exported configuration can contain secrets (current mitigation is ad-hoc pattern matching in `get_settings_export()`)
- **Blocks clean deprecation**: definition files are deprecated (v0.7.0) but still always written by managers
- **Complicates version control**: auto-written files create spurious diffs

The replacement model: configuration is created explicitly via CLI commands, exported explicitly when needed, and secrets are never included in exports unless the user opts in.

#### G.1 Secret field classification system [M]

**Prerequisite** for G.4. Foundation: replace the ad-hoc runtime pattern matching in `get_settings_export()` (`manager_base.py:447-465`) with a proper metadata-driven system.

**Current state**: The only secret redaction is a list of exact-match patterns (`password`, `secret`, `credential`, `api_key`, `apikey`) and boundary patterns (`token`, `key`, `auth`) applied at serialization time. No `SecretStr` usage exists anywhere in the codebase. No field-level metadata marks fields as sensitive.

**Design (based on Pydantic v2 best practices)**:

1. **Use `SecretStr` for string secrets** (passwords, tokens, API keys). This gives automatic masking in `repr()`, `str()`, and logs — the standard Pydantic approach.
2. **Use `json_schema_extra={"secret": True}` for non-string sensitive fields** (e.g., a `dict` containing credentials). This provides a programmatic way to discover which fields are sensitive.
3. **Use Pydantic serialization context** to control export behavior: `model_dump(context={"include_secrets": True})` reveals secrets; default behavior redacts them.
4. **Add a `model_dump_safe()` convenience method** to `MadsciBaseModel` that uses the context-based approach internally, replacing the need for callers to know about the context key.

**Scope**:
- Add `SecretStr` to fields like database passwords, API keys, and tokens across all Settings classes
- Add `json_schema_extra={"secret": True}` annotation to non-string sensitive fields
- Add `model_dump_safe(include_secrets: bool = False)` to `MadsciBaseModel`
- Add a `@model_serializer(mode='wrap')` or `@field_serializer` to `MadsciBaseSettings` that respects serialization context for secret redaction
- Replace the ad-hoc pattern matching in `get_settings_export()` with the new metadata-driven approach
- Ensure `to_yaml()` uses safe serialization by default (secrets redacted unless explicitly requested)

**Files to modify**:
- `src/madsci_common/madsci/common/types/base_types.py` (add `model_dump_safe()` and context-aware serialization)
- `src/madsci_common/madsci/common/manager_base.py` (update `get_settings_export()` to use new system)
- All manager `*_types.py` / settings files (add `SecretStr` annotations where appropriate)
- `src/madsci_common/madsci/common/types/node_types.py` (annotate sensitive NodeConfig/RestNodeConfig fields)

**Tests**:
- Verify `model_dump()` redacts secrets by default
- Verify `model_dump_safe(include_secrets=True)` reveals them
- Verify `to_yaml()` never writes secrets unless explicitly requested
- Verify the `/settings` endpoint still redacts properly

**Prior art / references**:
- Pydantic `SecretStr` / `SecretBytes`: automatic masking, explicit `get_secret_value()`
- Pydantic `json_schema_extra`: field-level metadata for programmatic discovery
- Pydantic serialization context: `info.context.get("include_secrets", False)` pattern
- See: https://docs.pydantic.dev/latest/concepts/types/#secret-types

#### G.2 Remove auto-writing of manager definition files [M]

Remove the unconditional `definition.to_yaml(def_path)` call in `AbstractManagerBase.load_or_create_definition()` (`manager_base.py:520`). Managers should load definitions but never silently write them back.

**Scope**:
- Remove `definition.to_yaml(def_path)` from `load_or_create_definition()`
- If definition file doesn't exist and no settings-based config is provided, raise a clear error with guidance: `"No manager configuration found. Run 'madsci config create manager <type>' to generate one, or set configuration via environment variables."`
- Keep `load_or_create_definition()` for backwards compatibility but make it load-only (rename to `load_definition()`, keep old name as deprecated alias)
- Update tests to verify no file writing occurs on manager startup

**Files to modify**:
- `src/madsci_common/madsci/common/manager_base.py`
- Manager-specific test files (verify no surprise file writes)

#### G.3 Remove auto-writing of node definition and info files [M]

Change `update_node_files` default from `True` to `False`, and deprecate the auto-writing behavior.

**Scope**:
- Change `NodeConfig.update_node_files` default from `True` to `False`
- Emit deprecation warning when `update_node_files=True` is explicitly set, pointing to `madsci config export` and `madsci node info --export`
- Plan removal of `_update_node_info_and_definition()` in a future version (target v0.8.0, consistent with definition file deprecation timeline)
- Update `example_lab/` node configs to not rely on auto-written files

**Files to modify**:
- `src/madsci_common/madsci/common/types/node_types.py` (change default, add deprecation)
- `src/madsci_node_module/madsci/node_module/abstract_node_module.py` (add deprecation warning in `_update_node_info_and_definition()`)
- `example_lab/` node configuration files

#### G.4 `madsci config` command group [M]

Explicit commands for managing configuration, replacing the auto-writing behavior with user-initiated actions.

**Subcommands**:
- `madsci config export` — export current configuration to stdout or file
  - `--output <path>` — write to specific file (default: stdout)
  - `--format yaml|json|toml` — output format (default: yaml)
  - `--include-secrets` — explicitly opt in to including secret values (default: redacted, with prominent warning)
  - `--include-defaults` — include fields that match their defaults
  - Works for both manager and node configurations (auto-detects from context, or specify `--manager <name>` / `--node <name|url>`)
- `madsci config create manager <type>` — generate a new manager configuration file from template
  - Interactive prompts for required values (name, ports, database URLs, etc.)
  - `--no-interactive` flag with sensible defaults
  - `--output <path>` — output location
- `madsci config create node <type>` — generate a new node configuration file from template
  - Same interactive/non-interactive pattern

**Note**: Evaluate overlap with `madsci new`. The distinction: `madsci new` scaffolds a full project (pyproject.toml, src/, tests/); `madsci config create` generates a single configuration file for deploying an existing component. They serve different audiences (developer vs. operator).

Uses the secret classification from G.1 for redaction in exports.

**Files to create**:
- `src/madsci_client/madsci/client/cli/commands/config.py`
- `src/madsci_client/tests/cli/test_config.py`

**Files to modify**:
- `src/madsci_client/madsci/client/cli/__init__.py` (add to `_LAZY_COMMANDS`)

#### G.5 Update NodeInfo for post-NodeDefinition world [L]

Currently `NodeInfo` inherits from `NodeDefinition` (`node_types.py:300`) and adds runtime fields (`node_url`, `actions`, `config`, `config_schema`). In a world where `NodeDefinition` files are no longer auto-written, NodeInfo needs to be reconsidered.

**Design considerations**:
- NodeInfo's identity fields (`node_name`, `node_id`, `module_name`, `module_version`, `node_type`) currently come from `NodeDefinition`. In a post-definition world, these should come from `NodeConfig`/settings or from module-level metadata (e.g., class attributes on the `AbstractNodeModule` subclass).
- The `config_schema` field should remain auto-generated from the settings class via `model_json_schema()`.
- The `actions` dict should continue to be built from decorated methods at startup.
- The `/info` REST endpoint response format should remain stable for backwards compatibility.

**Scope**:
- **Decouple NodeInfo from NodeDefinition inheritance**: Use composition instead. NodeInfo gets its identity fields from settings/module metadata, not from a separate definition model.
- **Move identity fields to NodeConfig**: `node_name`, `node_id`, `node_type`, `module_name`, `module_version` become settings (some already partially exist on `NodeConfig`). Generate defaults from module class metadata where possible.
- **NodeInfo becomes purely runtime**: Generated on-demand from settings + module introspection, never persisted automatically.
- **CLI integration**:
  - `madsci node info <name|url>` — query a running node's `/info` endpoint and display it
  - `madsci node info --export <path>` — save the info artifact to a file (explicit user action)
- **`from_node_def_and_config()` update**: Replace or supplement with `from_config()` factory that builds NodeInfo from settings + introspected actions, without requiring a `NodeDefinition` object.
- **Backwards compatibility**: Keep `NodeDefinition` class available but deprecated. Keep `from_node_def_and_config()` as deprecated alias.

**Files to modify**:
- `src/madsci_common/madsci/common/types/node_types.py` (NodeInfo, NodeDefinition, NodeConfig)
- `src/madsci_node_module/madsci/node_module/abstract_node_module.py` (update info generation)
- `src/madsci_client/madsci/client/cli/commands/` (new `node info` subcommand, or extend existing)

#### G.6 Deprecation timeline and migration path [S]

Document the full deprecation timeline for auto-written files:
- **v0.7.x (current)**: Auto-writing deprecated, emits warnings. `update_node_files` default flipped to `False`. `madsci config export` available as replacement.
- **v0.8.0**: Auto-writing removed. `NodeDefinition` files no longer loaded by default. Managers require explicit configuration (settings/env vars or generated config files).
- Publish migration guide: "From auto-generated definitions to explicit configuration"

**Files to create/modify**:
- `docs/guides/migration_from_definitions.md`
- Update deprecation messages in `src/madsci_common/madsci/common/deprecation.py`

**Done when**:
- `model_dump()` and `to_yaml()` redact secrets by default; `model_dump_safe(include_secrets=True)` reveals them
- No `SecretStr` values leak in logs, API responses, or exported config files
- `madsci config export` produces valid configuration with secrets redacted (unless `--include-secrets` is passed)
- `madsci config create manager <type>` generates a working configuration file
- Managers no longer auto-write definition files on startup
- Nodes no longer auto-write `*.node.yaml` / `*.info.yaml` by default
- NodeInfo is decoupled from NodeDefinition; `/info` endpoint response format is unchanged
- Migration guide is published and deprecation warnings are active

---

## Priority & Sequencing

```
Phase A (Foundation) [S-M]  --> Phase B (CLI Commands) [L] --> Phase C (Templates) [L]
                                   |
                                   v
                           Phase G.1 (Secrets) [M] --> G.4 (config CLI) [M]
                                   |
                                   v
                           Phase D (TUI) [L] --> Phase E (Integration) [XL]
                                                        |
                                                        |   (per-manager: E.2 before G.2)
                                                        v
                                                G.2-G.3 (Remove auto-write) [M]
                                                        |
                                                        v
                                                G.5 (NodeInfo redesign) [L]
                                                        |
                                                        v
                                                Phase F (Pure Python) [XXL]
```

**Note**: E.1 (validate migration tool against example_lab) can run independently after Phase A is complete. G.2-G.3 depend on E.2 on a per-manager basis: each manager must complete registry integration (E.2) before its auto-writing is removed (G.2).

**Tier 1 (Must Have)**: A, B.1-B.3 (start/stop/init), G.1 (secret classification)
**Tier 2 (Should Have)**: B.4-B.7 (validate/run/completion/backup), C.0-C.2 (generator decision + module & interface templates), D.1-D.2 (Trogon + auto-refresh), G.2-G.4 (remove auto-writing + config CLI), E.1 (validate migration tool against example_lab)
**Tier 3 (Nice to Have)**: C.3-C.5 (lab templates, template validation, comm pattern templates), D.3-D.5 (advanced TUI screens), G.5-G.6 (NodeInfo redesign + migration docs)
**Tier 4 (Stretch)**: E.2-E.3 (manager integration/settings consolidation), F (pure Python mode), extended start/stop (manager/node/local mode)

### Size Legend

| Size | Rough Scope |
|------|-------------|
| S | Single file or small change, < 1 day |
| M | A few files, clear scope, 1-3 days |
| L | Multiple files, some design decisions, 3-5 days |
| XL | Cross-cutting, significant design work, 1-2 weeks |
| XXL | Architectural change, multiple XL tasks, 2+ weeks |

---

## Verification

After each phase:
1. Run full test suite: `pytest` (all 2004+ tests pass)
2. Run linter: `ruff check` (zero violations)
3. Run formatter: `ruff format --check` (zero violations)
4. Run pre-commit checks: `just checks` (all pass — this runs the full pre-commit suite)
5. Run E2E tutorials: `pytest tests/e2e/` (all tutorial YAMLs pass)
6. Run template validation: Verify all templates render and pass syntax/lint checks
7. Manual smoke test: `madsci doctor`, `madsci version`, `madsci new module --no-interactive`

**Automation**: These 7 steps should be consolidated into a single `just verify-ux` target in the `justfile` so they can be run with one command locally and in CI. The target should fail fast on the first error. Note that `just checks` (`.justfile:35-36`) already runs `pre-commit run --all-files` which includes ruff, so steps 2-4 may be redundant if pre-commit is configured correctly — but it's worth keeping them explicit for clarity.

**CI/CD**: As new CLI commands land (Phase B), add them to the CI smoke test matrix. At minimum, every new command should have a `--help` invocation test in CI to catch import errors and broken lazy loading.

---

## Cross-Cutting Concerns

These apply across all phases and should be addressed incrementally as features land, not deferred to a single documentation sprint at the end.

### Documentation Updates

Each phase that adds user-facing functionality must include corresponding documentation:

- **CLI commands (Phase B)**: Update `docs/guides/` with usage examples for each new command. Add each command to the CLI reference section.
- **Templates (Phase C)**: Add a template catalog page listing all available templates with descriptions, use cases, and example invocations.
- **TUI (Phase D)**: Update the TUI user guide with screenshots and keyboard shortcut reference for new screens.
- **README**: Update the top-level README's "Quick Start" section once `madsci init`, `madsci start`, and `madsci stop` are available — these fundamentally change the onboarding flow.
- **Getting Started tutorial**: Rewrite or supplement existing tutorial to use the new CLI commands instead of manual `docker compose` / `python -m` invocations.

### Changelog & Migration Guide

- Maintain a running changelog (CHANGELOG.md or equivalent) as features land
- Before releasing a version that includes Phase E (manager migration), publish a **migration guide** for existing users covering:
  - What changed in configuration format
  - How to run `madsci migrate` against their lab
  - Backwards compatibility guarantees and deprecation timeline

### Cross-Platform Considerations

Phase F (Pure Python Mode) is motivated by "lowering the barrier to entry, especially on Windows." However, earlier phases should avoid creating obstacles for that future work:

- **Phase B**: `madsci start`/`stop` use `subprocess` to call `docker compose`. This is cross-platform as long as Docker Desktop is available. Avoid shell-specific features (e.g., don't shell out to `bash`, use `subprocess.run()` with list args).
- **Phase C**: Templates should generate code that works on all platforms. Avoid Unix-specific paths in generated `Dockerfile.j2` or scripts.
- **Phase F**: This is where Windows-specific concerns become critical (no SIGINT on Windows, different path separators, no `shutil.which` behavior differences, etc.). Design B.1/B.2 with clean interfaces so that Phase F can swap in a local-mode backend without rewriting the CLI layer.

### Security & Secret Handling

Phase G introduces a proper secret classification system. Until G.1 lands, the following interim rules apply:
- **Phase B**: `madsci config export` (if added before G.1) must NOT export any settings without the pattern-matching redaction from `get_settings_export()`
- **Phase E**: Manager migration must not inadvertently expose secrets in migrated config files
- **All phases**: Never write secrets to files by default. Any command that writes configuration must redact sensitive fields unless `--include-secrets` is explicitly passed.

### CI/CD Integration

- **Phase A**: Add `just verify-ux` target to CI pipeline
- **Phase B**: Add `--help` smoke tests for all new commands to CI matrix
- **Phase C**: Add template render + syntax check to CI (ensure new templates don't break on future PRs)
- **Phase D**: Add Textual snapshot tests (if feasible) or at minimum import/launch tests for new screens
- **Phase G**: Add tests verifying that `model_dump()` and `to_yaml()` never leak `SecretStr` values; add CI check that no new `password`/`token`/`key` fields are added without `SecretStr` or `secret` metadata

---

## Key Files Reference

| Area | Location |
|------|----------|
| CLI commands | `src/madsci_client/madsci/client/cli/commands/` |
| CLI lazy loading | `src/madsci_client/madsci/client/cli/__init__.py` |
| TUI screens | `src/madsci_client/madsci/client/cli/tui/screens/` |
| Bundled templates | `src/madsci_common/madsci/common/bundled_templates/` |
| Template engine | `src/madsci_common/madsci/common/templates/engine.py` |
| Template registry | `src/madsci_common/madsci/common/templates/registry.py` |
| ID Registry | `src/madsci_common/madsci/common/registry/` |
| Migration tools | `src/madsci_common/madsci/common/migration/` |
| Manager base class | `src/madsci_common/madsci/common/manager_base.py` |
| Node module base | `src/madsci_node_module/madsci/node_module/abstract_node_module.py` |
| Node/Manager types | `src/madsci_common/madsci/common/types/node_types.py`, `manager_types.py` |
| Base model types | `src/madsci_common/madsci/common/types/base_types.py` |
| Deprecation system | `src/madsci_common/madsci/common/deprecation.py` |
| Backup tools | `src/madsci_common/madsci/common/backup_tools/` |
| Docker Compose | `compose.yaml` |
| Example lab | `example_lab/` |
| Justfile (dev tasks) | `.justfile` |
| Design docs | `docs/designs/` |
| CLI design | `docs/designs/cli_design.md` |
| TUI design | `docs/designs/tui_design.md` |
| Original plan | `docs/guides/ux_overhaul_plan.md` |
| Progress tracker | `docs/guides/ux_overhaul_progress.md` |
