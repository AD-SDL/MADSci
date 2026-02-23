---
title: "MADSci: A modular Python-based framework to enable autonomous science"
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
  - name: Aileen Cleary
    orcid: 0000-0002-5336-9026
    affiliation: 2
  - name: Ian T. Foster
    orcid: 0000-0003-2129-5269
    affiliation: '1, 3'
  - name: Noah Paulson
    orcid: 0000-0002-3548-9120
    corresponding: true
    affiliation: 1
affiliations:
  - index: 1
    name: Argonne National Laboratory, United States
  - index: 2
    name: Northwestern University, United States
  - index: 3
    name: University of Chicago, United States
date: 19 September 2025
bibliography: paper.bib
---

# Summary

The Modular Autonomous Discovery for Science (MADSci) toolkit enables laboratory automation, high-throughput experimentation, and self-driving labs.
MADSci provides a microservices architecture integrating laboratory instruments, robots, and devices with coordination services for workflows, data management, and resource tracking.
Users define and execute experiments using Python applications and YAML-based workflow definitions.
This modular design separates concerns between device integrators, lab operators, and domain scientists.
MADSci supports research in biology, chemistry, materials science, and quantum science.

# Statement of Need

The lab automation ecosystem is fragmented, with many proprietary, costly, or narrowly domain-specific tools.
MADSci provides an open-source, extensible, domain-agnostic toolkit integrating equipment, sensors, and robots as "nodes" with managers for workflows, resources, experiments, logging, and data collection.
Built on a microservices architecture with RESTful APIs and Python clients, MADSci leverages standard databases (PostgreSQL, MongoDB, Redis, MiniIO) and open-source libraries (FastAPI, Pydantic, SQLModel).

Commercial platforms such as Chemspeed's Autosuite [@seifrid2024chemspyd] and Retisoft Genera [@retisoft2024genera] provide comprehensive functionality but operate under proprietary licensing that may limit academic accessibility.
Open-source alternatives including AlabOS [@fei2024alabos], ChemOS [@sim2024chemos; @roch2020chemos], and Bluesky [@allan2019bluesky] demonstrate strong capabilities within specific domains but exhibit varying cross-disciplinary transferability.
Specialized systems such as Polybot [@wang2025autonomous; @vriza2023selfdriving] showcase advanced features tailored to particular applications.
The Workcell Execution Interface [@vescovi2023modular], MADSci's predecessor, emphasizes instrument modularity but lacks advanced features and microservices principles at the management layer.
MADSci provides domain-agnostic laboratory automation while maintaining compatibility with diverse instrumentation and institutional requirements.

## Software Architecture and Features

MADSci's microservice architecture enables separation of concerns among system components.

![Schematic architecture diagram for MADSci, depicting the relationship between devices, nodes, managers, and users (via experiment applications and the web-based dashboard).\label{fig:madsci_architecture}](assets/drawio/madsci_architecture.png)

### Nodes

A node provides a standardized interface to a laboratory instrument, device, robot, or sensor \autoref{fig:madsci_architecture}.
Any software implementing standard API endpoints can function as a node.
We provide a `RestNode` Python class for device integration.
Key endpoints include `/action` for device functionality, `/status` for node state, `/state` for device information, `/admin` for administrative commands, and `/info` for metadata and capabilities.

### Workcell and Workflow Management

A workcell represents a collection of nodes, physical locations, and resources coordinated to execute experimental procedures.
A workflow is a sequence of steps directing nodes to perform specific actions with specified parameters.
A self-driving lab may comprise one or more workcells, each executing workflows semi-independently.

The Workcell Manager coordinates operation through a scheduler determining which workflow steps to execute based on current node, location, and resource states.
This modular scheduler can be customized by lab operators; we include an opportunistic first-in-first-out scheduler as default.

Workflows are defined using YAML syntax or Pydantic-based Python data models as linear sequences of steps.
Each step specifies a target node, an action, and required or optional arguments.
Beyond JSON-serializable arguments, steps can reference physical locations or files, with the Workcell Manager resolving location references at runtime.

Workflows support parameterization: users specify node, action, or arguments at submission time, enabling reusable templates.
Outputs from earlier steps can inform later parameter values, allowing intra-workflow data flow.

### Experiment Management

An experiment run represents a single execution of an experimental procedure, tracking associated workflows, resources, data, and metadata.
The Experiment Manager enables users to define experiments, initiate runs, and link MADSci objects (workflows, resources, datapoints) with those runs.
It supports experiment designs specifying properties and conditions under which experiments are conducted.

The included `ExperimentApplication` class provides a foundation for defining experimental applications in Python with client libraries and helper methods for common tasks.
This class runs as a Python script or MADSci node, enabling experiment-specific actions within workflows monitored from the Lab Dashboard.
This design makes laboratory capabilities accessible to domain scientists while remaining flexible for integration with other Python tools.

### Data Management

The Data Manager supports creation, storage, and querying of data generated during autonomous experimentation.
It stores JSON-serializable data in MongoDB and file-based data on filesystems or S3-compatible object storage.
For large datasets, the `DataClient` optionally supports direct upload to object storage.

### Resource Management

Many laboratories, particularly in chemistry and biology, require tracking physical resources such as consumables, labware, and samples.
The Resource Manager provides optional capabilities to define, validate, track, and manage these assets across their lifecycle.
Built on PostgreSQL, it supports diverse asset types and hierarchical organization with customizable properties and standardized operations.
It maintains automated histories and locking mechanisms for provenance and reliability.
Laboratories without such needs can utilize other MADSci components independently.

### Location Management

The Location Manager provides optional tracking of physical laboratory locations and their associations with resources.
Locations represent positions such as instrument slots, storage areas, or transfer stations within the laboratory environment.

This manager integrates with the Resource Manager to enable attachment of resources to specific locations, facilitating automated tracking of sample positions and consumable storage.
Workflows can reference locations symbolically, with the Workcell Manager resolving these references at runtime based on current attachments and states.
This abstraction separates physical laboratory layout from workflow logic, improving workflow portability across different laboratory configurations.

Laboratories not requiring location tracking can utilize other MADSci components independently.

### Event Management and Logging

The Event Manager enables nodes and managers to log JSON events to a central MongoDB-backed system supporting advanced queries.
The EventClient can also log to terminals or files using Python's standard logging library, facilitating reuse of existing logging code.

### Lab Management

The Lab Manager provides a primary entrypoint for users and applications.
A web-based Dashboard provides overview and detailed information on lab status, performance, and history.
The Lab Manager API surfaces context about available managers and lab configuration.

---

# Acknowledgements

The authors acknowledge financial support from Laboratory Directed Research and Development (LDRD) funding from Argonne National Laboratory, provided by the Director, Office of Science, of the U.S. Department of Energy under Contract No. DE-AC02-06CH11357.

# References
