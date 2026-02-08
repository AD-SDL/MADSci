# MADSci CLI Design Document

**Status**: Draft
**Date**: 2026-02-07
**Last Updated**: 2026-02-08
**Author**: Claude (AI Assistant)

## Overview

This document defines the design for the unified `madsci` command-line interface. The CLI serves as the primary "concierge" for all MADSci operations, providing a consistent, discoverable interface for users across all three personas (Operator, Integrator, Experimentalist).

## Design Principles

1. **Progressive Disclosure**: Simple commands for common tasks, advanced options available but not required
2. **Consistency**: All commands follow the same patterns for options, output, and error handling
3. **Discoverability**: Comprehensive help, examples, and tab completion
4. **Composability**: Commands can be chained and scripted
5. **Feedback**: Clear progress indicators, success/failure messages, and actionable errors

## Technical Foundation

### Framework Selection

| Component | Choice | Rationale |
|-----------|--------|----------|
| CLI Framework | **Click** | Already a dependency, mature, pytest-friendly |
| TUI Integration | **Trogon** | Already a dependency, generates TUI from Click commands |
| Interactive TUI | **Textual** | Modern async TUI framework, same ecosystem as Trogon |
| Output Formatting | **Rich** | Already a dependency, beautiful terminal output |
| Configuration | **Pydantic Settings** | Consistent with existing MADSci patterns |

### Package Location

The CLI will be implemented in `madsci_client` package:
- Entry point: `madsci.client.cli:main`
- Location: `src/madsci_client/madsci/client/cli/`

```
src/madsci_client/madsci/client/cli/
├── __init__.py           # Main CLI entry point, command group
├── commands/
│   ├── __init__.py
│   ├── version.py        # Version information
│   ├── doctor.py         # System diagnostics
│   ├── status.py         # Service status
│   ├── logs.py           # Log aggregation
│   ├── new.py            # Scaffolding commands
│   ├── start.py          # Service management
│   ├── stop.py           # Service management
│   ├── init.py           # Lab initialization wizard
│   ├── validate.py       # Configuration validation
│   ├── migrate.py        # Migration tools
│   ├── registry.py       # ID registry management
│   └── backup.py         # Re-export existing backup commands
├── tui/
│   ├── __init__.py
│   ├── app.py            # Main Textual app
│   ├── screens/          # TUI screens
│   └── widgets/          # Custom widgets
└── utils/
    ├── __init__.py
    ├── config.py         # CLI configuration
    ├── output.py         # Formatted output helpers
    └── context.py        # Click context helpers
```

---

## Command Structure

### Top-Level Commands

```
madsci
├── version                 # Show version information
├── doctor                  # System diagnostics
├── status                  # Service status
├── logs                    # Log viewing/aggregation
├── init                    # Interactive lab setup
├── new                     # Scaffolding (subcommands)
│   ├── lab
│   ├── node
│   ├── experiment
│   ├── workflow
│   └── workcell
├── start                   # Start services (subcommands)
│   ├── lab
│   ├── manager
│   └── node
├── stop                    # Stop services
├── validate                # Validate configuration
├── migrate                 # Migration tools (subcommands)
│   ├── scan
│   ├── convert
│   └── finalize
├── registry                # ID registry (subcommands)
│   ├── list
│   ├── resolve
│   ├── rename
│   ├── clean
│   ├── export
│   └── import
├── backup                  # Database backup (existing)
├── export                  # Export settings/state (subcommands)
│   ├── settings            # Export component settings
│   └── state               # Export runtime state (future)
├── run                     # Run workflows/experiments (subcommands)
│   ├── workflow            # Run a workflow
│   └── experiment          # Run an experiment
├── tui                     # Launch interactive TUI
└── completion              # Shell completion scripts
```

---

## Command Specifications

### Global Options

All commands support these global options:

```
--config, -c PATH      Configuration file path
--lab-url URL          Lab manager URL (default: http://localhost:8000)
--verbose, -v          Increase verbosity (can be repeated: -vv, -vvv)
--quiet, -q            Suppress non-essential output
--no-color             Disable colored output
--json                  Output in JSON format (where applicable)
--help                  Show help message
```

### Version Command

