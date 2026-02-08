# MADSci UX Overhaul Plan

**Status**: Active Development
**Created**: 2026-02-07
**Last Updated**: 2026-02-07

## Executive Summary

This document outlines a comprehensive plan to make MADSci more user-friendly and approachable for domain scientists who are not software engineers. The core principle is **progressive disclosure** - users should be able to start simple and add complexity as needed, rather than being confronted with the full distributed systems architecture upfront.

## Problem Statement

### Current Challenges

1. **Steep learning curve**: Users must understand Docker, REST APIs, multiple manager services, YAML configuration, and distributed systems concepts before they can do anything useful.

2. **All-or-nothing onboarding**: The example lab starts 15+ services; there's no way to start small.

3. **Configuration complexity**: Definition files conflate three concerns (templates, ID persistence, runtime config) and require manual YAML editing.

4. **No unified tooling**: Managers are started via `python -m ...`; there's no central CLI for common operations.

5. **Limited experiment modalities**: `ExperimentApplication` assumes workflow-based experiments with optional server mode, but scientists work in scripts, notebooks, and interactive sessions.

### Target Users

MADSci serves a bimodal distribution:
- **Internal**: RPL team building systems *for* scientists
- **External**: Independent researchers (biologists, chemists, materials scientists) bootstrapping their own labs, typically individuals or small teams (2-3 people)

### User Personas ("Hats")

| Persona | Role | Primary Needs |
|---------|------|---------------|
| **Lab Operator** | Runs and maintains the SDL | System health, troubleshooting, backups, updates |
| **Equipment Integrator** | Develops modules for instruments | Module scaffolding, interface development, testing without hardware, debugging |
| **Experimentalist** | Runs day-to-day experiments | Experiment creation, data access, workflow management |

Often one person wears 2-3 hats.

#### Equipment Integrator Workflow

The Equipment Integrator has the most complex journey, involving both software development and hardware interaction:

1. **Scaffold module**: `madsci new module --name my_instrument --template device`
2. **Develop interface**: Implement `my_instrument_interface.py` with hardware communication logic
3. **Create fake interface**: Implement `my_instrument_fake_interface.py` for testing without hardware
4. **Test interface standalone**: Use interface directly in Jupyter notebook or pytest
5. **Wire up node**: Configure `my_instrument_rest_node.py` to use interface
6. **Test node locally**: Run node with fake interface, verify actions work
7. **Test with hardware**: Switch to real interface, validate against actual instrument
8. **Package and deploy**: Build Docker image, add to lab configuration

**Key friction points to address**:
- Hardware-in-the-loop testing is slow and requires physical presence
- No standard pattern for fake/simulated interfaces
- Interface development often happens outside MADSci context (just Python + hardware)
- Debugging node issues vs. interface issues is confusing

## Success Criteria

> A scientist can go from zero to a fully functional basic self-driving lab in an afternoon, with a clear understanding of how to integrate new equipment, run experiments, and manage data - purely by reading documentation, following guides, using tools, and looking at examples, without needing to contact the MADSci team.

## Design Principle: Ladder of Complexity

```
Rung 5: Full distributed lab (Docker, multiple hosts, OTEL, etc.)
Rung 4: Local multi-service lab (Docker compose, all managers)
Rung 3: Single workcell + essential managers (minimal Docker or pure Python)
Rung 2: Single node + experiment script (pure Python, no services)
Rung 1: Interactive exploration (TUI, notebooks)
```

Each rung is:
- **Self-contained**: Works without understanding higher rungs
- **Documented separately**: Guides for each persona at each level
- **Scaffolded**: `madsci new ...` generates working starting points
- **Upgradeable**: Clear path to the next rung when ready

---

## Phase 0: Validation Infrastructure

**Goal**: Build the testing/validation framework that validates everything else.

**Rationale**: Without automated validation, we can't be confident the "happy path" actually works. This infrastructure prevents regressions as we refactor and serves as living documentation.

### Deliverables

#### 0.1 E2E Test Harness for Examples/Guides
- Framework to run a sequence of steps and validate outcomes
- Support for "pure Python" mode and Docker mode
- Captures logs, screenshots (for TUI), outputs for debugging
- Clear pass/fail reporting with actionable error messages

#### 0.2 Template Validation System
- Given a template, instantiate it with test values
- Verify the result is valid (parses, runs, passes linting)
- Integrated with `madsci new` command

#### 0.3 CI Integration
- GitHub Actions workflow that runs all validations
- Matrix testing across Python versions and platforms
- Clear reporting of what's broken

