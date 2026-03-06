# Template Catalog

MADSci includes 26 built-in templates for scaffolding lab components. Browse templates with:

```bash
madsci new list                       # Show all templates
madsci new list --category module     # Filter by category
madsci new list --tag device          # Filter by tag
```

---

## Module Templates (6)

Templates for creating complete node module packages with server, interface(s), types, tests, and documentation.

### module/basic

**Minimal module with a single example action.**

```bash
madsci new module --template module/basic --name my_module
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `module_name` | string | `my_module` | Module name (lowercase, underscores) |
| `module_description` | string | `A MADSci node module` | Module description |
| `author_name` | string | | Author name |
| `port` | integer | `2000` | Default port (1024-65535) |
| `include_tests` | boolean | `true` | Include test scaffolding |
| `include_dockerfile` | boolean | `true` | Include Dockerfile |

### module/device

**Standard device module with lifecycle actions (initialize, shutdown, status) and resource management.**

```bash
madsci new module --template module/device --name my_device
```

Parameters: Same as module/basic (default name: `my_device`).

### module/instrument

**Measurement instrument module with calibration and data acquisition actions.**

```bash
madsci new module --template module/instrument --name my_instrument
```

Parameters: Same as module/basic (default name: `my_instrument`).

### module/liquid_handler

**Liquid handling module with aspirate, dispense, and transfer actions.**

```bash
madsci new module --template module/liquid_handler --name my_liquid_handler
```

Parameters: Same as module/basic (default name: `my_liquid_handler`).

### module/camera

**Camera/vision system module with image capture and configuration actions.**

```bash
madsci new module --template module/camera --name my_camera
```

Parameters: Same as module/basic (default name: `my_camera`).

### module/robot_arm

**Robot arm module with pick, place, move, and home actions for material handling.**

```bash
madsci new module --template module/robot_arm --name my_robot_arm
```

Parameters: Same as module/basic (default name: `my_robot_arm`).

---

## Interface Templates (4)

Templates for adding interface variants to existing modules.

### interface/fake

**In-memory simulation interface for testing without hardware.**

```bash
madsci new interface --type fake
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `module_name` | string | `my_module` | Module name |
| `simulated_latency` | float | `0.1` | Simulated operation latency in seconds (0.0-60.0) |

### interface/real

**Real hardware interface stub with connection lifecycle and error handling patterns.**

```bash
madsci new interface --type real
# or: madsci new module  (included by default in module templates)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `module_name` | string | `my_module` | Module name |
| `connection_type` | string | `tcp` | Connection type |

### interface/sim

**Interface for connecting to an external device simulator (e.g., Omniverse).**

```bash
madsci new interface --type sim
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `module_name` | string | `my_module` | Module name |
| `simulator_url` | string | `http://localhost:9000` | Simulator URL |

### interface/mock

**Pytest mock-based interface for unit testing.**

```bash
madsci new interface --type mock
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `module_name` | string | `my_module` | Module name |

---

## Node Templates (1)

### node/basic

**Standalone REST node server for an existing interface.**

```bash
madsci new node --name my_device --interface-module my_device.interface
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `node_name` | string | `my_node` | Node name |
| `node_description` | string | `A MADSci REST node` | Node description |
| `port` | integer | `2000` | Default port (1024-65535) |

---

## Experiment Templates (4)

Templates for different experiment execution modalities.

### experiment/script

**Simple run-once experiment script using ExperimentScript modality.**

```bash
madsci new experiment --modality script --name my_study
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `experiment_name` | string | `my_experiment` | Experiment name |
| `experiment_description` | string | `A MADSci experiment` | Description |
| `author_name` | string | | Author name |

### experiment/notebook

**Interactive Jupyter notebook experiment using ExperimentNotebook modality.**

```bash
madsci new experiment --modality notebook --name my_analysis
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `experiment_name` | string | `my_experiment` | Experiment name |
| `experiment_description` | string | `A MADSci notebook experiment` | Description |
| `author_name` | string | | Author name |
| `lab_server_url` | string | `http://localhost:8000/` | Lab server URL |

### experiment/tui

**Interactive terminal UI experiment using ExperimentTUI modality.**