```bash
madsci version [OPTIONS]
```

**Options:**
- `--json` - Output as JSON
- `--check-updates` - Check for available updates

**Output:**
```
MADSci v0.2.0-beta

Installed packages:
  madsci_common      0.2.0-beta
  madsci_client      0.2.0-beta
  madsci_squid       0.2.0-beta
  madsci_node_module 0.2.0-beta
  ...

Python: 3.12.1
Platform: macOS 14.0 (arm64)
```

---

### Doctor Command

```bash
madsci doctor [OPTIONS]
```

Performs comprehensive system diagnostics.

**Options:**
- `--fix` - Attempt to fix detected issues
- `--check CATEGORY` - Only run specific checks (docker, python, ports, network)

**Checks Performed:**

1. **Python Environment**
   - Python version (3.10+ required)
   - Virtual environment detection
   - Required packages installed

2. **Docker Environment**
   - Docker installed and running
   - Docker Compose version (v2.0+ required)
   - Docker resource allocation (memory, disk)

3. **Port Availability**
   - Check ports 2000-2004, 5432, 6379, 8000-8006, 9000-9001, 27017
   - Identify conflicting processes

4. **Network Connectivity**
   - Local service connectivity
   - Lab server reachability (if configured)

5. **Configuration**
   - Valid configuration files
   - Environment variables set
   - Registry accessibility

6. **Observability (if configured)**
   - OpenTelemetry exporter connectivity
   - OTEL collector reachability
   - Trace/metric export status

**Output:**
```
MADSci System Diagnostics
=========================

✓ Python 3.12.1 (required: ≥3.10)
✓ Virtual environment active
✓ All required packages installed

✓ Docker 24.0.7 running
✓ Docker Compose v2.23.0 (required: ≥2.0)
✓ Docker resources: 8GB RAM, 50GB disk

✓ Port 8000 available (lab_manager)
✓ Port 8001 available (event_manager)
✗ Port 8005 in use by process 'node' (PID 12345)
  → Run: kill 12345

✓ Network: localhost reachable
✗ Lab server http://localhost:8000 not responding
  → Start lab with: madsci start lab

Summary: 2 issues found
  Run 'madsci doctor --fix' to attempt automatic fixes
```

---

### Status Command

```bash
madsci status [OPTIONS] [SERVICES...]
```

Show status of MADSci services.

**Arguments:**
- `SERVICES` - Specific services to check (optional, defaults to all)

**Options:**
- `--watch, -w` - Continuously update status
- `--interval SECONDS` - Watch interval (default: 5)
- `--json` - Output as JSON

**Output:**
```
MADSci Service Status
=====================

Managers:
  ✓ lab_manager         http://localhost:8000   healthy   v0.2.0
  ✓ event_manager       http://localhost:8001   healthy   v0.2.0
  ✓ experiment_manager  http://localhost:8002   healthy   v0.2.0
  ✓ resource_manager    http://localhost:8003   healthy   v0.2.0
  ✓ data_manager        http://localhost:8004   healthy   v0.2.0
  ✓ workcell_manager    http://localhost:8005   healthy   v0.2.0
  ✓ location_manager    http://localhost:8006   healthy   v0.2.0

Nodes:
  ✓ liquidhandler_1     http://localhost:2000   idle      v0.0.1
  ✓ liquidhandler_2     http://localhost:2001   busy      v0.0.1
  ○ platereader_1       http://localhost:2003   offline   -

Infrastructure:
  ✓ MongoDB             localhost:27017         connected
  ✓ PostgreSQL          localhost:5432          connected
  ✓ Redis               localhost:6379          connected
  ✓ MinIO               localhost:9000          connected

Last updated: 2026-02-07 15:30:45
```

---

### Logs Command

```bash
madsci logs [OPTIONS] [SERVICES...]
```

View and aggregate logs from MADSci services.

**Arguments:**
- `SERVICES` - Specific services to show logs from

**Options:**
- `--follow, -f` - Follow log output
- `--tail LINES` - Show last N lines (default: 100)
- `--since DURATION` - Show logs since duration (e.g., "5m", "1h")
- `--level LEVEL` - Minimum log level (debug, info, warning, error)
- `--grep PATTERN` - Filter logs by pattern
- `--timestamps` - Show timestamps
- `--no-color` - Disable colored output

