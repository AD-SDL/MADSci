# MADSci SQUID (Lab Manager) - Agent Guide

## Overview
MADSci SQUID serves as the central lab configuration manager and dashboard provider. It acts as the coordination hub for all MADSci manager services and provides the web-based laboratory interface.

## Key Responsibilities
- **Lab Coordination**: Central management point for all MADSci services
- **Service Discovery**: Provides context and service URLs to other components
- **Dashboard Backend**: Serves the Vue.js dashboard for laboratory monitoring and control
- **Health Monitoring**: Monitors and reports health status of all lab services
- **Static File Serving**: Hosts dashboard UI files and provides web interface

## Architecture Details

### Server Implementation
- **Main File**: `madsci/squid/lab_server.py`
- **Class**: `LabManager` inheriting from `AbstractManagerBase`
- **Port**: 8000 (configurable via `LAB_SERVER_URL`)
- **Framework**: FastAPI with static file mounting for dashboard

### Key Features
- **Service Context**: Provides `/context` endpoint with all manager URLs
- **Lab Health**: Comprehensive health checking across all services
- **Dashboard Integration**: Serves Vue 3 + Vuetify dashboard files
- **Manager Coordination**: Central point for inter-service communication

## API Endpoints

### Core Endpoints
- `GET /context` - Returns all service URLs and lab configuration
- `GET /health` - Standard service health check
- `GET /lab_health` - Comprehensive lab-wide health status
- `GET /definition` - Lab definition and metadata

### Dashboard Integration
- Static files served from root `/` when dashboard path is configured
- HTML fallback routing for SPA navigation
- API routes take precedence over static file serving

## Configuration

### Environment Variables
Uses `LAB_` prefix for all configuration:
- `LAB_SERVER_URL` - Lab manager server URL (default: http://localhost:8000)
- `LAB_DASHBOARD_FILES_PATH` - Path to dashboard static files
- `LAB_DEFINITION` - Path to lab definition YAML file

### Service Discovery
Provides context with URLs for all manager services:
- Event Manager (port 8001)
- Experiment Manager (port 8002)
- Resource Manager (port 8003)
- Data Manager (port 8004)
- Workcell Manager (port 8005)
- Location Manager (port 8006)

### Lab Definition Format
```yaml
name: Lab_Name
description: Laboratory description
manager_type: lab_manager
manager_id: <ULID>  # Generate with new_ulid_str()
```

## Health Monitoring

### Health Check Algorithm
- Queries `/health` endpoint on all configured manager services
- Lab considered healthy if >50% of managers are healthy
- Returns detailed status for each manager service
- Uses 5-second timeout for health check requests

### Manager Integration
Lab Manager automatically discovers and monitors:
- All services with URLs in the MADSci context
- Services must respond to standard `/health` endpoint
- Failed services are marked with error descriptions

## Dashboard Features

### Frontend Integration
- Vue 3 + Vuetify dashboard served from static files
- Real-time monitoring of all lab components
- Administrative controls for lab operations
- Workflow management and resource tracking

### Static File Serving
- Dashboard files mounted at root path `/`
- Configurable via `LAB_DASHBOARD_FILES_PATH`
- Only serves files if directory exists and is configured

## Development Notes

### Testing
- Test file: `tests/test_lab_server.py`
- Run with: `pytest tests/test_lab_server.py`
- Tests server creation and basic functionality

### Common Operations
- Run standalone: `python -m madsci.squid.lab_server`
- Run with dashboard: Add `--lab-dashboard-files-path ./ui/dist`
- Docker deployment: Uses `ghcr.io/ad-sdl/madsci_dashboard` image

### Integration Points
- **All Managers**: Central coordination and service discovery
- **Node Modules**: Dashboard displays node status and controls
- **Workflow System**: Dashboard provides workflow management interface
- **Resource Management**: Dashboard shows resource inventory and tracking

## Important Notes
- Lab Manager sets global ownership context for the entire lab
- Uses ULID for all ID generation (not UUID)
- Health checks use HTTP requests with proper error handling
- Static file serving order matters - API routes registered first
- Configuration exclusively uses `LAB_` prefix (not `SQUID_`)
