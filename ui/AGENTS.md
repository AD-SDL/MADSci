# MADSci Dashboard UI

## Overview
The MADSci Dashboard UI is a Vue 3 + Vuetify web application that provides a comprehensive interface for monitoring and controlling laboratory operations. It serves as the primary user interface for interacting with all MADSci manager services and laboratory instruments.

## Technology Stack
- **Vue 3**: Progressive JavaScript framework with Composition API
- **Vuetify**: Material Design component framework for Vue
- **TypeScript**: Type-safe JavaScript development
- **Vite**: Fast build tool and development server
- **Yarn**: Package manager for Node.js dependencies

## Key Components

### Core Application
- **App.vue**: Main application component and layout
- **main.ts**: Application entry point and Vue app initialization
- **store.ts**: Centralized state management using Vue reactivity
- **types.ts**: Global TypeScript type definitions

### Dashboard Components
- **Dashboard.vue**: Main dashboard overview and navigation
- **LabPanel.vue**: Laboratory status and control interface
- **NodesPanel.vue**: Laboratory instrument monitoring and control
- **ResourcesPanel.vue**: Resource inventory and management interface
- **LocationsPanel.vue**: Laboratory location and spatial management
- **WorkcellPanel.vue**: Workflow execution and monitoring
- **WorkflowsPanel.vue**: Workflow design and management interface
- **Experiments.vue**: Experiment tracking and campaign management

### Modal Components
- **NodeModal.vue**: Detailed node information and controls
- **ResourceModal.vue**: Resource details and operations
- **LocationModal.vue**: Location configuration and management
- **WorkflowModal.vue**: Workflow creation and editing
- **AddResourceModal.vue**: Resource creation interface
- **AddLocationModal.vue**: Location creation interface

### Administrative Controls
- **AdminButtons/**: Collection of administrative control components
  - **CancelButton.vue**: Cancel operations and workflows
  - **LockUnlockButton.vue**: System lock/unlock controls
  - **PauseResumeButton.vue**: Pause/resume operations
  - **ResetButton.vue**: System reset functionality
  - **SafetyStopButton.vue**: Emergency stop controls
  - **ShutdownButton.vue**: System shutdown interface

### Resource Management
- **ResourceComponents/**: Specialized resource display components
  - **Resource.vue**: Generic resource display component
  - **Consumable.vue**: Consumable resource interface
  - **Slot.vue**: Storage slot representation
  - **Stack.vue**: Stack-based resource organization
- **ResourceTable.vue**: Tabular resource display and management

### Workflow Components
- **CreateWorkflowPanel.vue**: Workflow creation interface
- **Workflow.vue**: Workflow display and monitoring
- **WorkflowTable.vue**: Tabular workflow management
- **Step.vue**: Individual workflow step representation
- **TransferGraph.vue**: Visual transfer and flow representation

### Event System
- **Event.vue**: Event display and monitoring component

## Configuration and Setup
- **package.json**: Node.js dependencies and scripts
- **vite.config.mts**: Vite build configuration
- **tsconfig.json**: TypeScript compiler configuration
- **yarn.lock**: Dependency lock file for reproducible builds

## Type System
- **types/**: TypeScript type definitions
  - **event_types.ts**: Event system type definitions
  - **experiment_types.ts**: Experiment and campaign types
  - **node_types.ts**: Laboratory instrument types
  - **workcell_types.ts**: Workflow execution types
  - **workflow_types.ts**: Workflow definition types

## Development Commands
```bash
yarn dev          # Start development server with hot reload
yarn build        # Build for production
yarn preview      # Preview production build
```

## Integration Points
- **MADSci SQUID**: Primary backend integration for dashboard data
- **All Manager Services**: Direct API integration for specialized operations
- **WebSocket**: Real-time data streaming and live updates
- **REST API**: Standard HTTP API for data retrieval and operations

## Features
- **Real-time Monitoring**: Live updates of laboratory status and operations
- **Interactive Controls**: Direct instrument control and workflow management
- **Responsive Design**: Mobile-friendly interface with adaptive layout
- **Type Safety**: Full TypeScript integration for reliable development
- **Component Library**: Reusable Vuetify components for consistent UI/UX
- **State Management**: Centralized application state with Vue reactivity
