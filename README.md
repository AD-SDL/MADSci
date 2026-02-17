# The Modular Autonomous Discovery for Science (MADSci) Framework

<!-- GitHub Actions Status Badges -->
[![Docker](https://github.com/AD-SDL/MADSci/actions/workflows/docker.yml/badge.svg)](https://github.com/AD-SDL/MADSci/actions/workflows/docker.yml)
[![Pre-Commit](https://github.com/AD-SDL/MADSci/actions/workflows/pre-commit.yml/badge.svg)](https://github.com/AD-SDL/MADSci/actions/workflows/pre-commit.yml)
[![PyPI](https://github.com/AD-SDL/MADSci/actions/workflows/pypi.yml/badge.svg)](https://github.com/AD-SDL/MADSci/actions/workflows/pypi.yml)
[![Pytests](https://github.com/AD-SDL/MADSci/actions/workflows/pytests.yml/badge.svg)](https://github.com/AD-SDL/MADSci/actions/workflows/pytests.yml)
![Coverage badge](https://raw.githubusercontent.com/AD-SDL/MADSci/python-coverage-comment-action-data/badge.svg)
[![JOSS status](https://joss.theoj.org/papers/d554e38543529f08aa8ebaf068c17eec/status.svg)](https://joss.theoj.org/papers/d554e38543529f08aa8ebaf068c17eec)

<img src="./assets/drawio/madsci_control_flow.drawio.svg" alt="Diagram of a MADSci laboratory's Architecture" width=1000/>

_Experiment Control Flow Using MADSci_

## Overview

MADSci is a modular, autonomous, and scalable framework for scientific discovery and experimentation. It aims to provide:

- **Laboratory Instrument Automation and Integration** via the MADSci Node standard. Developers can implement device-specific Node modules in any language that can then be integrated into a MADSci system using a common interface standard (currently supports REST-based HTTP communication)
- **Workflow Management**, allowing users to define and run flexible scientific workflows that can leverage one or more Nodes to complete complex tasks.
- **Experiment Management**, conducting flexible closed loop autonomous experiments by combining multiple workflow runs, as well as any compute, decision making, data collection, and analysis as needed.
- **Resource Management**, allowing robust tracking of all the labware, consumables, equipment, samples, and assets used in an autonomous laboratory.
- **Event Management**, enabling distributed logging and event handling across every part of the autonomous lab.
- **Data Management**, collecting and storing data created by instruments or analysis as part of an experiment.
- **Location Management**, coordinating multiple different representations of locations in the laboratory and their interactions with resources and nodes.
- **Observability**, with built-in OpenTelemetry integration for distributed tracing, metrics, and log correlation across the entire lab infrastructure.

<img src="./assets/drawio/madsci_architecture.drawio.svg" alt="Diagram of a MADSci laboratory's Architecture" width=1000/>

_Diagram of a MADSci Laboratory's Infrastructure_

## Notes on Stability

MADSci is currently in beta. Most of the core functionality is working and tested, but there may be bugs or stability issues (if you run into any, please [open an issue](https://github.com/AD-SDL/MADSci/issues) so we can get it fixed). New releases will likely include breaking changes, so we recommend pinning the version in your dependencies and upgrading only after reviewing the release notes.

## Documentation

MADSci is made up of a number of different modular components, each of which can be used independently to fulfill specific needs, or composed to build more complex and capable systems. Below we link to specific documentation for each system component.

- [Common](./src/madsci_common/README.md): the common types and utilities used across the MADSci toolkit
- [Clients](./src/madsci_client/README.md): A collection of clients for interacting with different components of MADSci
- [Event Manager](./src/madsci_event_manager/README.md): handles distributed event logging and querying across a distributed lab.
- [Workcell Manager](./src/madsci_workcell_manager/README.md): handles coordinating and scheduling a collection of interoperating instruments, robots, and resources using Workflows.
- [Location Manager](./src/madsci_location_manager/README.md): manages laboratory locations, resource attachments, and node-specific references.
- [Experiment Manager](./src/madsci_experiment_manager/README.md): manages experimental runs and campaigns across a MADSci-powered lab.
- [Experiment Application](./src/madsci_experiment_application/README.md): extensible python class for running autonomous experiments.
- [Resource Manager](./src/madsci_resource_manager/README.md): For tracking labware, assets, samples, and consumables in an automated or autonomous lab.
- [Data Manager](./src/madsci_data_manager/README.md): handles capturing, storing, and querying data, in either JSON value or file form, created during the course of an experiment (either collected by instruments, or synthesized during anaylsis)
- [Squid Lab Manager](./src/madsci_squid/README.md): a central lab configuration manager and dashboard provider for MADSci-powered labs.

### Guides

- [CLI Reference](./docs/guides/cli_reference.md): Complete reference for all 17 CLI commands, options, and aliases.
- [Template Catalog](./docs/guides/template_catalog.md): All 26 built-in templates with parameters and examples.
- [Logging and Event Context](./docs/guides/logging.md): Guide to MADSci's structured logging system and hierarchical context propagation.
- [Observability](./docs/guides/observability.md): How to use the OpenTelemetry observability stack for distributed tracing, metrics, and logs.
- [Daily Operations](./docs/guides/operator/01-daily-operations.md): Day-to-day lab operations, startup, shutdown, and health checks.

## Installation

### Python Packages

All MADSci components are available via [PyPI](https://pypi.org/search/?q=madsci). Install individual components as needed:

```bash
# Core components
pip install madsci.common          # Shared types and utilities
pip install madsci.client          # Client libraries
pip install madsci.experiment_application # Experiment Logic

# Manager services
pip install madsci.event_manager    # Event logging and querying
pip install madsci.workcell_manager # Workflow coordination
pip install madsci.location_manager # Location management
pip install madsci.resource_manager # Resource tracking
pip install madsci.data_manager     # Data capture and storage
pip install madsci.experiment_manager # Experiment management

# Lab infrastructure
pip install madsci.squid           # Lab manager with dashboard
pip install madsci.node_module      # Node development framework
```

### Docker Images

We provide pre-built Docker images for easy deployment:

- **[ghcr.io/ad-sdl/madsci](https://github.com/orgs/AD-SDL/packages/container/package/madsci)**: Base image with all MADSci packages. Use as foundation for custom services.
- **[ghcr.io/ad-sdl/madsci_dashboard](https://github.com/orgs/AD-SDL/packages/container/package/madsci_dashboard)**: Extends base image with web dashboard for lab management.

For users new to docker, we recommend checking out our [Docker Guide](https://github.com/AD-SDL/MADSci/wiki/Docker-Guide)

### Quick Start

```bash
pip install madsci-client
madsci init my_lab          # Interactive lab setup wizard
cd my_lab
madsci start                # Start with Docker
# or
madsci start --mode=local   # Start without Docker (pure Python)
```

Access the dashboard at `http://localhost:8000` to monitor your lab.

To try the complete example lab instead:

```bash
git clone https://github.com/AD-SDL/MADSci.git
cd MADSci
docker compose up  # Starts all services with example configuration
```

## Configuration

MADSci uses environment variables for configuration with hierarchical precedence. Key patterns:

- **Service URLs**: Each manager defaults to `localhost` with specific ports (Event: 8001, Experiment: 8002, Resource: 8003, Data: 8004, Workcell: 8005, Location: 8006, etc.)
- **Database connections**: MongoDB/PostgreSQL on localhost by default
- **File storage**: Defaults to `~/.madsci/` subdirectories
- **Environment prefixes**: Each service has a unique prefix (e.g., `WORKCELL_`, `EVENT_`, `LOCATION_`)
- **OpenTelemetry**: Configurable per-manager with `*_OTEL_ENABLED`, `*_OTEL_ENDPOINT`, etc.

See [Configuration.md](./Configuration.md) for comprehensive options, [example_lab/](./examples/example_lab/) for working configurations, and [OBSERVABILITY.md](./docs/guides/observability.md) for OpenTelemetry setup.

## Roadmap

We're working on bringing the following additional components to MADSci:

- **Auth Manager**: For handling authentication and user and group management for an autonomous lab.

## Getting Started

### Learning Resources

1. **[Example Lab](./examples/example_lab/)**: Complete working lab with virtual instruments (robot arm, liquid handler, plate reader)
2. **[Example Notebooks](./examples/notebooks)**: Jupyter notebooks covering core concepts and implementation patterns, included in the example lab
3. **Configuration examples**: See [example_lab/managers/](./examples/example_lab/managers/) for manager configurations

### CLI Overview

MADSci provides a unified CLI (`madsci`) with 17 commands:

| Command | Alias | Description |
|---------|-------|-------------|
| `init` | | Initialize a new lab interactively |
| `new` | `n` | Create components from 26 built-in templates |
| `start` | | Start lab services (Docker or local mode) |
| `stop` | | Stop lab services |
| `status` | `s` | Check service health |
| `doctor` | `doc` | Run diagnostic checks |
| `logs` | `l` | View and filter event logs |
| `run` | | Run workflows or experiments |
| `validate` | `val` | Validate configuration files |
| `config` | `cfg` | Export, create, or inspect configuration |
| `backup` | | Create database backups |
| `registry` | | Manage service registry |
| `migrate` | | Run database migrations |
| `tui` | `ui` | Launch interactive terminal interface |
| `completion` | | Generate shell completions |
| `commands` | `cmd` | List all commands |
| `version` | | Show version information |

Run `madsci <command> --help` for details on any command. See [CLI Reference](./docs/guides/cli_reference.md) for full documentation.

### Templates

Generate scaffolding for any MADSci component:

```bash
madsci new list                       # Browse all 26 templates
madsci new module                     # Interactive module creation
madsci new experiment --modality tui  # TUI experiment
madsci new lab --template standard    # Full lab with Docker Compose
```

See [Template Catalog](./docs/guides/template_catalog.md) for the complete list.

### TUI (Terminal User Interface)

```bash
madsci tui    # Launch interactive dashboard
```

Provides real-time service status, log browsing, node management, and workflow monitoring with auto-refresh.

### Local Mode

Run all managers without Docker using in-memory backends:

```bash
madsci start --mode=local
```

Useful for development, testing, and environments without Docker. Data is ephemeral.

### Configuration Management

```bash
madsci config export           # Export current config to YAML
madsci config create           # Create a new config file interactively
madsci config show             # Display active configuration
```

### Common Usage Patterns

**Creating custom nodes:**
```python
# See examples/example_lab/example_modules/ for reference implementations
from madsci.node_module import AbstractNodeModule

class MyInstrument(AbstractNodeModule):
    def my_action(self, param1: str) -> dict:
        # Your instrument control logic
        return {"result": "success"}
```

**Submitting workflows:**
```python
# See examples/example_lab/workflows/ for workflow definitions
from madsci.client.workcell_client import WorkcellClient

client = WorkcellClient("http://localhost:8005")
result = client.submit_workflow("path/to/workflow.yaml")
```

## Contributing

Interested in contributing to MADSci? We welcome all contributions, from bug reports to new features!

See our [Contributing Guide](./CONTRIBUTING.md) for:
- Development setup and prerequisites
- Development commands and workflows
- How to report bugs and request features
- Pull request guidelines
- Configuration best practices

For quick development setup:
```bash
git clone https://github.com/AD-SDL/MADSci.git
cd MADSci
just init  # Installs dependencies and sets up pre-commit hooks
just up    # Start example lab for testing
```
