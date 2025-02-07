# Modular Autonomous Discovery for Science (MADSci)

## 🚧Under Construction🚧

MADSci is currently in the very early stages of development. We're planning to have an Alpha release shortly.

If you're looking to start building your autonomous lab and just can't wait, consider taking a look at MADSci's predecessor, [the Workflow Execution Interface](https://github.com/AD-SDL/wei)

## Overview

MADSci is a modular, autonomous, and scalable framework for scientific discovery and experimentation. It aims to provide:

- Laboratory Instrument Automation and Integration via the MADSci Node standard. Developers can implement Node modules in any language that can then be integrated into a MADSci system using a common interface standard (currently supports REST-based communication)
- Workflow Management, allowing users to define and run flexible scientific workflow's that can leverage one or more Nodes to complete complex tasks.
- Experiment Management, conducting flexible closed loop autonomous experiments by combining multiple workflow runs, as well as any compute, decision making, data collection, and analysis as needed.
- Resource Management, allowing robust tracking of all the labware, consumables, equipment, samples, and assets used in the autonomous laboratory
- Event Management, enabling distributed logging and event handling across every part of the autonomous lab.
- Data Management, collecting and storing data created by instruments or analysis as part of an experiment.

## Documentation

MADSci is made up of a number of different modular components, each of which can be used independently to fulfill specific needs, or composed to build more complex and capable systems. Below we link to specific documentation for each system component.

- [Clients](./src/madsci_client/README.md): A collection of clients for interacting with different parts of MADSci
- [Event Manager](./src/madsci_event_manager/README.md): handles distributed event logging and querying across a distributed lab.
- []


## Getting Started with MADSci

TODO
