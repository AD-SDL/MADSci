# The Modular Autonomous Discovery for Science (MADSci) Framework

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
- [Resource Manager](./src/madsci_resource_manager/README.md): For tracking labware, assets, samples, and consumables in an automated or autonomous lab.
- [Data Manager](./src/madsci_data_manager/README.md): handles capturing, storing, and querying data, in either JSON value or file form, created during the course of an experiment (either collected by instruments, or synthesized during anaylsis)
- [Squid Lab Manager](./src/madsci_squid/README.md): a central lab configuration manager and dashboard provider for MADSci-powered labs.

## Python

We provide python packages via the [Python Package Index](https://pypi.org/search/?q=madsci) for each of the MADSci system components. See the individual components for information about how to install and use their corresponding python package.

## Docker

We provide docker images to make containerizing and orchestrating your labs as easy and robust as possible. Currently, we provide:

- [ghcr.io/ad-sdl/madsci](https://github.com/orgs/AD-SDL/packages/container/package/madsci): base docker image with the full set of MADSci python packages installed and available. You can use this image as a base for your own Manager, Experiment Application, or Node docker containers.
- [ghcr.io/ad-sdl/madsci_dashboard](https://github.com/orgs/AD-SDL/packages/container/package/madsci_dashboard): extends the base image to add the web-based dashboard's prebuilt static files. Should be used for running your Squid Lab Manager if you want to host the MADSci Dashboard.

## Roadmap

We're working on bringing the following additional components to MADSci:

- **Auth Manager**: For handling authentication and user and group management for an autonomous lab.
- **Transfer Manager**: For coordinating resource movement in a lab.

## Getting Started with MADSci

To get started with MADSci, we recommend checking out our [MADSci Examples Repository](https://github.com/AD-SDL/MADSci_Examples). There you'll find Jupyter Notebooks walking through the core concepts and how to leverage MADSci to build your autonomous laboratory and experiments.

## Developer Guide

### Environment Setup

Some notes for setting up a development environment for the MADSci core packages:

1. [Clone the Repository](https://docs.github.com/en/repositories/creating-and-managing-repositories/cloning-a-repository)
    1. If you want to contribute back, or have your own version of the code, consider [Forking the Repository](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/fork-a-repo) first
1. [Install Python](https://www.python.org/downloads/)
    1. We use [PDM](https://pdm-project.org/latest/) to make installing the `madsci` python packages and managing dependencies easier
    1. Alternatively, we recommend using [Virtual Environments](https://realpython.com/python-virtual-environments-a-primer/)
1. To build and/or use the MADSci docker containers, [https://docs.docker.com/engine/install/]
    1. If your organization doesn't allow Docker Desktop, or if you simply prefer an open source alternative, we recommend [Rancher Desktop](https://rancherdesktop.io/) or [Podman](https://podman.io/)
1. We use the [just](https://github.com/casey/just) command runner for developer commands
    1. To see all available commands, run `just list` or look at the [justfile](./.justfile) (useful even if you don't use just)
1. If you want to make changes to the Squid Dashboard, [install npm](https://docs.npmjs.com/downloading-and-installing-node-js-and-npm)
    1. Optionally, install [yarn](https://yarnpkg.com/getting-started/install) for faster package installation
1. We use [pre-commit](https://pre-commit.com/) to run automated linting, formatting, and other tests for code quality and consistency

If you use an IDE like Visual Studio Code and want a quick way to bootstrap your environment, consider taking advantage of the included [Dev Container](./.devcontainer).
See [Visual Studio Code Dev Container Documentation](https://code.visualstudio.com/docs/devcontainers/create-dev-container) or the [Development Container Documentation](https://containers.dev/) for more information on how to get started with Dev Containers in your IDE of choice.


### Running Automated Tests

1. Install locally using PDM or pip (see above)
1. Ensure you've activated any relevant virtual environments
1. Run `pytest` in the root directory of the repository
    1. To run only the tests for a specific component, such as the workcell manager, change directories into the relevant subdirectory in `src/`, or use `pytest -k EXPRESSION` to filter the tests by test name/parent class
1. Note that many of the pytests depend on docker to start mock database containers
