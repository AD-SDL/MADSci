# MADSci SQUID (Lab Manager)

## Overview
MADSci SQUID serves as the central lab configuration manager and dashboard provider. It acts as the "brain" of the laboratory, coordinating between all manager services and providing a unified interface for laboratory operations and monitoring.

## Key Responsibilities
- **Lab Configuration**: Central management of laboratory setup and configuration
- **Service Orchestration**: Coordinate communication between all MADSci manager services
- **Dashboard Provider**: Serve the primary laboratory monitoring and control interface
- **System Health**: Monitor overall system health and service availability
- **Central Control**: Provide unified control interface for laboratory operations

## Server Architecture
- **lab_server.py**: Main FastAPI server providing lab management and dashboard endpoints
- Central hub for inter-service communication
- Health monitoring and service discovery
- Configuration distribution to other services

## Core Features
- **Laboratory Configuration**: Define and manage lab topology, instruments, and workflows
- **Service Discovery**: Automatic detection and registration of MADSci services
- **Health Monitoring**: Real-time monitoring of all system components
- **Dashboard Backend**: Serve data and endpoints for the Vue.js dashboard
- **Administrative Controls**: System-wide administrative commands and controls

## Dashboard Integration
- **Vue.js Frontend**: Integration with the Vue 3 + Vuetify dashboard in `ui/`
- **Real-time Updates**: WebSocket connections for live data streaming
- **API Endpoints**: REST API for dashboard data retrieval and operations
- **User Interface**: Centralized interface for all laboratory operations

## Configuration Management
- **Lab Topology**: Define laboratory layout, locations, and equipment
- **Service Configuration**: Coordinate configuration across all manager services
- **Node Registration**: Register and manage laboratory instrument nodes
- **Workflow Templates**: Manage reusable workflow templates and protocols

## API Endpoints
- Laboratory status and health monitoring
- Service discovery and registration
- Configuration management and distribution
- Dashboard data endpoints
- Administrative control operations

## Configuration
Environment variables with `LAB_` or `SQUID_` prefix:
- Service discovery settings
- Dashboard configuration
- Laboratory topology definitions
- Administrative control parameters

## Integration Points
- **All Managers**: Central coordination point for all MADSci services
- **Dashboard UI**: Backend for the web-based laboratory interface
- **Node Modules**: Registration and management of laboratory instruments
- **External Systems**: Integration with laboratory infrastructure and LIMS