**Examples:**
```bash
# Follow all logs
madsci logs -f

# Show last 50 lines from workcell_manager
madsci logs workcell_manager --tail 50

# Show errors from the last hour
madsci logs --since 1h --level error

# Filter for workflow-related logs
madsci logs --grep "workflow"
```

---

### Init Command

```bash
madsci init [OPTIONS] [DIRECTORY]
```

Interactive lab initialization wizard.

**Arguments:**
- `DIRECTORY` - Target directory (default: current directory)

**Options:**
- `--template TEMPLATE` - Use specific lab template
- `--name NAME` - Lab name
- `--non-interactive` - Use defaults, don't prompt

**Interactive Flow:**
```
┌─────────────────────────────────────────────────────────────────┐
│                    MADSci Lab Initialization                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Welcome! Let's set up your MADSci lab.                         │
│                                                                  │
│  Lab name: [My Research Lab_______]                             │
│                                                                  │
│  Description: [Automated chemistry lab for synthesis_]          │
│                                                                  │
│  Lab template:                                                   │
│    ● minimal  - Single node, no Docker required                 │
│    ○ standard - All managers, Docker Compose                    │
│    ○ distributed - Multi-host deployment                        │
│                                                                  │
│  [Next]  [Cancel]                                               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Output:**
```
Creating lab "My Research Lab" in ./my-research-lab/

  ✓ Created configuration files
  ✓ Created docker-compose.yaml
  ✓ Created .env file
  ✓ Initialized ID registry
  ✓ Created example node
  ✓ Created example workflow

Next steps:
  1. cd my-research-lab
  2. madsci start lab
  3. Open http://localhost:8000 in your browser

For more information, run:
  madsci --help
```

---

### New Command Group

```bash
madsci new <TYPE> [OPTIONS]
```

Scaffolding for creating new MADSci components.

#### `madsci new lab`

```bash
madsci new lab [OPTIONS] [DIRECTORY]
```

**Options:**
- `--name NAME` - Lab name
- `--template TEMPLATE` - Lab template (minimal, standard, distributed)
- `--no-interactive` - Skip prompts, use defaults

#### `madsci new module`

```bash
madsci new module [OPTIONS] [DIRECTORY]
```

Creates a complete module repository with node, interface(s), types, tests, and documentation.

**Options:**
- `--name NAME` - Module name (required if non-interactive)
- `--type TYPE` - Node type (device, compute, human)
- `--template TEMPLATE` - Module template (basic, device, instrument, liquid_handler, robot_arm, camera)
- `--interface INTERFACE` - Interface communication pattern (serial, socket, rest, sdk)
- `--include-fake` - Include fake interface for testing (default: true)
- `--port PORT` - Default port number
- `--no-interactive` - Skip prompts, use defaults

**Interactive Flow:**
```
┌─────────────────────────────────────────────────────────────────┐
│                     Create New Module                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Module name: [my_pipette__________]                            │
│                                                                  │
│  Node type:                                                      │
│    ● device   - Physical instruments and robots                 │
│    ○ compute  - Data processing nodes                           │
│    ○ human    - Manual operation steps                          │
│                                                                  │
│  Template:                                                       │
│    ○ basic         - Minimal module with one action             │
│    ● device        - Standard device lifecycle                  │
│    ○ instrument    - Measurement device                         │
│    ○ liquid_handler - Pipetting operations                      │
│                                                                  │
│  Interface type:                                                 │
│    ○ serial   - Serial/USB communication                        │
│    ● socket   - TCP/IP socket                                   │
│    ○ rest     - REST API wrapper                                │
│    ○ sdk      - Vendor SDK integration                          │
│                                                                  │
│  Include interfaces:                                             │
│    ☑ Real interface (hardware communication)                    │
│    ☑ Fake interface (testing without hardware)                  │
│    ☐ Simulation interface (Omniverse/physics sim)               │
│                                                                  │
│  Port: [2000]                                                    │
│                                                                  │
│  [Preview]  [Create]  [Cancel]                                  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Output:**
```
Creating module "my_pipette" from template "device"...

  ✓ Created my_pipette_module/
  ✓ Created my_pipette_module/src/my_pipette_rest_node.py
  ✓ Created my_pipette_module/src/my_pipette_interface.py
  ✓ Created my_pipette_module/src/my_pipette_fake_interface.py
  ✓ Created my_pipette_module/src/my_pipette_types.py
  ✓ Created my_pipette_module/tests/
  ✓ Created my_pipette_module/tests/test_my_pipette_node.py
  ✓ Created my_pipette_module/tests/test_my_pipette_interface.py
  ✓ Created my_pipette_module/Dockerfile
  ✓ Created my_pipette_module/pyproject.toml
  ✓ Created my_pipette_module/README.md

Next steps:
  1. cd my_pipette_module
  2. Implement my_pipette_interface.py for your hardware
  3. python src/my_pipette_rest_node.py --fake  # Test with fake interface
  4. python src/my_pipette_rest_node.py  # Run with real hardware
  5. curl http://localhost:2000/health  # Verify it's running

Documentation:
  https://ad-sdl.github.io/MADSci/guides/integrator/modules
```

