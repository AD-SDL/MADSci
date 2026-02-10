# Equipment Integrator Guide

This guide is for the **Equipment Integrator** persona - developers who create modules to integrate laboratory instruments with MADSci.

## Guide Contents

1. [Understanding Modules](01-understanding-modules.md) - Node vs Module vs Interface concepts
2. [Creating a Module](02-creating-a-module.md) - `madsci new module` walkthrough
3. [Developing Interfaces](03-developing-interfaces.md) - Interface patterns and driver communication
4. [Fake Interfaces](04-fake-interfaces.md) - Creating testable simulated implementations
5. [Wiring the Node](05-wiring-the-node.md) - Connecting interface to node server
6. [Testing Strategies](06-testing-strategies.md) - Unit, integration, and hardware-in-the-loop testing
7. [Debugging](07-debugging.md) - Common issues, logging, and troubleshooting
8. [Packaging & Deployment](08-packaging-deployment.md) - Docker, dependencies, and CI/CD
9. [Publishing](09-publishing.md) - Sharing modules and versioning

## Who is an Equipment Integrator?

An Equipment Integrator:

- Develops modules for laboratory instruments
- Creates interfaces for hardware communication
- Tests modules with and without physical hardware
- Packages modules for deployment

Often, this is the same person who also operates the lab or runs experiments.

## Quick Start

To create a new module:

```bash
madsci new module --name my_instrument
cd my_instrument_module
pip install -e .
python src/my_instrument_rest_node.py
```

## Key Concepts

### Module vs Node vs Interface

| Concept | Description | Files |
|---------|-------------|-------|
| **Module** | Complete package for an instrument | Entire repository |
| **Node** | Runtime REST server | `*_rest_node.py` |
| **Interface** | Hardware communication logic | `*_interface.py` |

### The Development Workflow

```
1. Scaffold module     →  madsci new module
2. Develop interface   →  Hardware communication
3. Create fake         →  Simulated interface
4. Test interface      →  Jupyter/pytest
5. Wire up node        →  Connect to MADSci
6. Test node           →  Run with fake interface
7. Test with hardware  →  Switch to real interface
8. Package & deploy    →  Docker, CI/CD
```

## Prerequisites

- Python 3.10+
- Understanding of your target instrument's communication protocol
- Basic familiarity with MADSci concepts (see [Tutorial 1](../../tutorials/01-exploration.md))
