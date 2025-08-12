# MADSci Dashboard

Vue 3 + Vuetify web dashboard for monitoring and controlling MADSci-powered laboratories.

## Features

- **Real-time Lab Monitoring**: Live status updates from all lab components
- **Workcell Management**: View, control, and submit workflows to workcells
- **Resource Tracking**: Browse inventory, manage containers, track consumables
- **Experiment Oversight**: Monitor campaigns, runs, and experimental progress
- **Node Control**: Send administrative commands to laboratory instruments
- **Responsive Design**: Works on desktop and mobile devices

## Development Setup

### Prerequisites
- Node.js 16+ and npm
- MADSci lab services running (for API integration)

### Quick Start

```bash
# Install dependencies
npm install

# Start development server
npm run dev
# Dashboard available at http://localhost:3000

# Build for production
npm run build
# Output in ./dist/ directory
```

### Development Commands

```bash
npm run dev        # Start Vite dev server with hot reload
npm run build      # Build for production
npm run preview    # Preview production build locally
```

## Architecture

### Technology Stack
- **Vue 3**: Progressive JavaScript framework with Composition API
- **Vuetify 3**: Material Design component library
- **TypeScript**: Type-safe JavaScript development
- **Vite**: Fast build tool and dev server
- **Pinia**: State management (via `store.ts`)

### Project Structure
```
ui/
├── src/
│   ├── components/          # Vue components
│   │   ├── Dashboard.vue    # Main dashboard layout
│   │   ├── *Panel.vue       # Tab panels (Workcells, Resources, etc.)
│   │   ├── *Modal.vue       # Popup dialogs and forms
│   │   └── AdminButtons/    # Control buttons for nodes/workcells
│   ├── store.ts            # Global state management
│   ├── main.ts             # Application entry point
│   └── App.vue             # Root component
├── public/                 # Static assets
├── package.json            # Dependencies and scripts
└── vite.config.mts         # Vite configuration
```

## Core Components

### Dashboard Layout
The main dashboard uses a tabbed interface:

```vue
<!-- Dashboard.vue structure -->
<v-tabs>
  <v-tab>Workcells</v-tab>    <!-- WorkcellPanel.vue -->
  <v-tab>Workflows</v-tab>    <!-- WorkflowsPanel.vue -->
  <v-tab>Resources</v-tab>    <!-- ResourcesPanel.vue -->
  <v-tab>Experiments</v-tab>  <!-- Experiments.vue -->
</v-tabs>
```

### State Management
Global state is managed via Pinia store:

```typescript
// store.ts patterns
interface LabState {
  context: MadsciContext
  workcells: Workcell[]
  workflows: Workflow[]
  resources: Resource[]
  // ... other lab state
}

// Reactive updates from MADSci services
const store = useLabStore()
store.updateWorkcellStatus(workcellId, newStatus)
```

### Component Patterns

**Panel Components**: Display and manage collections of lab objects
```vue
<!-- WorkcellPanel.vue example -->
<template>
  <v-card>
    <v-card-title>Workcells</v-card-title>
    <WorkcellTable :workcells="workcells" />
    <AddWorkcellButton @add="handleAddWorkcell" />
  </v-card>
</template>
```

**Modal Components**: Handle forms and detailed views
```vue
<!-- ResourceModal.vue example -->
<template>
  <v-dialog v-model="dialog">
    <v-card>
      <v-card-title>Resource Details</v-card-title>
      <ResourceForm :resource="resource" @submit="handleSubmit" />
    </v-card>
  </v-dialog>
</template>
```

**Admin Controls**: Provide operational control over lab components
```vue
<!-- AdminButtons/ components -->
<PauseResumeButton :target="workcell" />
<SafetyStopButton :target="node" />
<ResetButton :target="workflow" />
```

## API Integration

The dashboard communicates with MADSci services via REST APIs:

### Service Connections
```typescript
// Connecting to MADSci services
const labContext = await fetch('http://localhost:8000/context')
const workcells = await fetch(`${context.workcell_server_url}/workcells`)
const resources = await fetch(`${context.resource_server_url}/resources`)
```

### Real-time Updates
The dashboard polls services for live updates:
```typescript
// Periodic status updates
setInterval(() => {
  updateWorkcellStatus()
  updateNodeStatus()
  updateWorkflowProgress()
}, 2000)  // 2-second update interval
```

## Customization

### Adding New Panels
1. Create new Vue component in `src/components/`
2. Add tab to `Dashboard.vue`
3. Integrate with store for state management
4. Add API calls for data fetching

### Styling
The dashboard uses Vuetify's Material Design system:
```vue
<template>
  <!-- Use Vuetify components for consistent styling -->
  <v-card>
    <v-card-title>Custom Panel</v-card-title>
    <v-data-table :items="items" />
  </v-card>
</template>
```

### Environment Configuration
```typescript
// Configure API endpoints for different environments
const config = {
  development: {
    labServerUrl: 'http://localhost:8000'
  },
  production: {
    labServerUrl: window.location.origin
  }
}
```

## Building and Deployment

### Production Build
```bash
npm run build
# Outputs to ./dist/

# Serve via Lab Manager
python -m madsci.squid.lab_server --lab-dashboard-files-path ./ui/dist
```

### Docker Integration
The dashboard is automatically included in the `madsci_dashboard` Docker image:

```dockerfile
# Dashboard included in production image
FROM ghcr.io/ad-sdl/madsci_dashboard:latest
# UI files pre-built and available at startup
```

**Development**: See [example_lab/](../../example_lab/) for complete development setup with live dashboard integration.
