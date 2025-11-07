# MADSci Experiment Application

## Overview
The Experiment Application package provides a high-level class for managing automated and autonomous experiments using MADSci-powered laboratories. This package serves as the primary interface for scientists and researchers to design, execute, and monitor complex experimental campaigns.

## Key Components

### ExperimentApplication Class
- **experiment_application.py**: Main class providing experiment management capabilities
- High-level API for experiment design and execution
- Integration with all MADSci manager services
- Support for both automated and autonomous experimental workflows

## Core Features
- **Experiment Design**: Define experimental parameters, conditions, and objectives
- **Automated Execution**: Orchestrate complex multi-step experimental procedures
- **Autonomous Operation**: AI-driven experiment optimization and decision making
- **Real-time Monitoring**: Track experiment progress and intermediate results
- **Data Integration**: Seamless connection to data storage and analysis pipelines

## Experiment Types Supported
- **Screening Experiments**: High-throughput parameter screening
- **Optimization Campaigns**: Autonomous optimization of experimental conditions
- **Characterization Studies**: Systematic material or process characterization
- **Method Development**: Automated method validation and refinement
- **Quality Control**: Routine testing and validation procedures

## Integration Capabilities
- **Manager Services**: Full integration with all MADSci managers
- **Laboratory Hardware**: Direct control of instruments via node modules
- **Analysis Tools**: Integration with data analysis and machine learning pipelines
- **External Systems**: Connection to LIMS, databases, and third-party tools

## Usage Patterns
```python
from madsci.experiment_application import ExperimentApplication

# Initialize experiment application
app = ExperimentApplication(lab_config="my_lab.yaml")

# Design and execute experiment
experiment = app.create_experiment("optimization_campaign")
app.execute_experiment(experiment_id=experiment.id)
```

## Configuration
- Laboratory configuration files (YAML)
- Experiment templates and protocols
- Hardware and node specifications
- Analysis pipeline definitions