#### `madsci new interface`

```bash
madsci new interface [OPTIONS] [MODULE_PATH]
```

Add a new interface variant to an existing module.

**Arguments:**
- `MODULE_PATH` - Path to existing module (default: current directory)

**Options:**
- `--type TYPE` - Interface type (fake, sim, mock)
- `--name NAME` - Custom interface name
- `--no-interactive` - Skip prompts, use defaults

**Output:**
```
Adding fake interface to my_pipette_module...

  ✓ Created src/my_pipette_fake_interface.py
  ✓ Updated src/my_pipette_types.py (added FakeInterfaceConfig)
  ✓ Created tests/test_my_pipette_fake_interface.py
  ✓ Updated README.md (documented fake interface)

Next steps:
  1. Implement fake behavior in my_pipette_fake_interface.py
  2. Run tests: pytest tests/test_my_pipette_fake_interface.py
  3. Use fake interface: python src/my_pipette_rest_node.py --fake
```

#### `madsci new node`

```bash
madsci new node [OPTIONS] [DIRECTORY]
```

Creates just the node server when an interface already exists (rare use case).

**Options:**
- `--name NAME` - Node name
- `--interface-module MODULE` - Python module path for existing interface
- `--port PORT` - Default port number
- `--no-interactive` - Skip prompts, use defaults

**Note:** Most users should use `madsci new module` instead, which creates the complete package including node, interface, and types.

#### `madsci new experiment`

```bash
madsci new experiment [OPTIONS] [DIRECTORY]
```

**Options:**
- `--name NAME` - Experiment name
- `--modality MODALITY` - Experiment modality (script, notebook, tui, node)
- `--template TEMPLATE` - Experiment template
- `--no-interactive` - Skip prompts

#### `madsci new workflow`

```bash
madsci new workflow [OPTIONS] [DIRECTORY]
```

**Options:**
- `--name NAME` - Workflow name
- `--template TEMPLATE` - Workflow template
- `--no-interactive` - Skip prompts

#### `madsci new workcell`

```bash
madsci new workcell [OPTIONS] [DIRECTORY]
```

**Options:**
- `--name NAME` - Workcell name
- `--nodes NODES` - Comma-separated list of nodes to include
- `--no-interactive` - Skip prompts

---

### Start Command Group

```bash
madsci start <TARGET> [OPTIONS]
```

Start MADSci services.

#### `madsci start lab`

```bash
madsci start lab [OPTIONS]
```

**Options:**
- `--mode MODE` - Startup mode (docker, local, hybrid)
- `--detach, -d` - Run in background
- `--build` - Rebuild Docker images before starting
- `--services SERVICES` - Start only specific services
- `--no-infra` - Don't start infrastructure (databases, etc.)

**Examples:**
```bash
# Start full lab with Docker
madsci start lab

# Start in background
madsci start lab -d

# Start only managers (no nodes)
madsci start lab --services managers

# Start in pure Python mode (no Docker)
madsci start lab --mode local
```

#### `madsci start manager`

```bash
madsci start manager <NAME> [OPTIONS]
```

