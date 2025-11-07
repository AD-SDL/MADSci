# MADSci Node Module

## Overview
The Node Module package provides the framework for creating laboratory instrument nodes. It defines the interfaces and base classes that allow scientific instruments to integrate with the MADSci ecosystem for automated laboratory operations.

## Key Components

### Abstract Base Classes
- **abstract_node_module.py**: Base class defining the node interface and common functionality
- **AbstractNodeModule**: Core abstract class that all instrument nodes must inherit from
- Standardized action patterns and state management
- Built-in health monitoring and diagnostics

### REST Implementation
- **rest_node_module.py**: REST-based node implementation using FastAPI
- HTTP/REST API endpoints for node communication
- Automatic OpenAPI documentation generation
- Standard error handling and response formatting

### Utilities
- **helpers.py**: Common utilities and helper functions for node development
- Parameter validation and serialization
- Location handling and resource management
- Action execution utilities and error handling

## Node Development Pattern
All laboratory instrument nodes follow this pattern:

1. **Inherit from AbstractNodeModule**:
```python
from madsci.node_module import AbstractNodeModule

class MyInstrumentNode(AbstractNodeModule):
    def __init__(self, settings: NodeSettings):
        super().__init__(settings)
```

2. **Implement Required Action Methods**:
- Define instrument-specific actions (e.g., measure, move, dispense)
- Handle action parameters and validation
- Return structured action results

3. **Configuration**:
- YAML configuration files define node capabilities
- Action definitions with parameters and return types
- Hardware connection settings

## Node Types Supported
- **Analytical Instruments**: Spectrometers, chromatographs, microscopes
- **Liquid Handlers**: Pipetting robots, dispensers, pumps
- **Sample Handling**: Robot arms, conveyor systems, storage systems
- **Environmental Control**: Incubators, furnaces, atmosphere control
- **Measurement Devices**: Sensors, meters, monitoring equipment

## Communication Protocols
- **REST/HTTP**: Standard REST API using FastAPI framework
- **WebSocket**: Real-time communication for streaming data
- **Custom Protocols**: Support for instrument-specific communication

## Action Framework
- **Synchronous Actions**: Immediate execution with direct response
- **Asynchronous Actions**: Long-running operations with status tracking
- **Parameter Validation**: Type checking and constraint validation
- **Error Handling**: Structured error responses with diagnostic information

## Testing Framework
- Mock node implementations for testing
- Integration test utilities
- Hardware simulation capabilities
- Automated API testing tools
