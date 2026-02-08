# MADSci UX Overhaul - Implementation Progress

**Status**: In Progress
**Started**: 2026-02-07
**Last Updated**: 2026-02-10

This document tracks the implementation progress of the [MADSci UX Overhaul Plan](./ux_overhaul_plan.md).

---

## Phase Summary

| Phase | Name | Status | Progress |
|-------|------|--------|----------|
| 0 | Validation Infrastructure | ✅ Complete | 100% |
| 1 | CLI Scaffold + Core Infrastructure | 🔲 Not Started | 0% |
| 2 | Definition System Refactor | 🔲 Not Started | 0% |
| 3 | Scaffolding & Templates | 🔲 Not Started | 0% |
| 4 | ExperimentApplication Modalities | 🔲 Not Started | 0% |
| 5 | Documentation & Guides | 🔲 Not Started | 0% |
| 6 | Polish & Integration | 🔲 Not Started | 0% |

---

## Phase 0: Validation Infrastructure ✅

**Goal**: Build the testing/validation framework that validates everything else.

### Deliverables

#### 0.1 E2E Test Harness for Examples/Guides ✅

**Status**: Complete

**Location**: `src/madsci_common/madsci/common/testing/`

**Components Implemented**:

| File | Description | Status |
|------|-------------|--------|
| `types.py` | Pydantic models for test definitions, steps, validations, and results | ✅ Complete |
| `validators.py` | 14 validator implementations for various validation types | ✅ Complete |
| `runner.py` | E2ETestRunner class for executing test definitions | ✅ Complete |
| `template_validator.py` | TemplateValidator class for validating templates | ✅ Complete |
| `__init__.py` | Module exports | ✅ Complete |

**Validation Types Supported**:
- `exit_code` - Validate command exit codes
- `file_exists` / `file_not_exists` - Check file existence
- `directory_exists` - Check directory existence
- `file_contains` - Check file content (plain text or regex)
- `output_contains` / `output_not_contains` - Check command output
- `regex_match` - Regex matching on output
- `http_health` / `http_status` - HTTP endpoint validation
- `json_contains` / `json_field` - JSON output validation
- `python_syntax` - Validate Python file syntax
- `ruff_check` - Lint validation with ruff

**Test Modes**:
- Pure Python mode (no Docker required)
- Docker mode (for full integration tests)
- Hybrid mode (some services in Docker)

**Features**:
- Background process support with health check waits
- Automatic cleanup of files and processes
- Skip conditions for conditional test execution
- Continue-on-error for non-critical steps
- Log capture to files for debugging
- Rich console output with progress indicators

#### 0.2 Template Validation System ✅

**Status**: Complete

**Location**: `src/madsci_common/madsci/common/testing/template_validator.py`

**Features**:
- Template manifest validation (`template.yaml`)
- Generated Python file syntax checking
- Ruff linting of generated code
- Optional import testing
- Batch validation of all templates in a directory
- Rich table output for validation results

**Note**: The `TemplateEngine` class referenced by the validator is planned for Phase 3. The validator gracefully falls back to basic validation when the engine is not available.

#### 0.3 CI Integration ✅

**Status**: Complete

**Location**: `.github/workflows/validation.yml`

**Workflow Jobs**:
1. **E2E Framework Tests**: Unit tests for the testing framework itself
2. **Tutorial Tests**: Runs tutorial YAML test definitions
3. **Template Validation**: Validates all project templates

**Features**:
- Runs on push and pull request
- Clear pass/fail status reporting
- Fast feedback loop

### Tests

**Location**: `src/madsci_common/tests/testing/`

| File | Tests | Status |
|------|-------|--------|
| `test_validators.py` | 29 tests for all validator types | ✅ Passing |
| `test_runner.py` | 14 tests for E2ETestRunner | ✅ Passing |

**Total**: 43 tests, all passing

### E2E Test Infrastructure

**Location**: `tests/e2e/`

| File | Purpose |
|------|--------|
| `conftest.py` | Pytest configuration with custom options |
| `test_tutorials.py` | Pytest integration for running tutorial YAML definitions |
| `tutorials/basic_test.tutorial.yaml` | Example tutorial test definition |

### Code Quality

- All code passes `ruff check` with no warnings
- Full docstrings on all public classes and methods
- Type hints throughout
- Proper handling of subprocess security patterns with documented `noqa` comments

### Research Completed

**Location**: `docs/guides/e2e_test_harness_research.md`

**Decision**: Built custom framework optimized for MADSci's specific needs:
- YAML-based test definitions (human-readable, version-controllable)
- Pluggable validator system (extensible for future needs)
- Pure Python mode first (fast feedback without Docker overhead)
- Integration with pytest for CI compatibility

---

## Phase 1: CLI Scaffold + Core Infrastructure 🔲

**Status**: Not Started

**Prerequisites**: Phase 0 (Complete ✅)

### Planned Deliverables

- [ ] 1.1 Unified `madsci` CLI Entry Point
- [ ] 1.2 Core Commands (`version`, `doctor`, `status`, `logs`)
- [ ] 1.3 TUI Foundation (Textual)
- [ ] 1.4 User Configuration Infrastructure

