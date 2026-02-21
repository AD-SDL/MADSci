# Tutorial 1: Exploring MADSci

**Time to Complete**: ~20 minutes
**Prerequisites**: Python 3.10+, pip
**Docker Required**: No

## What You'll Learn

In this tutorial, you'll:

1. Install MADSci and verify your environment
2. Understand core MADSci concepts
3. Use the `madsci` CLI to explore available tools
4. Launch and navigate the interactive TUI
5. Understand the "Ladder of Complexity" approach

## Introduction to MADSci

MADSci (Modular Autonomous Discovery for Science) is a framework for building and operating self-driving laboratories (SDLs). It provides:

- **Modular Architecture**: Mix and match components based on your needs
- **Progressive Disclosure**: Start simple, add complexity as needed
- **Instrument Integration**: Connect any lab equipment through a standardized interface
- **Workflow Orchestration**: Coordinate multi-step experimental protocols
- **Data Management**: Capture, store, and query experimental data

### Core Concepts

| Concept | Description |
|---------|-------------|
| **Node** | A running server that controls a single instrument. Executes actions and reports state. |
| **Module** | A complete package containing everything to control an instrument: node, interfaces, drivers, tests, and documentation. |
| **Interface** | A class that handles hardware communication, independent of MADSci. Can be used standalone in notebooks. |
| **Workcell** | A collection of nodes that work together to perform experiments. |
| **Workflow** | A sequence of steps executed across nodes in a workcell. |
| **Manager** | A service that coordinates a specific concern (events, experiments, resources, data, etc.). |

### The Ladder of Complexity

MADSci is designed with progressive disclosure in mind. You don't need to understand everything to get started:

```
Rung 5: Full distributed lab (Docker, multiple hosts, OTEL, etc.)
Rung 4: Local multi-service lab (Docker compose, all managers)
Rung 3: Single workcell + essential managers (minimal Docker or pure Python)
Rung 2: Single node + experiment script (pure Python, no services)
Rung 1: Interactive exploration (TUI, notebooks) ← YOU ARE HERE
```

This tutorial starts at Rung 1. Each subsequent tutorial climbs the ladder.

## Step 1: Install MADSci

First, create a virtual environment and install MADSci:

```bash
# Create a new directory for your work
mkdir madsci-tutorial
cd madsci-tutorial

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install MADSci client with TUI support
pip install madsci-client[tui]
```

## Step 2: Verify Your Environment

MADSci includes a `doctor` command that checks your environment:

```bash
madsci doctor
```

You should see output like:

```
╭─────────────────────────────────────────────────────────────────╮
│                      MADSci Doctor                              │
╰─────────────────────────────────────────────────────────────────╯

  Python Environment
  ✓ Python version: 3.10.12 (meets minimum 3.10)
  ✓ Virtual environment active
  ✓ madsci-client installed (0.6.2)
  ✓ madsci-common installed (0.6.2)

  Docker (optional)
  ⚠ Docker not found - some features require Docker
    Hint: Install Docker Desktop or Rancher Desktop

  Ports
  ✓ Port 8000 available (Lab Manager)
  ✓ Port 8001 available (Event Manager)
  ...
```

Don't worry if Docker isn't installed - it's not required for this tutorial.

## Step 3: Explore the CLI

The `madsci` command is your gateway to all MADSci operations. Let's explore:

```bash
# See all available commands
madsci --help
```

Output:
```
Usage: madsci [OPTIONS] COMMAND [ARGS]...

  MADSci - Modular Autonomous Discovery for Science.

  A comprehensive toolkit for building and operating self-driving laboratories.

  Quick start:
      madsci init           Initialize a new lab
      madsci start lab      Start all services
      madsci status         Check service status
      madsci tui            Launch interactive interface

Options:
  --lab-url TEXT       Lab manager URL.
  -v, --verbose        Increase verbosity.
  -q, --quiet          Suppress non-essential output.
  --no-color           Disable colored output.
  --json               Output in JSON format.
  --version            Show the version and exit.
  --help               Show this message and exit.

Commands:
  doctor    Check system requirements and diagnose issues.
  logs      View and filter event logs.
  migrate   Migrate definition files to new format.
  new       Create new MADSci components from templates.
  registry  Manage the component ID registry.
  status    Show status of MADSci services.
  tui       Launch the interactive terminal UI.
  version   Display version information.
```

### Useful Command Aliases

For convenience, common commands have short aliases:

| Alias | Command | Description |
|-------|---------|-------------|
| `n` | `new` | Create new components |
| `s` | `status` | Check service status |
| `l` | `logs` | View logs |
| `doc` | `doctor` | System diagnostics |
| `ui` | `tui` | Launch TUI |

### Check MADSci Version

```bash
madsci version
```

Output:
```
MADSci Version Information

  Core Packages:
    madsci-client    0.6.2
    madsci-common    0.6.2

  Environment:
    Python           3.10.12
    Platform         darwin (arm64)
```

## Step 4: Explore the `new` Command

The `madsci new` command helps you create new components using templates:

```bash
# See what you can create
madsci new --help
```

Output:
```
Usage: madsci new [OPTIONS] COMMAND [ARGS]...

  Create new MADSci components from templates.

Commands:
  experiment  Create a new experiment.
  interface   Add an interface to an existing module.
  lab         Create a new lab configuration.
  list        List available templates.
  module      Create a new node module.
  node        Create a new node server.
  workflow    Create a new workflow.
  workcell    Create a new workcell configuration.
```