**Arguments:**
- `NAME` - Manager name (event, experiment, resource, data, workcell, location, lab)

**Options:**
- `--port PORT` - Override default port
- `--mode MODE` - docker or local
- `--detach, -d` - Run in background

#### `madsci start node`

```bash
madsci start node <NAME|PATH> [OPTIONS]
```

**Arguments:**
- `NAME|PATH` - Node name (from registry) or path to node module

**Options:**
- `--port PORT` - Override default port
- `--detach, -d` - Run in background

---

### Stop Command

```bash
madsci stop [OPTIONS] [SERVICES...]
```

Stop MADSci services.

**Arguments:**
- `SERVICES` - Specific services to stop (default: all)

**Options:**
- `--remove` - Remove containers (for Docker mode)
- `--volumes` - Also remove volumes (data loss warning!)
- `--force` - Force stop without graceful shutdown

---

### Validate Command

```bash
madsci validate [OPTIONS] [PATHS...]
```

Validate MADSci configuration files.

**Arguments:**
- `PATHS` - Specific files/directories to validate (default: current directory)

**Options:**
- `--fix` - Attempt to fix issues automatically
- `--strict` - Fail on warnings

**Output:**
```
Validating MADSci configuration...

  ✓ managers/example_lab.manager.yaml - valid
  ✓ managers/example_workcell.manager.yaml - valid
  ⚠ node_definitions/liquidhandler_1.node.yaml
      Line 5: deprecated field 'node_type', use 'type' instead
  ✗ workflows/broken.workflow.yaml
      Line 12: unknown step type 'invalid_step'
      Line 15: missing required field 'node'

Summary: 2 valid, 1 warning, 1 error
```

---

### Migrate Command Group

```bash
madsci migrate <SUBCOMMAND> [OPTIONS]
```

Tools for migrating from old configuration formats.

#### `madsci migrate scan`

```bash
madsci migrate scan [OPTIONS] [DIRECTORY]
```

Scan for files that need migration.

**Options:**
- `--json` - Output as JSON

**Output:**
```
Scanning for deprecated configuration files...

Found 12 files requiring migration:

  Definition files (to be converted to Settings + Registry):
    ✗ managers/example_lab.manager.yaml
    ✗ managers/example_workcell.manager.yaml
    ✗ node_definitions/liquidhandler_1.node.yaml
    ✗ node_definitions/platereader_1.node.yaml
    ...

Run 'madsci migrate convert --all' to convert all files.
Run 'madsci migrate convert <path>' to convert individual files.
```

#### `madsci migrate convert`

```bash
madsci migrate convert [OPTIONS] [PATHS...]
```

Convert files to new format.

**Arguments:**
- `PATHS` - Files to convert (or use --all)

**Options:**
- `--all` - Convert all detected files
- `--dry-run` - Show what would be done without making changes
- `--backup` - Create backup before converting (default: true)
- `--force` - Overwrite existing converted files

#### `madsci migrate finalize`

```bash
madsci migrate finalize [OPTIONS]
```

Finalize migration by removing deprecated files.

**Options:**
- `--dry-run` - Show what would be deleted
- `--keep-backups` - Keep backup files

---

### Registry Command Group

```bash
madsci registry <SUBCOMMAND> [OPTIONS]
```

Manage the component ID registry.

#### `madsci registry list`

```bash
madsci registry list [OPTIONS]
```

**Options:**
- `--type TYPE` - Filter by component type (node, manager)
- `--json` - Output as JSON

**Output:**
```
MADSci Component Registry
=========================

Managers:
  lab_manager           01JK7069E1EVFT4SA5M0VQT35G   active   lab-workstation
  workcell_manager      01JK706A23XYZFT4SA5M0VQT35H   active   lab-workstation
  event_manager         01JK706B34ABCFT4SA5M0VQT35I   active   lab-workstation

Nodes:
  liquidhandler_1       01JYFEHVSV20D60Z88RVERJ75N   active   lab-workstation
  liquidhandler_2       01JYFEI123456D60Z88RVERJ75P   idle     robot-pc-1
  platereader_1         01JYFEJ789012D60Z88RVERJ75Q   stale    -

Total: 6 entries (5 active, 1 stale)
```

