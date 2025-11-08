# MADSci Dashboard (squid_dashboard)

Vue 3 + Vuetify web dashboard for monitoring and controlling MADSci-powered laboratories.

> **Note**: This package is internally named `squid_dashboard` but serves as the primary MADSci Dashboard UI component.

## Features

- **Real-time Lab Monitoring**: Live status updates from all lab components
- **Workcell Management**: View, control, and submit workflows to workcells
- **Resource Tracking**: Browse inventory, manage containers, track consumables
- **Experiment Oversight**: Monitor campaigns, runs, and experimental progress
- **Node Control**: Send administrative commands to laboratory instruments
- **Responsive Design**: Works on desktop and mobile devices

## Development Setup

### Prerequisites
- **Node.js**: Version 16.0 or higher (LTS recommended)
- **Yarn**: Version 1.22+ for package management (do NOT use npm)
- **TypeScript**: Automatically installed with dependencies
- **System Requirements**: 2GB+ RAM, modern browser with ES2020 support
- **MADSci Services**: Lab Manager (SQUID) and manager services running for full functionality

### Quick Start

```bash
# Install dependencies
yarn install

# Start development server
yarn dev
# Dashboard available at http://localhost:3000

# Build for production
yarn build
# Output in ./dist/ directory
```

### Development Commands

```bash
yarn dev        # Start Vite dev server with hot reload
yarn build      # Build for production
yarn preview    # Preview production build locally
```

## Architecture

### Technology Stack
- **Vue 3**: Progressive JavaScript framework with Composition API
- **Vuetify 3**: Primary Material Design component library
- **PrimeVue**: Secondary component library (for specialized components)
- **TypeScript**: Type-safe JavaScript development
- **Vite**: Fast build tool and dev server
- **Vue Reactivity**: State management using Vue's built-in reactivity system (via `store.ts`)

> **UI Framework Note**: The dashboard primarily uses Vuetify for the main interface, with PrimeVue providing additional specialized components where needed. Both frameworks are configured in `vite.config.mts` with auto-import resolvers.

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
Global state is managed using Vue 3's Composition API and reactive references:

```typescript
// store.ts actual implementation
import { ref, watchEffect } from 'vue'

// Reactive state variables
const workcell_state = ref<WorkcellState>()
const active_workflows = ref<Record<string, Workflow>>({})
const resources = ref()
const locations = ref<Record<string, any>>({})
const labContext = ref<any>(null)

// Real-time updates with automatic refresh intervals
watchEffect(async () => {
  // Initialize API URLs from lab context
  const urls = await (await fetch(main_url.value + "/context")).json()
  setInterval(updateWorkcellState, 1000)
  setInterval(updateWorkflows, 1000)
  setInterval(updateResources, 1000)
})
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

### Service Discovery
```typescript
// Fetch lab context to discover all service URLs
const urls = await (await fetch(main_url.value + "/context")).json()
state_url.value = urls.workcell_server_url + "state"
resources_url.value = urls.resource_server_url
experiments_url.value = urls.experiment_server_url + "experiments"
locations_url.value = urls.location_server_url?.concat("locations") || ""
```

### Resource Management
```typescript
// Query resources with POST request
const resources = await fetch(resources_url.value + 'resource/query', {
  method: "POST",
  body: JSON.stringify({"multiple": true}),
  headers: { 'Content-Type': 'application/json' }
})
```

### Real-time Updates
The dashboard uses 1-second polling intervals for live updates:
```typescript
// Continuous polling for lab state changes
setInterval(updateWorkcellState, 1000)  // Workcell and node status
setInterval(updateWorkflows, 1000)      // Active and archived workflows
setInterval(updateResources, 1000)      // Resource inventory
setInterval(updateLocations, 1000)      // Location management
setInterval(updateExperiments, 1000)    // Experiment campaigns
```

### Error Handling
```typescript
// Graceful fallbacks for service unavailability
async function updateLocations() {
  if (locations_url.value) {
    try {
      locations.value = await (await fetch(locations_url.value)).json()
    } catch (error) {
      console.error("Failed to fetch locations from LocationManager:", error)
      // Fallback to workcell state locations
      locations.value = workcell_state.value?.locations || {}
    }
  }
}
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
The dashboard automatically adapts to different environments:

```typescript
// Automatic environment detection in store.ts
const main_url = ref<string>("")
main_url.value = "http://".concat(window.location.host)

// Development (localhost:3000)
// - Connects to local MADSci services
// - Hot reload enabled
// - Console debugging available

// Production (deployed)
// - Uses same origin for API calls
// - Optimized bundle size
// - Service worker caching (if configured)
```

#### Custom Environment Setup
For non-standard deployments, modify the base URL in `store.ts`:
```typescript
// Custom API endpoint
main_url.value = "http://your-lab-server:8000"
```

## Building and Deployment

### Production Build
```bash
yarn build
# Outputs to ./dist/

# Serve via Lab Manager
python -m madsci.squid.lab_server --lab-dashboard-files-path ./ui/dist
```

### Docker Integration
The dashboard is automatically included in the MADSci Docker images:

```dockerfile
# Dashboard included in production image
FROM ghcr.io/ad-sdl/madsci_dashboard:latest
# UI files pre-built and available at startup
```

## Troubleshooting

### Common Setup Issues

#### Node Version Conflicts
```bash
# Check your Node.js version
node --version  # Should be 16.0+

# Use nvm to switch versions if needed
nvm install 16
nvm use 16
```

#### Yarn vs NPM Issues
```bash
# If you accidentally used npm, remove node_modules
rm -rf node_modules package-lock.json

# Reinstall with yarn
yarn install
```

#### TypeScript Build Errors
```bash
# Run TypeScript check separately
npx vue-tsc --noEmit

# Common issue: Missing type definitions
yarn add @types/missing-package
```

#### Development Server Issues
```bash
# Clear Vite cache
rm -rf node_modules/.vite

# Restart with clean state
yarn dev
```

#### API Connection Problems
1. **Check Lab Manager Status**: Ensure SQUID is running on expected port
2. **CORS Issues**: Verify CORS configuration in backend services
3. **Network Timeouts**: Check firewall settings for local development

```typescript
// Debug API connections in browser console
fetch('http://localhost:8000/context')
  .then(res => res.json())
  .then(console.log)
  .catch(console.error)
```

### Performance Issues

#### Slow Update Intervals
The dashboard updates every 1 second. To reduce load:
```typescript
// In store.ts, modify intervals
setInterval(updateWorkcellState, 2000)  // Increase to 2 seconds
```

#### Memory Leaks
Long-running sessions may accumulate data. Refresh browser periodically during development.

### Browser Compatibility

**Supported Browsers**:
- Chrome 90+, Firefox 88+, Safari 14+, Edge 90+

**Unsupported**:
- Internet Explorer (all versions)
- Chrome < 90 (missing ES2020 features)

### Development Tips

1. **Use Browser DevTools**: Vue DevTools extension recommended
2. **Hot Reload**: Changes auto-refresh, but state resets on error
3. **Console Debugging**: Store state available as `window.store` in development
4. **Network Tab**: Monitor API calls for debugging connection issues

**Development**: See [example_lab/](../../example_lab/) for complete development setup with live dashboard integration.
