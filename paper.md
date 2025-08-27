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
MADSci and its predecesor have enabled autonomous science in domains including Biology, Chemistry, materials science, and quantum science. 

# Statement of Need

The existing software ecosystem for lab automation and autonomous discovery is highly fragmented and inconsistent. Many existing solutions are proprietary, expensive, or closed source (Chemspeed Autosuite and Arksuite [citation], Retisoft Genera [citation], Cellario [citation]); or are targeted at specific experimental domains, problems, or setups (AlabOS [citation], ChemOS [citation], BlueSky [citation], Polybot [citation]). 
MADSci aims to provide a flexible, domain-agnostic, and modular set of open source tools for handling the complexity of autonomous experimental setups and self driving labs
To achieve this, it supports integrating arbitrary equipment, devices, sensors, and robots as "nodes", and provides "managers" for handling common functionality such as workflow orchestration and scheduling, resource management and inventory tracking, experimental campaigns, events and logging, and data collection.
In order to be adaptable and flexible to the wide diversity of needs and challenges in lab autonomy, MADSci is implemented with a microservices architecture, as a collection of RESTful OpenAPI servers, with Python clients provided to interface easily with any part of the system, backed by standard databases (PostgreSQL, MongoDB, Redis, MiniIO) and open source Python libraries (FastAPI, Pydantic, SQLModel).

## Software Architecture and Features

Below we describe the modular, composable, distributed microservice-based architecture of MADSci, which focuses on enabling separation of concerns for different system components.

<!-- if there's something in the figure we don't mention, it should not be included in the figure -->
![MADSci Architecture Diagram.\label{fig:madsci_architecture}](assets/drawio/madsci_architecture.drawio.svg)
Figure 1: Schematic architecture diagram for MADSci

### Nodes

MADSci enables modular integration of lab equipment, devices, robots, sensors, and other components needed to operate an automated or self driving lab via the MADSci Nodes API (see Fig. 1).

Any software which implements a subset of common endpoints, summarized below, can be used as a MADSci Node; in addition, we provide a `RestNode` Python class which can be extended to easily integrate a new device.

- `/action`: allows `POST` requests to invoke specific functionality of the controlled device or service
- `/status`: retrieves information about current node status, such as whether busy, idle, or in an error state.
- `/state`: allows the node to publish arbitrary state information related to the integrated device or service.
- `/admin`: supports administrative commands, such as cancelling, pausing, or resuming a current action, or safety stopping the device
- `/info`: allows the node to publish structured metadata about the controlled device or service and its capabilities

While we provide and support a RESTful implementation of the MADSci Node API standard, we also have implemented an `AbstractNode` and `AbstractNodeClient` with the intention of enabling and eventually supporting additional implementations. The MADSci node approach is compatible with the commonly used SiLA2 device communication standard.

### Workcell and Workflow Management

The MADSci Workcell Manager handles the operation of a **Workcell**--a collection of **Nodes**, **Locations**, and **Resources** that are scheduled together--to perform **Workflows**. A self-driving lab may consist of one or more Workcells, with each Workcell able to execute workflows semi-independently.

At the core of the workcell manager is the scheduler, which determines which steps in one or more workflows to run next based on the current state of the workcell's constituent nodes, locations, and resources.
This scheduler is a modular component of the workcell manager that is designed to be swapped out by the lab operator to meet the specific requirements of their lab.
We include a straightforward opportunistic first-in-first-out scheduler as a default.

Workflows can be defined using a straightforward YAML syntax, or as Pydantic-based Python data models.
In either case, a workflow consists of a linear sequence of steps to be run on individual nodes.
A Step Definition includes the node to run on, the specific action to take, and any required or optional arguments for that action.
In addition to standard JSON-serializable arguments, workflow steps can include Location or File arguments.
The value of location arguments are provided by the Workcell at runtime, and the WorkcellManager substitutes an appropriate representation.

Finally, Workflows are parameterizable, allowing users to specify the node, action, or arguments for certain steps at submission time.
This enables reusable template workflows.
Optionally, the output from previous steps can inform parameter values for later steps, allowing simple intra-workflow data flow.

### Event Management and Logging

We implement an Event Manager, which allows nodes and other managers to log JSON-based events to a central event tracking and storage system.
Our EventClient implementation also supports logging to local terminal output and log files, based on Python's native logging library, providing users with familiar syntax and usage patterns, as well as the ability to easily convert existing Python logging to use the Event Manager.
The Event Manager is backed by MongoDB, a document-based database, and supports advanced querying using Mongo's query selectors.

### Resource Management

Most autonomous laboratories involve various consumables, labware, and other trackable assets.
Often, these physical resources are collected into different containers.
We provide a Resource Manager to support flexible and distributed definition, templating, validation, instantiation, tracking, and lifecycle management of these resources.
Backed by PostgreSQL, our implementation supports numerous types of assets, containers, and consumables, as well as nested resources inside of containers. It is designed to be flexible, allowing users to define the properties of specific resources, while also providing a rich library of verbs for interacting with these resources in a standardized fashion.
Finally, we provide automated history and resource locking functionality to help ensure data provenance and robustness.

### Experiment Management

- Campaigns, Experiment Designs, Experiment Runs
- `ExperimentApplication`

MADSci's Experiment Manager allows users to define experimental campaigns, start experiment runs associated with those campaiagns, and link MADSci objects (workflows, resources, datapoints, etc) with experimental runs.
The Experiment Manager supports Experiment Designs, which allow users to specify properties and conditions of experiments.
Finally, an `ExperimentApplication` classmprovides a foundation for defining autonomous experimental applications, including all clients needed to interact with a MADSci-powered lab and helper functions for common autonomous experimental needs.

### Data Management

MADSci's Data Manager supports the creation, storage, and querying of data generated during autonomous experimentation from any component of the autonomous laboratory.
The Data Manager currently supports the storage and querying of JSON-serializable data directly in MongoDB, storing file-based data either on a filesystem or in S3-compatible object storage.
When working with large data where unneccesary data transfer is undesirable, the `DataClient` implementation optionally supports direct upload to object storage.

---

# Acknowledgements

The authors acknowledge financial support from Laboratory Directed Research and Development (LDRD) funding from Argonne National Laboratory, provided by the Director, Office of Science, of the U.S. Department of Energy under Contract No. DE-AC02-06CH11357.

# References