---

## Phase 2: Definition System Refactor 🔲

**Status**: Not Started

**Prerequisites**: Phase 1

### Planned Deliverables

- [ ] 2.1 Template System
- [ ] 2.2 ID Registry
- [ ] 2.3 Settings Consolidation
- [ ] 2.4 Migration Tool
- [ ] 2.5 Deprecation Layer

---

## Phase 3: Scaffolding & Templates 🔲

**Status**: Not Started

**Prerequisites**: Phase 2, Phase 0

### Planned Deliverables

- [ ] 3.1 `madsci new` Command Family (`module`, `interface`, `node`, `experiment`, `workflow`, `lab`)
- [ ] 3.2 Interactive Wizards (TUI) - Module Wizard with interface variant selection
- [ ] 3.3 Template Library (module templates, interface templates, communication patterns)
- [ ] 3.4 Generated Code Quality
- [ ] 3.5 Fake/Simulation Interface Infrastructure

---

## Phase 4: ExperimentApplication Modalities 🔲

**Status**: Not Started

**Prerequisites**: Phase 3

### Planned Deliverables

- [ ] 4.1 Base Class Extraction
- [ ] 4.2 Modality Implementations (Script, Notebook, TUI, Node)
- [ ] 4.3 Migration of Existing Experiments

---

## Phase 5: Documentation & Guides 🔲

**Status**: Not Started

**Prerequisites**: Phases 1-4

### Planned Deliverables

- [ ] Updated documentation for new CLI
- [ ] Persona-based guides (Lab Operator, Equipment Integrator, Experimentalist)
- [ ] Tutorial sequences validated by Phase 0 infrastructure
- [ ] Example updates

---

## Phase 6: Polish & Integration 🔲

**Status**: Not Started

**Prerequisites**: Phases 1-5

### Planned Deliverables

- [ ] End-to-end user journey testing
- [ ] Performance optimization
- [ ] Error message improvements
- [ ] Final documentation review

---

## Design Documents

The following design documents were created during Phase 0 planning:

| Document | Location | Description |
|----------|----------|-------------|
| UX Overhaul Plan | `docs/guides/ux_overhaul_plan.md` | Master plan for the UX overhaul |
| E2E Test Harness Research | `docs/guides/e2e_test_harness_research.md` | Research on E2E testing approaches |
| CLI Design | `docs/designs/cli_design.md` | Detailed CLI command structure |
| TUI Design | `docs/designs/tui_design.md` | TUI screens and navigation |
| Template System Design | `docs/designs/template_system_design.md` | Template architecture |
| ID Registry Design | `docs/designs/id_registry_design.md` | ID registry implementation |
| Settings Consolidation Design | `docs/designs/settings_consolidation_design.md` | Settings system refactor |
| Migration Tool Design | `docs/designs/migration_tool_design.md` | Definition file migration |

---

## Changelog

### 2026-02-10

- **Review Feedback Incorporated**: Comprehensive review feedback synthesized and applied across all documents
  - Added concrete deprecation timeline: deprecated in v0.7.0, removed in v0.8.0
  - TUI phased delivery: MVP in Phase 1, full features in later phases
  - Multi-workcell support added to ID Registry design
  - Air-gapped environment support added to Template System
  - Docker-compose migration safety improvements (ruamel.yaml, validation, rollback)
  - OTEL integration notes added across CLI, TUI, and ID Registry designs
  - Documentation URL corrected to https://ad-sdl.github.io/MADSci/
  - Added `madsci run workflow` convenience command
  - Windows compatibility requirements clarified (filelock, pathlib)
  - Schema export capability added to Settings Consolidation
  - Step timeout support added to E2E test harness
  - ExperimentCampaign design notes expanded

### 2026-02-09

- **Plan Updated**: Added Node vs. Module distinction throughout the UX Overhaul Plan
  - New "Equipment Integrator Workflow" section documenting 8-step module development journey
  - Updated CLI commands: `madsci new module`, `madsci new interface`
  - New Phase 3.5: Fake/Simulation Interface Infrastructure
  - Full module structure with `foo_types.py` pattern
  - Updated glossary with Node, Module, Interface definitions
- **Design Documents Updated**: All 6 design documents updated to align with module-first approach
  - CLI Design: Updated scaffolding commands
  - Template System: Added module/interface templates
  - TUI Design: Replaced Node Wizard with Module Wizard
  - ID Registry: Added module registration support
  - Settings Consolidation: Added ModuleSettings and foo_types.py pattern
  - Migration Tool: Added module migration commands

### 2026-02-08

- **Phase 0 Complete**: All validation infrastructure implemented and tested
  - E2E test harness with 14 validator types
  - Template validator with syntax and lint checking
  - 43 passing tests
  - CI workflow for automated validation
  - Code refactored to pass all ruff linting checks

### 2026-02-07

- **Project Started**: UX Overhaul Plan created
- **Phase 0 Started**: Initial implementation of E2E test harness
