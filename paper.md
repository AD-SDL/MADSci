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
It allows laboratory operators to define autonomous workcells as collections of *Nodes*, each controlling individual instruments, robots, or other devices.
These nodes, when combined with *Managers* that provide general lab functionality and coordination, form flexible, modular autonomous laboratories.
Lab users can then create and run experimental campaigns using simple Python applications and YAML workflow definitions.
This design allows a separation of expertise and concerns between device integrators, automated/autonomous lab operators, and domain and data scientists running automated, autonomous, and high-throughput experiments using them.
MADSci and its predecesor have enabled autonomous science in domains including biology, chemistry, materials science, and quantum science.

# Statement of Need

The lab automation ecosystem is fragmented, with many proprietary, costly, or narrowly domain-specific tools.
MADSci provides a flexible, open-source, easily extensible, and domain-agnostic toolkit for autonomous labs.
It integrates equipment, sensors, and robots as “nodes,” with modular managers for workflows, resources, experiments, logging, and data collection.
Built on a microservices architecture with developer-friendly RESTful APIs and Python clients, MADSci leverages standard databases (PostgreSQL, MongoDB, Redis, MiniIO) and open-source libraries (FastAPI, Pydantic, SQLModel) to ensure adaptability and extensibility.


## Software Architecture and Features

The modular, composable, distributed microservice-based MADSci architecture enables separation of concerns among different system components.

<!-- if there's something in the figure we don't mention, it should not be included in the figure -->
![MADSci Architecture Diagram.\label{fig:madsci_architecture}](assets/drawio/madsci_architecture.drawio.svg)
Figure 1: Schematic architecture diagram for MADSci

### Nodes

MADSci enables modular integration of lab equipment, devices, robots, sensors, and other components needed to operate an automated or self driving lab via the MADSci **Node** Protocol (see Fig. 1).

Any software which implements a subset of common API endpoints, summarized below, can be used as a MADSci Node; in addition, we provide a `RestNode` Python class which can be extended to easily integrate a new device.

- `/action`: accepts `POST` requests to invoke specific functionality of the controlled device or service
- `/status`: retrieves information about current node status, such as whether busy, idle, or in an error state.
- `/state`: allows the node to publish arbitrary state information related to the integrated device or service.
- `/admin`: supports administrative commands, such as cancelling, pausing, or resuming a current action, or safety stopping the device
- `/info`: publishes structured metadata about the controlled device or service and its capabilities

We provide and support a RESTful implementation of the MADSci Node API standard. We have also implemented an `AbstractNode` and `AbstractNodeClient` to enable additional implementations. The MADSci node approach is compatible with the commonly used SiLA2 device communication standard.

### Workcell and Workflow Management

The MADSci Workcell Manager handles the operation of a **Workcell**--a collection of **Nodes**, **Locations**, and **Resources** that are scheduled together--to perform **Workflows**. A self-driving lab may comprise one or more Workcells, each able to execute workflows semi-independently.

At the core of the workcell manager is the scheduler, which determines which steps in active workflow(s) to run next based on the current state of the workcell's nodes, locations, and resources.
A modular design allows this component to be swapped out by a lab operator to meet specific requirements of their lab.
We include a straightforward opportunistic first-in-first-out scheduler as a default.

Workflows can be defined using a straightforward YAML syntax, or as Pydantic-based Python data models.
In either case, a workflow consists of a linear sequence of steps to be run on individual nodes.
A Step Definition specifies a node, an action, and any (required or optional) action arguments.
In addition to standard JSON-serializable arguments, workflow steps can include Location or File arguments.
The values of location arguments are provided by the Workcell at runtime; the WorkcellManager substitutes an appropriate representation.

Workflows are parameterizable: users can specify the node, action, or arguments for certain steps at submission time.
This enables reusable template workflows.
The output from previous steps can inform parameter values for later steps, allowing simple intra-workflow data flow.

### Event Management and Logging

The MADSci Event Manager lets nodes and managers log JSON events to a central system backed by MongoDB, which supports advanced queries. The EventClient can also log to the terminal or files using Python’s standard logging library, making it easy to reuse existing Python logging code.

### Resource Management

Autonomous labs rely on consumables, labware, and other assets, often organized into containers.
Our Resource Manager provides flexible tools to define, validate, track, and manage these resources across their lifecycle.
Built on PostgreSQL, it supports many asset types, including nested resources, and lets users customize properties while interacting through a standardized set of operations.
It also maintains automated histories and locking to ensure provenance and reliability.


### Experiment Management

MADSci's Experiment Manager allows users to define experimental campaigns, start experiment runs associated with those campaigns, and link MADSci objects (workflows, resources, datapoints, etc) with experimental runs.
The Experiment Manager supports Experiment Designs, which allow users to specify the properties and conditions of experiments.

An included `ExperimentApplication` class provides a foundation for defining autonomous experimental applications using python, including all python clients needed to interact with a MADSci-powered lab and helper methods for common autonomous experimental needs.
This `ExperimentApplication` can be run either as a standard python script, or as a first class MADSci Rest node, allowing the user to define experiment-specific actions that can be included in workflows and started, stopped, or monitored from the Lab Dashboard.
Because it is a scaffolded python class, the `ExperimentApplication` is both powerful (making the entire capabilities of a MADSci-powered autonomous laboratory accessible) while also being simple and flexible, allowing users to easily combine MADSci's capabilities with other python tools, libraries, workflows, and scripts.

### Data Management

MADSci's Data Manager supports the creation, storage, and querying of data generated by any component of the system during autonomous experimentation.
The Data Manager currently supports the storage and querying of JSON-serializable data directly in MongoDB, storing file-based data either on a filesystem or in S3-compatible object storage.
When working with large datasets where extra transfer steps are undesirable, the `DataClient` implementation optionally supports direct upload to object storage.

### Lab Management

Finally, the MADSci Lab Manager provides a primary entrypoint to users and applications for a given MADSci-powered autonomous lab.
A web-based Dashboard provides both overview and detailed information on the lab's status, performance, and history.
Additionally, the lab manager's API surfaces important context about the lab, including information about what managers are available.

---

# Acknowledgements

The authors acknowledge financial support from Laboratory Directed Research and Development (LDRD) funding from Argonne National Laboratory, provided by the Director, Office of Science, of the U.S. Department of Energy under Contract No. DE-AC02-06CH11357.

# References