#### `madsci registry resolve`

```bash
madsci registry resolve <NAME>
```

Resolve a component name to its ID.

**Output:**
```
liquidhandler_1 → 01JYFEHVSV20D60Z88RVERJ75N
```

#### `madsci registry rename`

```bash
madsci registry rename <OLD_NAME> <NEW_NAME>
```

Rename a component in the registry.

**Arguments:**
- `OLD_NAME` - Current component name
- `NEW_NAME` - New component name

**Options:**
- `--force` - Rename even if currently locked (steal lock)

**Output:**
```
Renamed: liquidhandler_1 → liquid_handler_1
ID: 01JYFEHVSV20D60Z88RVERJ75N (unchanged)
```

#### `madsci registry clean`

```bash
madsci registry clean [OPTIONS]
```

Remove stale entries from the registry.

**Options:**
- `--older-than DURATION` - Remove entries older than duration (default: 7d)
- `--dry-run` - Show what would be removed
- `--force` - Don't prompt for confirmation

#### `madsci registry export`

```bash
madsci registry export [OPTIONS] [OUTPUT]
```

Export registry to a file.

**Arguments:**
- `OUTPUT` - Output file path (default: stdout)

**Options:**
- `--format FORMAT` - Export format (json, yaml)

#### `madsci registry import`

```bash
madsci registry import [OPTIONS] <INPUT>
```

Import registry from a file.

**Arguments:**
- `INPUT` - Input file path

**Options:**
- `--merge` - Merge with existing registry (default: replace)
- `--dry-run` - Show what would be imported

---

### Run Command Group

```bash
madsci run <TYPE> [OPTIONS]
```

Convenience commands for running workflows and experiments.

#### `madsci run workflow`

```bash
madsci run workflow <NAME|PATH> [OPTIONS]
```

Run a workflow on the workcell.

**Arguments:**
- `NAME|PATH` - Workflow name (from workcell) or path to workflow YAML file

**Options:**
- `--workcell URL` - Workcell manager URL (default: from config)
- `--parameters JSON` - Workflow parameters as JSON string
- `--parameters-file PATH` - Path to parameters JSON/YAML file
- `--wait` - Wait for workflow to complete (default: true)
- `--no-wait` - Submit and return immediately
- `--timeout SECONDS` - Timeout for workflow completion

**Examples:**
```bash
# Run workflow by name
madsci run workflow sample_transfer

# Run workflow with parameters
madsci run workflow sample_transfer --parameters '{"source": "plate_1", "dest": "plate_2"}'

# Run workflow from file
madsci run workflow ./workflows/my_workflow.yaml

# Submit without waiting
madsci run workflow long_experiment --no-wait
```

#### `madsci run experiment`

```bash
madsci run experiment <NAME|PATH> [OPTIONS]
```

Run an experiment.

**Arguments:**
- `NAME|PATH` - Experiment name or path to experiment script

**Options:**
- `--parameters JSON` - Experiment parameters as JSON string
- `--campaign` - Run as part of a campaign (creates campaign if needed)

---

### TUI Command

```bash
madsci tui [OPTIONS]
```

Launch interactive terminal user interface.

**Options:**
- `--screen SCREEN` - Start on specific screen (status, logs, nodes, workflows)

This launches the full Textual-based TUI application (detailed in the TUI design document).

---

### Completion Command

```bash
madsci completion <SHELL>
```

Generate shell completion scripts.

**Arguments:**
- `SHELL` - Shell type (bash, zsh, fish)

**Usage:**
```bash
# For bash
eval "$(madsci completion bash)"

# For zsh
eval "$(madsci completion zsh)"

# Or add to shell config:
madsci completion bash >> ~/.bashrc
```

---

## Implementation Details

### Entry Point Registration

```toml
# In src/madsci_client/pyproject.toml
[project.scripts]
madsci = "madsci.client.cli:main"
```

### Main CLI Structure