### List Available Templates

```bash
madsci new list
```

Output:
```
Available Templates

  Category     Template    Description
  ──────────────────────────────────────────────────────────────
  module       basic       Complete module with node, interfaces, types, tests
  interface    fake        Simulated interface for testing without hardware
  experiment   script      Simple run-once experiment using ExperimentScript
  experiment   notebook    Jupyter notebook experiment
  workflow     basic       Single-step workflow YAML
  workcell     basic       Workcell configuration with environment example
  lab          minimal     Lab configuration without Docker
```

## Step 5: Launch the TUI

MADSci includes an interactive Terminal User Interface (TUI) for monitoring and managing your lab:

```bash
madsci tui
```

The TUI provides:

- **Dashboard**: Overview of all services and their status
- **Status Screen**: Detailed view of each manager service
- **Log Viewer**: Real-time log viewing with filtering

### TUI Navigation

| Key | Action |
|-----|--------|
| `d` | Go to Dashboard |
| `s` | Go to Status screen |
| `l` | Go to Logs screen |
| `r` | Refresh current view |
| `q` | Quit |
| `?` | Show help |

**Note**: Since we haven't started any services yet, all services will show as "offline" or "unreachable". This is expected!

### TUI Screenshot (Dashboard)

```
╭─────────────────────────────────────────────────────────────────╮
│                    MADSci Dashboard                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Service Status                                                 │
│  ─────────────────────────────────────────────────────────────  │
│  ○ Lab Manager        http://localhost:8000  Offline            │
│  ○ Event Manager      http://localhost:8001  Offline            │
│  ○ Experiment Manager http://localhost:8002  Offline            │
│  ○ Resource Manager   http://localhost:8003  Offline            │
│  ○ Data Manager       http://localhost:8004  Offline            │
│  ○ Workcell Manager   http://localhost:8005  Offline            │
│  ○ Location Manager   http://localhost:8006  Offline            │
│                                                                 │
│  Press 'r' to refresh, 'q' to quit, '?' for help               │
│                                                                 │
╰─────────────────────────────────────────────────────────────────╯
```

Press `q` to exit the TUI.

## Step 6: Understand Configuration

MADSci uses a layered configuration system:

1. **Environment Variables**: Highest priority, prefix with service name (e.g., `LAB_SERVER_URL`)
2. **Settings Files**: `settings.yaml` or `.env` files
3. **Defaults**: Sensible defaults for all settings

### User Configuration

You can create a `settings.yaml` file in your project directory:

```yaml
# settings.yaml

# Service URLs (all optional — defaults to localhost)
lab_server_url: "http://localhost:8000/"
event_server_url: "http://localhost:8001/"
experiment_server_url: "http://localhost:8002/"
resource_server_url: "http://localhost:8003/"
data_server_url: "http://localhost:8004/"
workcell_server_url: "http://localhost:8005/"
location_server_url: "http://localhost:8006/"
```

## Concepts Deep Dive

### Nodes and Modules

The most important distinction in MADSci:

- **Node**: The runtime server that the workcell talks to. It receives action requests and reports status.

- **Module**: A complete package (often its own git repository) containing everything needed to control an instrument:
  - Node server (`foo_rest_node.py`)
  - Interface classes (`foo_interface.py`, `foo_fake_interface.py`)
  - Type definitions (`foo_types.py`)
  - Tests, Dockerfile, documentation

**Key Insight**: The interface is independent of MADSci! You can use it directly in Jupyter notebooks or scripts without running a node server.

### Managers

MADSci uses microservices (managers) to handle different concerns:

| Manager | Port | Purpose |
|---------|------|--------|
| **Lab Manager** | 8000 | Central dashboard, lab coordination |
| **Event Manager** | 8001 | Distributed logging and event querying |
| **Experiment Manager** | 8002 | Experiment lifecycle and campaigns |
| **Resource Manager** | 8003 | Laboratory inventory and resources |
| **Data Manager** | 8004 | Data capture and storage |
| **Workcell Manager** | 8005 | Workflow orchestration |
| **Location Manager** | 8006 | Physical location tracking |

You don't need all managers for every use case! Start with what you need.

### Workflows

Workflows define multi-step experimental protocols:

```yaml
# example_workflow.yaml
name: Simple Transfer
steps:
  - name: pick_up_sample
    node: robot_arm
    action: pick
    args:
      location: rack_1
      slot: A1

  - name: move_to_analyzer
    node: robot_arm
    action: place
    args:
      location: analyzer_1
      slot: input
```

## What's Next?

You've completed the exploration tutorial! You now understand:

- What MADSci is and its core concepts
- How to use the CLI and TUI
- The difference between nodes and modules
- The role of different manager services

### Next Tutorial

**[Tutorial 2: Your First Node](02-first-node.md)** - Create a node module with a fake interface and test it without any services running.

### Quick Reference

| Command | Description |
|---------|-----------|
| `madsci doctor` | Check your environment |
| `madsci version` | Show version info |
| `madsci new list` | List available templates |
| `madsci new module` | Create a new module |
| `madsci tui` | Launch interactive TUI |
| `madsci --help` | Show all commands |

### Additional Resources

- [MADSci Documentation](https://ad-sdl.github.io/MADSci/)
- [Configuration Reference](../../docs/Configuration.md)
- [Example Lab](../../examples/example_lab/README.md)
