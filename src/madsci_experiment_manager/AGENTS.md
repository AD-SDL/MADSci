# MADSci Experiment Manager

## Overview
The Experiment Manager (Port 8002) handles experimental runs and campaigns management. It provides comprehensive tracking and coordination of scientific experiments from design through completion, including campaign-level orchestration of multiple related experiments.

## Key Responsibilities
- **Experiment Lifecycle**: Manage experiments from creation to completion
- **Campaign Management**: Coordinate multi-experiment campaigns and studies
- **Progress Tracking**: Monitor experiment status and milestone completion
- **Results Integration**: Collect and organize experimental results and outcomes
- **Scheduling Coordination**: Work with Workcell Manager for experiment scheduling

## Server Architecture
- **experiment_server.py**: Main FastAPI server providing experiment management endpoints
- REST API for experiment and campaign operations
- Integration with workflow execution systems
- Database storage for experiment metadata and results

## Core Features
- **Experiment Creation**: Define experimental parameters and protocols
- **Campaign Organization**: Group related experiments into cohesive campaigns
- **Status Monitoring**: Real-time tracking of experiment progress and health
- **Result Collection**: Automated gathering of experimental outputs and data
- **Reporting**: Generate experiment summaries and campaign reports

## Experiment States
- **Planned**: Experiment designed but not yet started
- **Queued**: Experiment scheduled for execution
- **Running**: Experiment currently in progress
- **Paused**: Temporarily halted execution
- **Completed**: Successfully finished experiment
- **Failed**: Experiment terminated due to errors
- **Cancelled**: User-initiated termination

## API Endpoints
- Experiment CRUD operations (create, read, update, delete)
- Campaign management and organization
- Status updates and progress reporting
- Result data association and retrieval
- Experiment scheduling and queue management

## Configuration
Environment variables with `EXPERIMENT_` prefix:
- Database connection settings
- Experiment storage locations
- Campaign organization rules
- Integration service URLs

## Integration Points
- **Workcell Manager**: Schedule and execute experimental workflows
- **Data Manager**: Store experimental results and measurements
- **Event Manager**: Log experiment lifecycle events
- **Resource Manager**: Track resource usage during experiments