### Research Required
- Evaluate existing E2E frameworks: pytest-bdd, Robot Framework, pytest-docker, testinfra, etc.
- Determine best fit for our mixed Python/Docker/CLI testing needs

### Success Metrics
- All existing examples have automated validation
- CI runs validation on every PR
- < 5 minute feedback loop for validation failures

---

## Phase 1: CLI Scaffold + Core Infrastructure

**Goal**: Establish the unified `madsci` command and TUI foundation.

**Rationale**: The CLI is the primary interface for all user personas. Building it first (with features that don't depend on the definition refactor) provides immediate value while we design the new configuration system.

### Deliverables

#### 1.1 Unified `madsci` CLI Entry Point
- Click-based command group in `madsci_client` package
- Subcommand structure: `madsci <command> [subcommand]`
- Rich help system with examples
- Shell completion support

#### 1.2 Core Commands (No Config Dependency)

```
madsci version            # Version info for all installed packages
madsci doctor             # System diagnostics
                          #   - Docker availability and version
                          #   - Python version and venv status
                          #   - Port availability
                          #   - Required dependencies
                          #   - Network connectivity
madsci status             # Query running services
                          #   - Hit health endpoints
                          #   - Show service versions
                          #   - Display connection info
madsci logs               # Aggregate/tail logs from services
                          #   - Filter by service, level, time
                          #   - Follow mode (-f)
```

#### 1.3 TUI Foundation (Textual)
- Basic app shell with navigation
- Service status dashboard (real-time health)
- Log viewer with filtering
- Foundation for future screens (wizards, resource browser, etc.)

#### 1.4 User Configuration Infrastructure
- `MadsciUserConfig` class for CLI-level preferences
- `~/.madsci/config.toml` for user settings
- Foundation for ID registry (design finalized, implementation started)

### CLI Command Structure (Full Vision)

```
madsci
├── version                 # Version info
├── doctor                  # System diagnostics
├── status                  # Service status
├── logs                    # Log aggregation
├── init                    # Interactive lab setup wizard
├── new                     # Scaffolding
│   ├── module              # Create new node module (full repository)
│   ├── interface           # Add interface to existing module
│   ├── node                # Create node server (for existing interface)
│   ├── experiment          # Create new experiment
│   ├── workflow            # Create new workflow
│   ├── workcell            # Create new workcell
│   └── lab                 # Create new lab configuration
├── start                   # Start services
│   ├── lab                 # Start full lab
│   ├── manager <name>      # Start specific manager
│   └── node <name>         # Start specific node
├── stop                    # Stop services
├── validate                # Validate configuration
├── migrate                 # Migration tools
├── registry                # ID registry management
│   ├── list                # List registered components
│   ├── resolve <name>      # Resolve name to ID
│   └── clean               # Remove stale entries
├── backup                  # Database backup (existing)
└── tui                     # Launch interactive TUI
```

### Dependencies
- Phase 0 (validation harness validates CLI works)

### Success Metrics
- `madsci doctor` successfully diagnoses common setup issues
- `madsci status` shows health of running services
- TUI provides functional status dashboard

---

## Phase 2: Definition System Refactor

**Goal**: Replace definition files with cleaner separation of concerns.

**Rationale**: Current definition files conflate three distinct purposes:
1. **Templates**: Patterns for generating new components
2. **ID Persistence**: Reliable name-to-ID mapping across restarts
3. **Configuration**: Runtime settings for services

Separating these makes each easier to understand and maintain.

### Deliverables

#### 2.1 Template System
- `Template` base class with Jinja2 rendering
- Template registry (bundled + user-defined)
- Template validation before instantiation
- Template versioning for upgrades

```python
class NodeTemplate(Template):
    """Template for generating node modules."""
    template_id: str
    template_version: str
    parameters: list[TemplateParameter]
    files: list[TemplateFile]  # Jinja2 templates to render

    def instantiate(self, values: dict) -> GeneratedProject:
        """Generate a new node project from this template."""
        ...
```

#### 2.2 ID Registry

**Design Requirements**:
- Tie node/manager names to IDs reliably
- Work standalone (single machine, no services) and lab-wide (distributed)
- Persist across restarts
- Handle name/ID conflicts gracefully
- Cross-platform (Windows, macOS, Linux)
- Work in Docker and bare metal

**Proposed Architecture**:

```
┌─────────────────────────────────────────────────────────────────┐
│                        ID Resolution Flow                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Component Startup                                               │
│       │                                                          │
│       ▼                                                          │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐  │
│  │ Local       │ -> │ Lab         │ -> │ Generate New        │  │
│  │ Registry    │    │ Registry    │    │ ID (ULID)           │  │
│  │ (~/.madsci/ │    │ (if avail)  │    │                     │  │
│  │ registry)   │    │             │    │                     │  │
│  └─────────────┘    └─────────────┘    └─────────────────────┘  │
│       │                   │                     │                │
│       └───────────────────┴─────────────────────┘                │
│                           │                                      │
│                           ▼                                      │
│                   ┌───────────────┐                              │
│                   │ Heartbeat     │                              │
│                   │ + Lock        │                              │
│                   └───────────────┘                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Local Registry** (`~/.madsci/registry.json`):
```json
{
  "version": 1,
  "entries": {
    "liquidhandler_1": {
      "id": "01JYFEHVSV20D60Z88RVERJ75N",
      "component_type": "node",
      "created_at": "2026-02-07T10:00:00Z",
      "last_seen": "2026-02-07T15:30:00Z",
      "lock": {
        "holder_pid": 12345,
        "holder_host": "lab-workstation-1",
        "acquired_at": "2026-02-07T15:30:00Z",
        "heartbeat_at": "2026-02-07T15:30:05Z"
      }
    }
  }
}
```

**Conflict Resolution**:
1. Check local registry for name
2. If found and lock is stale (no heartbeat > 30s), claim it
3. If found and lock is active, fail with clear error message
4. If lab server available, check lab registry (source of truth for distributed)
5. If not found anywhere, generate new ULID

**CLI Commands**:
```
madsci registry list                # Show all registered components
madsci registry resolve <name>      # Get ID for name
madsci registry clean               # Remove stale entries
madsci registry export              # Export for backup/sharing
madsci registry import <file>       # Import from backup
```

#### 2.3 Settings Consolidation

**Current State**:
- `*ManagerSettings` classes handle runtime config (URLs, ports, etc.)
- `*ManagerDefinition` classes handle identity + some structure
- Overlap and confusion between the two

**New State**:
- `*Settings` classes handle ALL configuration (runtime + identity reference)
- ID comes from registry (by name) not from definition file
- Structural config (list of nodes in workcell) moves to Settings or registry

```python
# Before
class WorkcellManagerSettings(ManagerSettings):
    manager_definition: PathLike = "workcell.manager.yaml"  # Points to definition
    server_url: AnyUrl = "http://localhost:8005"

class WorkcellManagerDefinition(ManagerDefinition):
    name: str
    manager_id: str  # Duplicated identity concern
    nodes: dict[str, AnyUrl]  # Structural config mixed in

# After
class WorkcellManagerSettings(ManagerSettings):
    name: str = "my_workcell"  # Name for registry lookup
    server_url: AnyUrl = "http://localhost:8005"
    nodes: dict[str, AnyUrl] = {}  # Structural config in settings
    # ID is resolved via registry from name
```

#### 2.4 Migration Tool

**Approach**: Incremental with finalize

```
madsci migrate scan                 # Find old definition files
madsci migrate convert <path>       # Convert one file (dry-run by default)
madsci migrate convert <path> --apply  # Actually convert
madsci migrate all --dry-run        # Preview full migration
madsci migrate all --apply          # Run full migration
madsci migrate finalize             # Remove deprecated files, update imports
```

**Migration Steps**:
1. Scan for `*.manager.yaml`, `*.node.yaml` files
2. Extract IDs and register in local registry
3. Generate new Settings-based configuration
4. Emit deprecation warnings for old pattern usage
5. Provide rollback capability

#### 2.5 Deprecation Layer
- Old definition loading still works but emits warnings
- Clear timeline: deprecated in X.Y, removed in X.Z
- Migration guide in documentation

### Dependencies
- Phase 1 (CLI infrastructure for migration commands)

### Success Metrics
- All example_lab configurations migrated to new format
- Zero definition files in new projects
- Migration tool handles 100% of existing definition patterns

---

## Phase 3: Scaffolding & Templates

**Goal**: `madsci new` generates working starting points for modules, nodes, experiments, and other components.

**Rationale**: Users should never copy-paste and edit to create new components. Scaffolding ensures correct structure and reduces errors.

### Key Concept: Node vs. Module

A critical distinction that affects scaffolding:

- **Node**: The runtime server that the workcell communicates with (`*_rest_node.py`). Executes actions and reports state.
- **Module**: A complete package (typically a git repository) containing everything needed to control an instrument:
  - Node server (`foo_rest_node.py`)
  - Interface(s) (`foo_interface.py`, `foo_fake_interface.py`, `foo_sim_interface.py`)
  - Driver/communication layer (serial, socket, REST, SDK wrappers)
  - Resource templates (labware definitions, etc.)
  - Configuration and settings
  - Dockerfile and dependencies
  - Documentation and examples
  - Tests (unit, integration, hardware-in-the-loop)

**Production Module Structure** (based on pf400_module, ot2_module, inheco_incubator_module):
```
foo_module/
├── src/
│   ├── foo_rest_node.py           # MADSci node server
│   ├── foo_types.py               # Settings, Pydantic models, data types
│   ├── foo_interface/             # Interface package (or foo_interface.py)
│   │   ├── __init__.py
│   │   ├── foo.py                 # Main interface class
│   │   ├── foo_constants.py       # Device constants/enums
│   │   ├── foo_errors.py          # Custom exceptions
│   │   └── foo_driver.py          # Low-level communication
│   ├── foo_fake_interface.py      # Simulated interface (no hardware)
│   └── foo_sim_interface.py       # Simulation interface (e.g., Omniverse)
├── tests/
│   ├── test_interface.py          # Interface unit tests
│   ├── test_node.py               # Node unit tests
│   └── test_integration.py        # Integration tests
├── resources/
│   └── templates/                 # Resource templates (labware, etc.)
├── docs/
│   └── README.md                  # Module documentation
├── Dockerfile
├── pyproject.toml
├── .env.example
└── README.md
```

### Deliverables

#### 3.1 `madsci new` Command Family

```
madsci new module [--name NAME] [--template TEMPLATE]  # Full module repository
madsci new interface [--name NAME] [--type TYPE]       # Interface class only
madsci new node [--name NAME] [--interface INTERFACE]  # Node server only
madsci new experiment [--name NAME] [--modality MODALITY]
madsci new workflow [--name NAME] [--template TEMPLATE]
madsci new workcell [--name NAME]
madsci new lab [--name NAME] [--template TEMPLATE]
```

All commands support:
- `--interactive` / `-i`: Launch TUI wizard (default if no options)
- `--output` / `-o`: Output directory
- `--dry-run`: Preview what would be generated

**Usage Patterns**:

1. **New instrument integration** (most common): `madsci new module --name pipette`
   - Creates complete repository structure with interface, node, tests, Docker, etc.

2. **Add interface variant**: `madsci new interface --name pipette --type fake`
   - Adds `pipette_fake_interface.py` to existing module

3. **Quick node for existing interface**: `madsci new node --name pipette --interface pipette_interface`
   - Creates just the node server, assuming interface already exists

#### 3.2 Interactive Wizards (TUI)

- Step-by-step prompts with sensible defaults
- Real-time validation of inputs
- Preview of generated files before writing
- Help text and examples inline

**Example: `madsci new module -i`**
```
┌─────────────────────────────────────────────────────────────┐
│                  Create New Node Module                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Module name: [my_pipette________]                          │
│                                                             │
│  Description: [Automated pipetting system_______]           │
│                                                             │
│  Device type: ○ Device (physical instruments)               │
│               ● Compute (data processing)                   │
│               ○ Human (manual operations)                   │
│                                                             │
│  Template:    ● Basic (minimal starting point)              │
│               ○ Device (init/shutdown/status actions)       │
│               ○ Instrument (measure/calibrate actions)      │
│               ○ Liquid Handler (aspirate/dispense/etc.)     │
│               ○ Robot Arm (pick/place/move)                 │
│                                                             │
│  Interface variants to include:                             │
│    [x] Real (hardware communication)                        │
│    [x] Fake (simulated, no hardware)                        │
│    [ ] Sim (external simulator, e.g., Omniverse)            │
│                                                             │
│  Include:     [x] Dockerfile                                │
│               [x] Tests                                     │
│               [x] Documentation                             │
│               [x] GitHub Actions CI                         │
│                                                             │
│  [Preview]  [Create]  [Cancel]                              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 3.3 Template Library

**Module Templates** (complete repository):
| Template | Description | Interface Pattern | Actions Included |
|----------|-------------|-------------------|------------------|
| `basic` | Minimal module | Single file | One example action |
| `device` | Standard device | Package with driver | `initialize`, `shutdown`, `status`, `reset` |
| `instrument` | Measurement device | Package with calibration | `measure`, `calibrate`, `get_reading` |
| `liquid_handler` | Pipetting system | Package with deck model | `aspirate`, `dispense`, `transfer`, `pick_up_tips` |
| `robot_arm` | Material handling | Package with kinematics | `pick`, `place`, `move`, `home` |
| `camera` | Vision system | Package with capture | `capture`, `stream`, `configure` |

**Interface Templates** (add to existing module):
| Template | Description | Use Case |
|----------|-------------|----------|
| `real` | Hardware communication | Production use |
| `fake` | In-memory simulation | Testing without hardware |
| `sim` | External simulator connection | Omniverse, Gazebo, etc. |
| `mock` | Pytest mock wrapper | Unit testing |

**Interface Communication Patterns**:
| Pattern | Description | Examples |
|---------|-------------|----------|
| `serial` | Serial/USB communication | Arduino, many lab instruments |
| `socket` | TCP/IP socket | PF400, industrial robots |
| `rest` | REST API wrapper | OT-2, cloud instruments |
| `sdk` | Vendor SDK wrapper | Proprietary instruments |
| `modbus` | Modbus protocol | Industrial equipment |

**Experiment Templates**:
| Template | Modality | Description |
|----------|----------|-------------|
| `script` | ExperimentScript | Simple run-once experiment |
| `notebook` | ExperimentNotebook | Jupyter-friendly cells |
| `tui` | ExperimentTUI | Interactive terminal UI |
| `node` | ExperimentNode | REST API server mode |

**Lab Templates**:
| Template | Description | Includes |
|----------|-------------|----------|
| `minimal` | Smallest viable lab | 1 node, in-memory managers |
| `standard` | Standard lab | All managers, Docker compose |
| `distributed` | Multi-host lab | Docker swarm/k8s configs |

#### 3.4 Generated Code Quality

**For all generated code**:
- Helpful comments explaining each section
- Links to relevant documentation
- Type hints throughout
- Passes linting (ruff) out of the box
- Working immediately (validated by Phase 0 infrastructure)

**For modules specifically**:
- Interface is independent of MADSci (can be used in notebooks)
- Fake interface works identically to real interface
- Clear separation between interface logic and node wiring
- Tests use fake interface by default (no hardware required)
- Docker build works out of the box
- Types module (`foo_types.py`) centralizes all data definitions:
  - `FooNodeConfig` (node settings, inherits from `RestNodeConfig`)
  - `FooInterfaceConfig` (interface-specific settings)
  - Device-specific Pydantic models (commands, responses, states)
  - Enums for device modes, states, error codes
  - Type aliases for clarity

#### 3.5 Fake/Simulation Interface Infrastructure

**Goal**: Every module template includes a fake interface that enables:
- Development without hardware
- CI testing without hardware
- Demo/training environments
- Debugging workflow logic before hardware integration

**Design Pattern**:
```python
# foo_types.py - Centralized type definitions
from pydantic import BaseModel
from madsci.node_module import RestNodeConfig

class FooNodeConfig(RestNodeConfig):
    """Node-level configuration."""
    interface_type: Literal["real", "fake", "sim"] = "real"
    port: str = "/dev/ttyUSB0"
    timeout: float = 30.0

class FooInterfaceConfig(BaseModel):
    """Interface-specific configuration."""
    baud_rate: int = 9600
    retry_count: int = 3

class FooCommand(BaseModel):
    """Command sent to device."""
    action: str
    parameters: dict[str, Any] = {}

class FooResult(BaseModel):
    """Result from device action."""
    success: bool
    data: Any = None
    error_code: int | None = None

# foo_interface.py - Abstract base or protocol
from foo_types import FooInterfaceConfig, FooCommand, FooResult

class FooInterfaceBase(Protocol):
    """Protocol defining the interface contract."""
    def connect(self) -> None: ...
    def disconnect(self) -> None: ...
    def do_action(self, cmd: FooCommand) -> FooResult: ...

# foo_real_interface.py - Hardware implementation
from foo_types import FooInterfaceConfig, FooCommand, FooResult

class FooRealInterface:
    """Real hardware communication."""
    def __init__(self, config: FooInterfaceConfig, port: str = "/dev/ttyUSB0"):
        self.config = config
        self.connection = SerialConnection(port, baud_rate=config.baud_rate)

    def do_action(self, cmd: FooCommand) -> FooResult:
        self.connection.send(f"{cmd.action} {cmd.parameters}")
        return FooResult(**self.connection.read_response())

# foo_fake_interface.py - Simulated implementation
from foo_types import FooInterfaceConfig, FooCommand, FooResult

class FooFakeInterface:
    """In-memory simulation for testing."""
    def __init__(self, config: FooInterfaceConfig, latency: float = 0.1):
        self.config = config
        self.latency = latency
        self.state: dict = {}

    def do_action(self, cmd: FooCommand) -> FooResult:
        time.sleep(self.latency)  # Simulate real timing
        self.state["last_action"] = cmd.action
        return FooResult(success=True, data=cmd.parameters)

# foo_rest_node.py - Node uses interface via dependency injection
from foo_types import FooNodeConfig, FooInterfaceConfig
from foo_real_interface import FooRealInterface
from foo_fake_interface import FooFakeInterface

class FooNode(RestNode):
    config: FooNodeConfig = FooNodeConfig()
    config_model = FooNodeConfig
    interface: FooInterfaceBase

    def startup_handler(self) -> None:
        interface_config = FooInterfaceConfig()
        if self.config.interface_type == "real":
            self.interface = FooRealInterface(interface_config, self.config.port)
        elif self.config.interface_type == "fake":
            self.interface = FooFakeInterface(interface_config)
        # etc.
```

**Benefits**:
- Same node code works with any interface variant
- Switch interfaces via config/environment variable
- Tests automatically use fake interface
- Gradual transition from fake to real during development

### Success Metrics
- All module templates generate valid, runnable code with working fake interfaces
- < 15 minutes from `madsci new module` to running node with fake interface
- < 30 minutes to first successful action call (using fake interface)
- 100% of generated code passes linting
- All tests in generated modules pass without hardware
- Clear path from fake interface testing to hardware integration

### Dependencies
- Phase 2 (templates use new settings/registry system)
- Phase 0 (templates are validated)

---

## Phase 4: ExperimentApplication Modalities

**Goal**: Support different experiment execution contexts explicitly.

**Rationale**: Scientists work in different contexts: quick scripts, interactive notebooks, long-running campaigns. The experiment infrastructure should adapt to each.

### Deliverables

#### 4.1 Base Class Extraction

```python
# Current (problematic)
class ExperimentApplication(RestNode):
    """Inherits from RestNode even when server mode isn't needed."""
    ...

# New (composition over inheritance)
class ExperimentBase:
    """Core experiment lifecycle management."""
    experiment_design: ExperimentDesign
    clients: MadsciClientMixin  # Composition, not inheritance

    def start_experiment_run(self, ...):
        ...

    def end_experiment(self, ...):
        ...

    @contextmanager
    def manage_experiment(self, ...):
        ...
```

#### 4.2 Modality Implementations

**ExperimentScript** (simplest)
```python
class MyExperiment(ExperimentScript):
    experiment_design = ExperimentDesign(name="My Experiment")

    def run(self):
        with self.manage_experiment():
            result = self.workcell.start_workflow("my_workflow.yaml")
            return result

if __name__ == "__main__":
    MyExperiment().run()
```

**ExperimentNotebook** (Jupyter-friendly)
```python
class MyExperiment(ExperimentNotebook):
    experiment_design = ExperimentDesign(name="My Experiment")

# In notebook cells:
exp = MyExperiment()
exp.start()  # Starts experiment, displays status widget

result = exp.run_workflow("my_workflow.yaml")  # Shows progress
exp.display(result)  # Rich display of results

exp.end()  # Ends experiment, shows summary
```

**ExperimentTUI** (interactive terminal)
```python
class MyExperiment(ExperimentTUI):
    experiment_design = ExperimentDesign(name="My Experiment")

    def build_ui(self) -> Screen:
        # Define Textual UI for experiment control
        ...

if __name__ == "__main__":
    MyExperiment().run_tui()
```

**ExperimentNode** (server mode, current behavior)
```python
class MyExperiment(ExperimentNode):
    experiment_design = ExperimentDesign(name="My Experiment")
    config = ExperimentNodeConfig(server_mode=True, port=6000)

    def run_experiment(self, param1: str, param2: int) -> dict:
        # Called via REST API
        ...

if __name__ == "__main__":
    MyExperiment().start_server()
```

#### 4.3 Future: ExperimentCampaign

```python
class MyOptimization(ExperimentCampaign):
    """Long-running iterative experiment with decision points."""
    experiment_design = ExperimentDesign(name="Parameter Optimization")

    def get_next_parameters(self, history: list[ExperimentResult]) -> dict:
        # AI/ML-driven parameter selection
        ...

    def run_iteration(self, params: dict) -> ExperimentResult:
        # Single iteration
        ...

    def should_continue(self, history: list[ExperimentResult]) -> bool:
        # Stopping criteria
        ...
```

#### 4.4 Template Integration

`madsci new experiment` prompts for modality and generates appropriate template.

### Dependencies
- Phase 3 (templates reference new modalities)

### Success Metrics
- Each modality has working template
- Migration guide for existing ExperimentApplication users
- Notebooks work without server mode complexity

---

## Phase 5: Example Lab Transformation

**Goal**: Transform example_lab into guides + templates.

**Rationale**: The example lab should demonstrate the happy path, not be a monolithic artifact to reverse-engineer.

### Deliverables

#### 5.1 Restructured Documentation

**By Rung (progressive complexity)**:
1. `docs/tutorials/01-exploration.md` - Using the TUI, understanding concepts
2. `docs/tutorials/02-first-node.md` - Single node, no services
3. `docs/tutorials/03-first-experiment.md` - Node + experiment script
4. `docs/tutorials/04-first-workcell.md` - Multiple nodes, minimal managers
5. `docs/tutorials/05-full-lab.md` - Complete lab with Docker

**By Persona**:
- `docs/guides/operator/` - Lab operation, monitoring, backup, troubleshooting
- `docs/guides/integrator/` - Node development, testing, debugging
- `docs/guides/experimentalist/` - Running experiments, accessing data

#### 5.2 Example Extraction

- Example modules become templates in template library
- Example interfaces demonstrate the real/fake pattern
- Example workflows become templates
- Example experiments become templates
- `example_lab/` becomes "generated from templates" reference

#### 5.3 Equipment Integrator Guide

A dedicated guide for the Equipment Integrator persona covering the full module development lifecycle:

```
docs/guides/integrator/
├── 01-understanding-modules.md      # Node vs Module vs Interface concepts
├── 02-creating-a-module.md          # madsci new module walkthrough
├── 03-developing-interfaces.md      # Interface patterns, driver communication
├── 04-fake-interfaces.md            # Creating testable fake implementations
├── 05-wiring-the-node.md            # Connecting interface to node server
├── 06-testing-strategies.md         # Unit, integration, hardware-in-the-loop
├── 07-debugging.md                  # Common issues, logging, troubleshooting
├── 08-packaging-deployment.md       # Docker, dependencies, CI/CD
└── 09-publishing.md                 # Sharing modules, versioning
```

**Key documentation principles**:
- Interface development is independent of MADSci (show Jupyter examples)
- Fake interfaces enable full development without hardware
- Clear separation of concerns: driver → interface → node → workcell
- Testing pyramid: most tests use fake interface, few need hardware

#### 5.4 Tutorial Automation

```yaml
# tutorial-02-first-module.yaml
name: "First Module Tutorial"
steps:
  - name: "Create module"
    command: "madsci new module --name my_sensor --template instrument --output ."
    validate:
      - directory_exists: "my_sensor_module"
      - file_exists: "my_sensor_module/src/my_sensor_rest_node.py"
      - file_exists: "my_sensor_module/src/my_sensor_interface.py"
      - file_exists: "my_sensor_module/src/my_sensor_fake_interface.py"
      - file_contains: "my_sensor_module/src/my_sensor_rest_node.py": "class MySensorNode"

  - name: "Run tests with fake interface"
    command: "pytest my_sensor_module/tests/"
    validate:
      - exit_code: 0

  - name: "Start node with fake interface"
    command: "python my_sensor_module/src/my_sensor_rest_node.py --interface-type fake &"
    background: true
    validate:
      - http_health: "http://localhost:2000/health"

  - name: "Query node info"
    command: "curl http://localhost:2000/info"
    validate:
      - json_contains: {"module_name": "my_sensor"}

  - name: "Execute action"
    command: 'curl -X POST http://localhost:2000/actions/measure -H "Content-Type: application/json" -d "{}"'
    validate:
      - json_field: "action_response": "succeeded"
```

#### 5.5 Minimal Viable Lab (Pure Python)

- No Docker required
- In-memory or SQLite-backed managers
- Single-process mode option
- Full functionality for development/testing

### Dependencies
- Phase 4 (tutorials use new experiment modalities)
- Phase 0 (tutorials are validated in CI)

### Success Metrics
- New user completes first module tutorial in < 45 minutes (with fake interface)
- All tutorials pass automated validation
- Zero Docker required for tutorials 01-03
- Equipment Integrator can develop and test module without hardware access
- Clear documentation path from "I have a new instrument" to "It works in my lab"

---

## Phase 6: Pure Python Mode (Stretch)

**Goal**: Run full MADSci stack without Docker.

**Rationale**: Docker is a barrier for many scientists. A pure Python mode dramatically lowers the entry barrier and improves development experience.

### Deliverables

#### 6.1 In-Memory/SQLite Manager Backends

- SQLite adapter for PostgreSQL managers (Resource Manager)
- In-memory adapter for MongoDB managers (Event, Experiment, Workcell, Data)
- SQLite-based queue as Redis alternative

#### 6.2 Single-Process Mode

```bash
madsci start --mode=local  # Everything in one process
madsci start --mode=hybrid  # Some local, some Docker
madsci start --mode=docker  # Full Docker (current behavior)
```

#### 6.3 Manager Abstraction Layer

```python
class StorageBackend(Protocol):
    async def get(self, key: str) -> Any: ...
    async def set(self, key: str, value: Any) -> None: ...
    async def query(self, filter: dict) -> list[Any]: ...

class SQLiteBackend(StorageBackend): ...
class MongoDBBackend(StorageBackend): ...
class PostgreSQLBackend(StorageBackend): ...
```

### Dependencies
- All previous phases
- May require significant manager refactoring

### Success Metrics
- Full lab runs in single Python process
- All tests pass in both Docker and pure Python mode
- < 1 second startup time in pure Python mode

---

## Implementation Timeline

```
Week 1-2:   Phase 0 - Validation Infrastructure
Week 3-4:   Phase 1 - CLI Scaffold + TUI Foundation
Week 5-6:   Phase 2 - Definition System Refactor (design + ID registry)
Week 7-8:   Phase 2 - Settings consolidation + Migration tool
Week 9-10:  Phase 3 - Scaffolding & Templates
Week 11-12: Phase 4 - Experiment Modalities
Week 13-14: Phase 5 - Example Lab Transformation
Week 15+:   Phase 6 - Pure Python Mode (stretch)
```

*Timeline is approximate and will be adjusted based on findings.*

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Breaking existing production labs | Migration tool with dry-run, deprecation warnings, rollback support |
| Scope creep | Clear phase boundaries, MVP for each deliverable |
| TUI complexity | Start minimal, iterate based on feedback |
| Pure Python mode intractable | Treat as stretch goal, fail fast if blockers found |
| Template maintenance burden | Automated validation catches template breakage |
| Module complexity overwhelming | Progressive disclosure: basic template first, advanced patterns documented |
| Fake interface fidelity | Document limitations clearly, provide timing simulation helpers |
| External module repos diverge | Provide migration CLI, template versioning, compatibility checks |

---

## Design Decisions

The following decisions have been made based on review:

1. **Template storage**: Templates will be bundled in the monorepo alongside the packages they support. This keeps templates in sync with code changes and simplifies versioning.

2. **TUI framework**: Use Textual as the primary TUI framework, with Trogon integration for auto-generating command forms from Click commands. Trogon will be used for the command palette feature, while custom Textual screens will handle specialized interfaces (dashboard, logs, wizards).

3. **Registry service**: The ID Registry API will be part of the Lab Manager (Squid), not a separate service. This reduces operational complexity while still providing distributed coordination.

4. **Notebook integration**: Start with Rich display (simpler, works in more environments). IPywidgets integration can be added later if there's demand for interactive progress widgets.

5. **Windows support**: **Critical priority.** Many laboratory instruments only work on Windows. All features must work on Windows, and Docker Desktop issues should be documented with workarounds. Pure Python mode (Phase 6) is especially important for Windows users.

---

## Appendix A: Current Architecture Reference

### Manager Services
| Service | Port | Database | Purpose |
|---------|------|----------|--------|
| Lab Manager (Squid) | 8000 | - | Central configuration, dashboard |
| Event Manager | 8001 | MongoDB | Event logging |
| Experiment Manager | 8002 | MongoDB | Experiment lifecycle |
| Resource Manager | 8003 | PostgreSQL | Resource/inventory |
| Data Manager | 8004 | MongoDB + MinIO | Data storage |
| Workcell Manager | 8005 | MongoDB + Redis | Workflow orchestration |
| Location Manager | 8006 | MongoDB | Location management |

### Current Definition Types
- `*ManagerDefinition` - Manager identity and structure
- `NodeDefinition` - Node identity
- `WorkflowDefinition` - Workflow steps and parameters
- `ActionDefinition` - Node action signatures (generated)

---

## Appendix B: Glossary

| Term | Definition |
|------|------------|
| **SDL** | Self-Driving Laboratory |
| **Node** | A running instance of a Node Module - the REST server that the workcell communicates with to execute actions on an instrument |
| **Node Module** | A complete package (typically a git repository) containing everything needed to control an instrument: node server, interface(s), drivers, documentation, tests, Dockerfile, and dependencies |
| **Interface** | A class that encapsulates all logic for communicating with hardware (or a simulation), independent of MADSci. Can be used standalone in notebooks or scripts |
| **Workcell** | Collection of nodes that work together |
| **Workflow** | Sequence of steps executed on nodes |
| **Manager** | Service that coordinates a specific concern |
| **Definition** | (Deprecated) YAML file describing component identity |
| **Template** | (New) Pattern for generating new components |
| **Registry** | Name-to-ID mapping for persistent identity |