```python
# src/madsci_client/madsci/client/cli/__init__.py
import click
from rich.console import Console

from .commands import (
    version, doctor, status, logs, init,
    new, start, stop, validate, migrate, registry, tui, completion
)
from .utils.config import MadsciCLIConfig

console = Console()

@click.group()
@click.option('-c', '--config', type=click.Path(), help='Configuration file')
@click.option('--lab-url', envvar='MADSCI_LAB_URL', default='http://localhost:8000/')
@click.option('-v', '--verbose', count=True, help='Increase verbosity')
@click.option('-q', '--quiet', is_flag=True, help='Suppress non-essential output')
@click.option('--no-color', is_flag=True, help='Disable colored output')
@click.option('--json', 'json_output', is_flag=True, help='Output as JSON')
@click.version_option()
@click.pass_context
def madsci(ctx, config, lab_url, verbose, quiet, no_color, json_output):
    """MADSci - Modular Autonomous Discovery for Science.

    A comprehensive toolkit for building and operating self-driving laboratories.

    Quick start:
        madsci init           Initialize a new lab
        madsci start lab      Start all services
        madsci status         Check service status
        madsci tui            Launch interactive interface

    For more information:
        madsci <command> --help
        https://ad-sdl.github.io/MADSci/
    """
    ctx.ensure_object(dict)
    ctx.obj['config'] = MadsciCLIConfig.load(config)
    ctx.obj['lab_url'] = lab_url
    ctx.obj['verbose'] = verbose
    ctx.obj['quiet'] = quiet
    ctx.obj['console'] = Console(no_color=no_color, quiet=quiet)
    ctx.obj['json'] = json_output

# Register commands
madsci.add_command(version.version)
madsci.add_command(doctor.doctor)
madsci.add_command(status.status)
madsci.add_command(logs.logs)
madsci.add_command(init.init)
madsci.add_command(new.new)
madsci.add_command(start.start)
madsci.add_command(stop.stop)
madsci.add_command(validate.validate)
madsci.add_command(migrate.migrate)
madsci.add_command(registry.registry)
madsci.add_command(tui.tui)
madsci.add_command(completion.completion)

def main():
    """CLI entry point."""
    madsci()

if __name__ == '__main__':
    main()
```

### CLI Configuration

```python
# src/madsci_client/madsci/client/cli/utils/config.py
from pathlib import Path
from typing import Optional
from pydantic import AnyUrl
from madsci.common.types.base_types import MadsciBaseSettings

class MadsciCLIConfig(MadsciBaseSettings):
    """Configuration for MADSci CLI."""

    model_config = {'env_prefix': 'MADSCI_'}

    # Default URLs
    lab_url: AnyUrl = "http://localhost:8000/"

    # Registry settings
    registry_path: Path = Path.home() / ".madsci" / "registry.json"

    # Output preferences
    default_output_format: str = "text"  # text, json, yaml
    color_enabled: bool = True

    # Template settings
    template_dir: Optional[Path] = None  # Custom template directory

    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "MadsciCLIConfig":
        """Load configuration from file or defaults."""
        if config_path:
            return cls.from_yaml(Path(config_path))

        # Check for config in standard locations
        for path in [
            Path.cwd() / ".madsci" / "config.yaml",
            Path.home() / ".madsci" / "config.yaml",
        ]:
            if path.exists():
                return cls.from_yaml(path)

        return cls()
```

### Output Helpers

```python
# src/madsci_client/madsci/client/cli/utils/output.py
from typing import Any
import json
import yaml
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

def output_result(
    console: Console,
    data: Any,
    format: str = "text",
    title: str = None
):
    """Output data in the requested format."""
    if format == "json":
        console.print_json(json.dumps(data, default=str))
    elif format == "yaml":
        console.print(yaml.dump(data, default_flow_style=False))
    else:
        # Rich formatted output
        if isinstance(data, dict):
            table = Table(title=title, show_header=False)
            for key, value in data.items():
                table.add_row(str(key), str(value))
            console.print(table)
        elif isinstance(data, list):
            for item in data:
                console.print(f"  • {item}")
        else:
            console.print(data)

def success(console: Console, message: str):
    """Print success message."""
    console.print(f"[green]✓[/green] {message}")

def error(console: Console, message: str):
    """Print error message."""
    console.print(f"[red]✗[/red] {message}", style="red")

def warning(console: Console, message: str):
    """Print warning message."""
    console.print(f"[yellow]⚠[/yellow] {message}", style="yellow")

def info(console: Console, message: str):
    """Print info message."""
    console.print(f"[blue]ℹ[/blue] {message}")
```

