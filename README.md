# The Modular Autonomous Discovery for Science (MADSci) Framework

<!-- GitHub Actions Status Badges -->
[![Docker](https://github.com/AD-SDL/MADSci/actions/workflows/docker.yml/badge.svg)](https://github.com/AD-SDL/MADSci/actions/workflows/docker.yml)
[![Pre-Commit](https://github.com/AD-SDL/MADSci/actions/workflows/pre-commit.yml/badge.svg)](https://github.com/AD-SDL/MADSci/actions/workflows/pre-commit.yml)
[![PyPI](https://github.com/AD-SDL/MADSci/actions/workflows/pypi.yml/badge.svg)](https://github.com/AD-SDL/MADSci/actions/workflows/pypi.yml)
[![Pytests](https://github.com/AD-SDL/MADSci/actions/workflows/pytests.yml/badge.svg)](https://github.com/AD-SDL/MADSci/actions/workflows/pytests.yml)
![Coverage badge](https://raw.githubusercontent.com/AD-SDL/MADSci/python-coverage-comment-action-data/badge.svg)

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
- [Experiment Manager](./src/madsci_experiment_manager/README.md): manages experimental runs and campaigns across a MADSci-powered lab.
- [Experiment Application](./src/madsci_experiment_application/README.md): extensible python class for running autonomous experiments.
- [Resource Manager](./src/madsci_resource_manager/README.md): For tracking labware, assets, samples, and consumables in an automated or autonomous lab.
- [Data Manager](./src/madsci_data_manager/README.md): handles capturing, storing, and querying data, in either JSON value or file form, created during the course of an experiment (either collected by instruments, or synthesized during anaylsis)
- [Squid Lab Manager](./src/madsci_squid/README.md): a central lab configuration manager and dashboard provider for MADSci-powered labs.

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

### Quick Start

Try MADSci with our complete example lab:

```bash
git clone https://github.com/AD-SDL/MADSci.git
cd MADSci
docker compose up  # Starts all services with example configuration
```

Access the dashboard at `http://localhost:8000` to monitor your virtual lab.

## Configuration

MADSci uses environment variables for configuration with hierarchical precedence. Key patterns:

- **Service URLs**: Each manager defaults to `localhost` with specific ports (Event: 8001, Experiment: 8002, etc.)
- **Database connections**: MongoDB/PostgreSQL on localhost by default
- **File storage**: Defaults to `~/.madsci/` subdirectories
- **Environment prefixes**: Each service has a unique prefix (e.g., `WORKCELL_`, `EVENT_`)

See [Configuration.md](./Configuration.md) for comprehensive options and [example_lab/](./example_lab/) for working configurations.

## Roadmap

We're working on bringing the following additional components to MADSci:

- **Auth Manager**: For handling authentication and user and group management for an autonomous lab.
- **Transfer Manager**: For coordinating resource movement in a lab.

## Getting Started

### Learning Resources

1. **[Example Lab](./example_lab/)**: Complete working lab with virtual instruments (robot arm, liquid handler, plate reader)
2. **[Example Notebooks](./example_lab/notebooks)**: Jupyter notebooks covering core concepts and implementation patterns, included in the example lab
3. **Configuration examples**: See [example_lab/managers/](./example_lab/managers/) for manager configurations

### Common Usage Patterns

**Starting a basic lab:**
```bash
# Use our example lab as a starting point
cp -r example_lab my_lab
cd my_lab
# Modify configurations in managers/ directory
docker compose up
```

**Creating custom nodes:**
```python
# See example_lab/example_modules/ for reference implementations
from madsci.node_module import AbstractNodeModule

class MyInstrument(AbstractNodeModule):
    def my_action(self, param1: str) -> dict:
        # Your instrument control logic
        return {"result": "success"}
```

**Submitting workflows:**
```python
# See example_lab/workflows/ for workflow definitions
from madsci.client.workcell_client import WorkcellClient

client = WorkcellClient("http://localhost:8005")
result = client.submit_workflow("path/to/workflow.yaml")
```

## Developer Guide

### Prerequisites

- **Python 3.9+**: Required for all MADSci components
- **[PDM](https://pdm-project.org/)**: For dependency management and virtual environments
- **[Docker](https://docs.docker.com/engine/install/)**: Required for services and integration tests
  - Alternatives: [Rancher Desktop](https://rancherdesktop.io/), [Podman](https://podman.io/)
- **[just](https://github.com/casey/just)**: Task runner for development commands
- **Node.js/npm**: Only needed for dashboard development

### Quick Setup

```bash
# Clone and initialize
git clone https://github.com/AD-SDL/MADSci.git
cd MADSci
just init  # Installs all dependencies and sets up pre-commit hooks

# See all available commands
just list

# Start example lab for testing
just up
```

### Development Commands

```bash
# Testing
pytest                    # Run all tests
just test                 # Alternative test runner
pytest -k workcell        # Run specific component tests

# Code Quality
just checks               # Run all pre-commit checks (ruff, formatting, etc.)
ruff check               # Manual linting
ruff format              # Manual formatting

# Services
just build               # Build Docker images
just up                  # Start example lab
just down               # Stop services

# Dashboard Development
cd ui/
npm run dev             # Start Vue dev server
npm run build           # Build for production
```

### Development Patterns

**Manager Implementation:**
Each manager service follows this structure:
- Settings class inheriting from `MadsciBaseSettings`
- FastAPI server with REST endpoints
- Client class for programmatic interaction
- Database models (SQLModel/Pydantic)

**Testing:**
- Integration tests use Docker containers via pytest-mock-resources
- Component tests are in each package's `tests/` directory
- Use `pytest -k EXPRESSION` to filter tests

**Configuration:**
- Environment variables with hierarchical precedence
- Each manager has unique prefix (e.g., `WORKCELL_`, `EVENT_`)
- See [Configuration.md](./Configuration.md) for full details

### Dev Container Support

For VS Code users, use the included [.devcontainer](./.devcontainer) for instant setup:
- Automatic dependency installation
- Pre-configured development environment
- Docker services ready to run
