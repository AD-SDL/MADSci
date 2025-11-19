# MADSci Dashboard UI - Agent Guidelines

## Overview
The MADSci Dashboard UI (package name: `squid_dashboard`) is a Vue 3 + Vuetify web application that provides a comprehensive interface for monitoring and controlling laboratory operations. It serves as the primary user interface for interacting with all MADSci manager services and laboratory instruments.

## Development Guidelines for Coding Agents

### Technology Stack Understanding
- **Vue 3**: Uses Composition API exclusively (NOT Options API)
- **Vuetify 3**: Primary UI framework for Material Design components
- **PrimeVue**: Secondary component library for specialized components
- **TypeScript**: Strict type checking enabled
- **Vite**: Build tool with HMR for development
- **Yarn**: Package manager (use `yarn`, not `npm`)

### State Management Pattern
The application uses Vue 3's built-in reactivity system, **NOT Pinia or Vuex**:

```typescript
// Correct pattern from store.ts
import { ref, watchEffect } from 'vue'

const workcell_state = ref<WorkcellState>()
const active_workflows = ref<Record<string, Workflow>>({})

// Auto-refresh with watchers
watchEffect(async () => {
  setInterval(updateWorkcellState, 1000)
})
```

### API Integration Patterns
1. **Service Discovery**: Always fetch context first to get service URLs
2. **Error Handling**: Implement graceful fallbacks for unavailable services
3. **Polling**: Use 1-second intervals for real-time updates
4. **POST Requests**: Use JSON payloads for complex queries

```typescript
// Example from actual implementation
const resources = await fetch(resources_url.value + 'resource/query', {
  method: "POST",
  body: JSON.stringify({"multiple": true}),
  headers: { 'Content-Type': 'application/json' }
})
```

### Component Architecture
- **Panel Components**: Display collections (e.g., `WorkcellPanel.vue`)
- **Modal Components**: Handle forms and detailed views (e.g., `ResourceModal.vue`)
- **Admin Controls**: Operational buttons (`AdminButtons/` directory)
- **Resource Components**: Specialized displays (`ResourceComponents/` directory)

### File Structure Rules
- Main components in `src/components/`
- Type definitions in `src/types/` (separate files per domain)
- Global state in `src/store.ts`
- Auto-imported components (no manual imports needed)

### Development Commands
```bash
yarn dev          # Start development server on port 3000
yarn build        # Build for production (includes TypeScript check)
yarn preview      # Preview production build
```

### Important Configuration Notes
- **Port**: Development server runs on port 3000 (configured in `vite.config.mts`)
- **Auto-imports**: Components are auto-imported via `unplugin-vue-components`
- **Resolvers**: Both Vuetify and PrimeVue components resolve automatically
- **TypeScript**: Strict mode enabled, must pass `vue-tsc --noEmit` check

### Integration Points
- **Main Backend**: Connects to MADSci SQUID (Lab Manager) for context
- **Manager Services**: Direct REST API calls to all 6 manager services
- **Real-time Updates**: 1-second polling intervals (no WebSocket currently)
- **Resource Management**: POST-based queries for complex resource filtering

### Common Pitfalls to Avoid
1. **Do NOT** use Pinia - state management is pure Vue Composition API
2. **Do NOT** manually import components - auto-import is configured
3. **Do NOT** use npm - project uses yarn exclusively
4. **Do NOT** assume WebSocket - current implementation uses HTTP polling
5. **Do NOT** hardcode service URLs - always use context discovery

### Testing and Quality
- Run `yarn build` to verify TypeScript compliance
- All components should be responsive (mobile-friendly)
- Error handling should include console logging and graceful fallbacks
- Use Vuetify components for consistency unless PrimeVue provides better functionality

### Adding New Features
1. Create component in appropriate subdirectory
2. Add to Dashboard.vue if it's a new tab/panel
3. Update store.ts for new state requirements
4. Add type definitions in `src/types/`
5. Ensure proper error handling and loading states
