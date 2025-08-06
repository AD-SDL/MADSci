---
title: ‘MADSci: A modular Python-based framework to enable autonomous science’
tags:
  - Python
  - laboratory autonomy
  - autonomy
  - automation
  - infrastructure
authors:
  - name: Ryan D. Lewis
    orcid: 0000-0002-3000-2811
    affiliation: 1
  - name: Tobias S. Ginsburg
    orcid: 0000-0001-5908-2782
    affiliation: 1
  - name: Doga Ozgulbas
    orcid: 0000-0003-3653-4779
    affiliation: 1
  - name: Casey Stone
    orcid: 0009-0006-9208-4046
    affiliation: 1
  - name: Abraham Stroka
    orcid: 0009-0001-9448-1583
    affiliation: 1
  - name: Ian T. Foster
    orcid: 0000-0003-2129-5269
    affiliation: “1, 2”
  - name: Noah Paulson
    orcid: 0000-0002-3548-9120
    corresponding: true
    affiliation: 1
affiliations:
  - name: Argonne National Laboratory, United States
    index: 1
  - name: University of Chicago, United States
    index: 2
date: XX Month 2025
bibliography: paper.bib
---

# Summary

The Modular Autonomous Discovery for Science (MADSci) toolkit is a modular, open source software framework for enabling laboratory automation, high-throughput experimentation, and self driving labs.
It allows laboratory operators to define an autonomous laboratory as a collection of Nodes, each controlling individual instruments, robots, or other devices.
These nodes—when combined with Managers that provide lab-wide functionality and coordination—form flexible, modular autonomous laboratories.
Lab users can then create and run experimental campaigns using simple python applications and YAML workflow definitions.
This design allows a separation of expertise and concerns between device integrators, automated/autonomous lab operators, and domain scientists running experiments on them.

# Statement of Need

The existing software ecosystem for lab automation and autonomous discovery is highly fragmented and inconsistent. Many existing solutions are proprietary, expensive, or closed source (Chemspeed Autosuite and Arksuite [citation], Retisoft Genera [citation], Cellario [citation]); or are targeted at specific experimental domains, problems, or setups (AlabOS, ChemOS, BlueSky, Polybot).
MADSci aims to provide a flexible, domain-agnostic, modular, set of open source tools for handling the complexity of autonomous experimental setups and self driving labs.
It supports integrating arbitrary equipment, devices, sensors, and robots as "nodes", and provides "managers" for handling common functionality such as workflow orchestration and scheduling, resource management and inventory tracking, experimental campaigns, events and logging, and data collection.
MADSci is implemented as a collection of modular RESTful OpenAPI servers, with python clients provided to easily interface with any part of the system, backed by standard databases (PostgreSQL, MongoDB, Redis, MiniIO) and open source python libraries (FastAPI, Pydantic, SQLModel).

## Software Architecture and Features

Briefly describe software architecture
Modular, composable, distributed microservice-based architecture with a focus on separation of concerns for different system components.
Managers provide broad cross-lab functionality, Nodes handle device-specific actions and state management.
Implemented with Python, RESTful/OpenAPI, and Docker. Heavy usage of Pydantic/JSON Schema for validation.

![MADSci Architecture Diagram.\label{fig:madsci_architecture}](assets/drawio/madsci_architecture.drawio.svg)

### Nodes

MADSci enables modular integration of lab equipment, devices, robots, sensors, or any other components necessary for the operation of an automated or self driving lab via MADSci Nodes.

Any software which implements a set of common endpoints, summarized below, can be used as a MADSci Node; in addition, we provide a `RestNode` Python class which can be extended to easily integrate a new device.

- `/action`: allows `POST` requests to invoke specific functionality of the controlled device or service
- `/status`: get information about the current status of the node, such as whether it is currently busy, idle, or in an error state.
- `/state`: allows the node to publish arbitrary state information related to the integrated device or service.
- `/admin`: supports receiving administrative commands, such as cancelling, pausing, or resuming a current action, or safety stopping the device
- `/info`: allows the node to publish structured metadata about the controlled device or service and its capabilities

### Workcell Management

- Orchestrate multiple nodes
- Modular scheduler
- Workflows
- Parameters, locations, feed-forward data

### Event Management and Logging

- Local and distributed logging
- JSON based event data

### Resource Management

- Distributed Resource Tracking
- Custom Resource Definitions/Templates
- Consumables vs. Assets
- Containers + different container types
- Resource History

### Experiment Management

- Campaigns, Experiment Designs, Experiment Runs
- `ExperimentApplication`

### Data Management

- JSON data, file storage (filesystem and S3 bucket support)

---

Briefly go through the various components/capabilities of the software
Managers
Automated/Autonomous Laboratory functionality and capabilities are provided by different independent Managers (RESTful Servers + databases/other dependencies)
Different Managers can be composed to provide the functionality required for operating a given facility
REST API and python clients available for all managers
Nodes
Provide standardized control interfaces individual robots/instruments/devices
Currently supports RESTful Node Server implementations
Allows sending actions, managing lifecycle, tracking status, and administrating devices
Workcells
Collection of co-scheduled Nodes and other resources that work in tandem to conduct scientific workflows
Controlled by a Workcell Manager
Make use of Nodes (charged with controlling individual devices/system components), Locations, and Resources
Experiments
Supports tracking and managing Experiment Runs and Campaigns
Experiment Applications implemented as python scripts to control and monitor system
Resources
Supports tracking any labware, consumables, or other physical resources across the system
Full history of all changes to the resources is maintained


Figures can be included like this:
![Caption for example figure.\label{fig:example}](figure.png)
and referenced from text using \autoref{fig:example}.

Figure sizes can be customized by adding an optional second parameter:
![Caption for example figure.](figure.png){ width=20% }

# Acknowledgements

The authors acknowledge financial support from Laboratory Directed Research and Development (LDRD) funding from Argonne National Laboratory, provided by the Director, Office of Science, of the U.S. Department of Energy under Contract No. DE-AC02-06CH11357.

# References