```bash
madsci new experiment --modality tui --name my_interactive
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `experiment_name` | string | `my_experiment` | Experiment name |
| `experiment_description` | string | `A MADSci experiment` | Description |
| `author_name` | string | | Author name |

### experiment/node

**REST API server experiment using ExperimentNode modality.**

```bash
madsci new experiment --modality node --name my_service
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `experiment_name` | string | `my_experiment` | Experiment name |
| `experiment_description` | string | `A MADSci server experiment` | Description |
| `author_name` | string | | Author name |
| `server_port` | integer | `6000` | Server port (1024-65535) |

---

## Workflow Templates (2)

### workflow/basic

**Simple single-step workflow.**

```bash
madsci new workflow --name sample_transfer
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `workflow_name` | string | `my_workflow` | Workflow name |
| `workflow_description` | string | `A MADSci workflow` | Description |
| `node_name` | string | `example_node` | Target node name |
| `action_name` | string | `example_action` | Action to execute |

### workflow/multi_step

**Multi-step workflow with sequential node actions.**

```bash
madsci new workflow --template workflow/multi_step --name process_pipeline
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `workflow_name` | string | `my_workflow` | Workflow name |
| `workflow_description` | string | `A multi-step MADSci workflow` | Description |
| `node_1_name` | string | `node_1` | First node name |
| `node_1_action` | string | `action_1` | First action |
| `node_2_name` | string | `node_2` | Second node name |
| `node_2_action` | string | `action_2` | Second action |

---

## Workcell Templates (1)

### workcell/basic

**Basic workcell configuration for coordinating multiple nodes.**

```bash
madsci new workcell --name my_lab_workcell
madsci new workcell --nodes liquidhandler,platereader,incubator
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `workcell_name` | string | `my_workcell` | Workcell name |
| `workcell_description` | string | `A MADSci workcell` | Description |

---

## Lab Templates (3)

### lab/minimal

**Minimal lab configuration with no Docker required.**

```bash
madsci new lab --template minimal --name my_research_lab
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `lab_name` | string | `my_lab` | Lab name |
| `lab_description` | string | `A MADSci self-driving laboratory` | Description |

### lab/standard

**Standard lab with all managers and Docker Compose infrastructure.**

```bash
madsci new lab --template standard --name my_lab
```

Parameters: Same as lab/minimal.

### lab/distributed

**Distributed lab configuration for multi-host deployments.**

```bash
madsci new lab --template distributed --name production_lab
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `lab_name` | string | `my_lab` | Lab name |
| `lab_description` | string | `A distributed MADSci self-driving laboratory` | Description |

---

## Communication Templates (5)

Templates for instrument communication interfaces, used within node modules.

### comm/serial

**Serial port communication using pySerial patterns.**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `interface_name` | string | `my_serial` | Interface name |
| `interface_description` | string | `A serial port communication interface` | Description |

### comm/socket

**TCP/UDP socket communication interface.**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `interface_name` | string | `my_socket` | Interface name |
| `interface_description` | string | `A socket communication interface` | Description |

### comm/rest

**REST API client for HTTP-based instrument communication.**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `interface_name` | string | `my_rest_client` | Interface name |
| `interface_description` | string | `A REST API client interface` | Description |

### comm/sdk

**Vendor SDK wrapper for instrument communication.**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `interface_name` | string | `my_sdk` | Interface name |
| `interface_description` | string | `A vendor SDK wrapper interface` | Description |

### comm/modbus

**Modbus TCP/RTU communication using pymodbus patterns.**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `interface_name` | string | `my_modbus` | Interface name |
| `interface_description` | string | `A Modbus communication interface` | Description |

---

## Summary

| Category | Count | Templates |
|----------|-------|-----------|
| Module | 6 | basic, device, instrument, liquid_handler, camera, robot_arm |
| Interface | 4 | fake, real, sim, mock |
| Node | 1 | basic |
| Experiment | 4 | script, notebook, tui, node |
| Workflow | 2 | basic, multi_step |
| Workcell | 1 | basic |
| Lab | 3 | minimal, standard, distributed |
| Communication | 5 | serial, socket, rest, sdk, modbus |
| **Total** | **26** | |
