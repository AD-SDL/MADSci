# MADSci Dashboard Plugins

This directory contains Vue 3 plugins that extend the application's functionality and configure global libraries.

## Configured Plugins

### Vuetify (`vuetify.ts`)
Primary UI framework providing Material Design components:
- **Component Library**: Full Vuetify 3 component set with auto-import
- **Theme Configuration**: Material Design 3 theming system
- **Icons**: Material Design Icons (@mdi/font)
- **Typography**: Roboto font family integration
- **Responsive System**: Mobile-first responsive breakpoints

### Plugin Registration (`index.ts`)
Central plugin registration point that configures:
- Vuetify instance with theme and component settings
- Global application plugins and providers
- Third-party library integrations

## Usage

Plugins are automatically registered during Vue app initialization in `main.ts`:

```typescript
import { createApp } from 'vue'
import { registerPlugins } from '@/plugins'

const app = createApp(App)
registerPlugins(app)
```

## Configuration Details

### Vuetify Configuration
The Vuetify plugin is configured with:
- **Material Design 3**: Latest Material Design system
- **Auto-imports**: Components resolved automatically via Vite plugin
- **Icon Sets**: MDI icons with tree-shaking
- **Custom Theme**: Laboratory-appropriate color scheme
- **Responsive Breakpoints**: Optimized for lab monitoring displays

### Auto-Import System
Components from both Vuetify and PrimeVue are automatically imported:
```typescript
// vite.config.mts configuration
Components({
  resolvers: [PrimeVueResolver()],
}),
Vuetify(), // Auto-imports Vuetify components
```

This means components can be used without explicit imports:
```vue
<template>
  <!-- Vuetify components -->
  <v-card>
    <v-data-table :items="items" />
  </v-card>

  <!-- PrimeVue components -->
  <DataTable :value="data" />
</template>
```

## Adding New Plugins

To add new global plugins:

1. Install the plugin package: `yarn add plugin-name`
2. Create configuration file in `src/plugins/`
3. Register in `src/plugins/index.ts`
4. Add to Vite resolvers if needed (for auto-import)

Example plugin registration:
```typescript
// src/plugins/my-plugin.ts
export default {
  install(app: App) {
    app.config.globalProperties.$myPlugin = myPluginInstance
    app.provide('myPlugin', myPluginInstance)
  }
}

// src/plugins/index.ts
import myPlugin from './my-plugin'

export function registerPlugins(app: App) {
  app.use(vuetify)
  app.use(myPlugin)
}
```
