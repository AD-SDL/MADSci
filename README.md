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

## Roadmap

We're working on bringing the following additional components to MADSci:

- **Notification Manager**: For handling notifications related to an automated or autonomous lab.
- **Auth Manager**: For handling authentication and user and group management for an autonomous lab.
- **Transfer Manager**: For coordinating resource movement in a lab.

## Getting Started with MADSci

To get started with MADSci, we recommend checking out our [MADSci Examples Repository](https://github.com/AD-SDL/MADSci_Examples). There you'll find Jupyter Notebooks walking through the core concepts and how to leverage MADSci to build your autonomous laboratory and experiments.
