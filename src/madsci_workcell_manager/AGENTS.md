# MADSci Workcell Manager

## Overview
The Workcell Manager (Port 8005) handles workflow coordination and scheduling. It serves as the execution engine for complex laboratory workflows, managing the orchestration of multiple instruments, resources, and processes to accomplish experimental objectives.

## Key Components

### Core Server
- **workcell_server.py**: Main FastAPI server providing workflow execution and scheduling endpoints
- REST API for workflow operations and monitoring
- Integration with all manager services for comprehensive workflow execution

### Workflow Engine
- **workcell_engine.py**: Core workflow execution engine
- **workflow_utils.py**: Workflow processing and manipulation utilities
- **workcell_utils.py**: General workcell operation utilities
- State machine-based workflow execution
- Support for complex branching and conditional logic

### Scheduling System
- **schedulers/**: Pluggable scheduling system
  - **scheduler.py**: Abstract scheduler interface
  - **default_scheduler.py**: Default FIFO scheduling implementation
- Resource-aware scheduling
- Priority-based workflow queuing
- Conflict resolution and optimization

### State and Action Management
- **state_handler.py**: Workflow and step state management
- **workcell_actions.py**: Action execution and coordination
- **condition_checks.py**: Conditional logic evaluation for workflow branching
- Real-time state tracking and updates
- Error handling and recovery mechanisms

## Workflow Execution Features
- **Multi-Step Workflows**: Complex sequences of laboratory operations
- **Parallel Execution**: Concurrent operation of independent workflow branches
- **Conditional Logic**: Dynamic branching based on experimental results
- **Error Recovery**: Automatic retry and error handling mechanisms
- **Resource Scheduling**: Intelligent allocation of laboratory resources

## Workflow Types Supported
- **Sequential Workflows**: Step-by-step experimental procedures
- **Parallel Workflows**: Simultaneous execution of independent operations
- **Conditional Workflows**: Dynamic workflows that adapt based on results
- **Iterative Workflows**: Loops and repeated operations
- **Nested Workflows**: Sub-workflows within larger experimental protocols

## Scheduling Capabilities
- **Priority Queuing**: Workflow prioritization and urgent processing
- **Resource Optimization**: Efficient allocation of shared resources
- **Conflict Resolution**: Handle resource contention and scheduling conflicts
- **Load Balancing**: Distribute workload across available instruments
- **Time-based Scheduling**: Schedule workflows for specific time windows

## API Endpoints
- Workflow submission and management
- Real-time execution monitoring and status
- Scheduling and queue management
- Resource allocation and tracking
- Performance metrics and reporting

## Configuration
Environment variables with `WORKCELL_` prefix:
- Scheduling algorithm parameters
- Resource allocation settings
- Workflow execution timeouts
- Integration service configurations

## Integration Points
- **Experiment Manager**: Execute experimental workflows and campaigns
- **Resource Manager**: Reserve and allocate laboratory resources
- **Location Manager**: Coordinate resource movements and positioning
- **Node Modules**: Direct control of laboratory instruments
- **Event Manager**: Log workflow execution events and status changes