---

## Error Handling

### Error Categories

| Exit Code | Category | Description |
|-----------|----------|-------------|
| 0 | Success | Command completed successfully |
| 1 | General Error | Unspecified error |
| 2 | Usage Error | Invalid command or options |
| 3 | Configuration Error | Invalid or missing configuration |
| 4 | Connection Error | Cannot connect to services |
| 5 | Validation Error | Input validation failed |
| 10+ | Custom | Command-specific errors |

### Error Output Format

```
✗ Error: Cannot connect to lab manager

  URL: http://localhost:8000
  Status: Connection refused

  Possible causes:
    • Lab services not running
    • Firewall blocking connection
    • Incorrect URL

  Try:
    • madsci start lab
    • madsci doctor --check network
    • Check MADSCI_LAB_URL environment variable
```

---

## Testing Strategy

All CLI commands will be tested using Click's CliRunner:

```python
# tests/cli/test_version.py
from click.testing import CliRunner
from madsci.client.cli import madsci

def test_version_command():
    runner = CliRunner()
    result = runner.invoke(madsci, ['version'])
    assert result.exit_code == 0
    assert 'MADSci' in result.output
    assert 'madsci_common' in result.output

def test_version_json():
    runner = CliRunner()
    result = runner.invoke(madsci, ['version', '--json'])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert 'version' in data
    assert 'packages' in data
```

---

## Migration from Existing CLIs

Existing CLI commands (`madsci-backup`, `madsci-postgres-backup`, `madsci-mongodb-backup`) will be:
1. Re-exported under `madsci backup` command group
2. Deprecated standalone entry points with warning
3. Eventually removed in future major version

```python
# src/madsci_client/madsci/client/cli/commands/backup.py
import click
from madsci.common.backup_tools.cli import madsci_backup

# Re-export existing backup commands under madsci backup
@click.command(cls=click.CommandCollection, sources=[madsci_backup])
def backup():
    """Database backup management."""
    pass
```

---

## Dependencies

New dependencies for CLI (add to `madsci_client/pyproject.toml`):

```toml
dependencies = [
    # ... existing ...
    "click>=8.1",        # Already present
    "rich>=13.0",        # Already present via madsci_common
    "trogon>=0.6.0",     # Already present
    "textual>=0.50.0",   # For TUI (detailed in TUI design)
]
```

---

## Design Decisions

The following decisions have been made based on review:

1. **Alias support**: Yes, command aliases will be supported (e.g., `madsci n` for `madsci new`). Implementation will use Click's built-in alias support.

2. **Plugin system**: Deferred to future work. The initial implementation will focus on core functionality. Plugin architecture can be added later if there's demand for third-party extensions.

3. **Configuration file format**: Use `MadsciBaseSettings` (Pydantic Settings) to support multiple formats (YAML, TOML, JSON, environment variables). **Default to TOML** for the user config file (`~/.madsci/config.toml`) as it's more human-friendly for configuration.

4. **Update mechanism**: Yes, `madsci version --check-updates` will check PyPI for available updates. This will use a simple HTTP request to the PyPI JSON API and compare versions using semantic versioning.

5. **OpenTelemetry integration**: The CLI integrates with MADSci's existing OTEL support:
   - `madsci doctor` checks OTEL exporter connectivity when `*_OTEL_ENABLED=true`
   - `madsci status` shows trace/span counts if OTEL is enabled
   - All CLI operations can be traced via OTEL when configured
   - OTEL configuration follows the same `*_OTEL_*` environment variable pattern as managers

6. **Documentation URL**: All help text and error messages reference https://ad-sdl.github.io/MADSci/ as the documentation location.

---

## Command Aliases

The following aliases will be supported for frequently-used commands:

| Command | Alias |
|---------|-------|
| `madsci new` | `madsci n` |
| `madsci status` | `madsci s` |
| `madsci logs` | `madsci l` |
| `madsci doctor` | `madsci doc` |
| `madsci validate` | `madsci val` |
| `madsci tui` | `madsci ui` |
