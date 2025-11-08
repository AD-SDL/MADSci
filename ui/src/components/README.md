# MADSci Dashboard Components

Vue template files in this folder are automatically imported and provide the core UI functionality for laboratory monitoring and control.

## Auto-Import System

Components are automatically imported via [unplugin-vue-components](https://github.com/unplugin/unplugin-vue-components). No manual imports required.

## Component Categories

### Core Dashboard Components
- **Dashboard.vue**: Main tabbed interface with navigation
- **LabPanel.vue**: Overall laboratory status and health monitoring
- **Event.vue**: Event display and filtering

### Laboratory Management Panels
- **NodesPanel.vue**: Laboratory instrument monitoring and control
- **ResourcesPanel.vue**: Resource inventory browser with search/filter
- **LocationsPanel.vue**: Spatial laboratory layout and location management
- **WorkcellPanel.vue**: Workflow execution monitoring and control
- **WorkflowsPanel.vue**: Workflow design and template management
- **Experiments.vue**: Experiment campaign tracking and analysis

### Interactive Modals
- **NodeModal.vue**: Detailed node information with administrative controls
- **ResourceModal.vue**: Resource details, metadata, and operations
- **LocationModal.vue**: Location configuration and spatial properties
- **WorkflowModal.vue**: Workflow creation and editing interface
- **AddResourceModal.vue**: New resource creation wizard
- **AddLocationModal.vue**: New location setup wizard

### Administrative Controls (`AdminButtons/`)
Emergency and operational control components:
- **SafetyStopButton.vue**: Emergency stop for safety-critical situations
- **PauseResumeButton.vue**: Pause/resume operations (workcells, nodes)
- **LockUnlockButton.vue**: Lock/unlock nodes for maintenance
- **CancelButton.vue**: Cancel running workflows and operations
- **ResetButton.vue**: Reset node states and clear errors
- **ShutdownButton.vue**: Graceful system shutdown

### Resource Management (`ResourceComponents/`)
Specialized resource display components:
- **Resource.vue**: Base resource component with common properties
- **Consumable.vue**: Consumable-specific display (quantity tracking)
- **Slot.vue**: Storage slot visualization with occupancy status
- **Stack.vue**: Stack container with item management

### Workflow Components
- **CreateWorkflowPanel.vue**: Drag-and-drop workflow builder
- **Workflow.vue**: Running workflow status with progress indicators
- **WorkflowTable.vue**: Tabular workflow listing with filtering
- **Step.vue**: Individual workflow step with status and timing
- **TransferGraph.vue**: Visual representation of resource transfers

### Data Display Components
- **ResourceTable.vue**: Sortable, filterable resource inventory table

## Usage Patterns

### Panel Components
```vue
<template>
  <v-card>
    <v-card-title>{{ title }}</v-card-title>
    <v-card-text>
      <!-- Content with real-time data binding -->
      <DataTable :items="reactiveData" />
    </v-card-text>
    <v-card-actions>
      <AddButton @click="openModal" />
    </v-card-actions>
  </v-card>
</template>

<script lang="ts" setup>
import { ref } from 'vue'
import { workcell_state, resources } from '@/store'

// Direct reactive binding to global state
const reactiveData = ref(resources)
</script>
```

### Modal Components
```vue
<template>
  <v-dialog v-model="dialog" max-width="600px">
    <v-card>
      <v-card-title>Resource Details</v-card-title>
      <v-card-text>
        <v-form @submit="handleSubmit">
          <!-- Form fields with validation -->
        </v-form>
      </v-card-text>
      <v-card-actions>
        <v-btn @click="dialog = false">Cancel</v-btn>
        <v-btn @click="handleSubmit" color="primary">Save</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script lang="ts" setup>
import { ref } from 'vue'

const dialog = ref(false)
const emit = defineEmits(['submit', 'cancel'])

const handleSubmit = () => {
  // API call and emit result
  emit('submit', formData.value)
  dialog.value = false
}
</script>
```

### Admin Button Components
```vue
<template>
  <v-btn
    :color="buttonColor"
    :disabled="!canPerformAction"
    @click="performAction"
  >
    <v-icon>{{ icon }}</v-icon>
    {{ label }}
  </v-btn>
</template>

<script lang="ts" setup>
import { computed } from 'vue'

const props = defineProps<{
  target: Node | Workcell
  action: string
}>()

const canPerformAction = computed(() => {
  // Real-time validation based on target state
  return props.target.status === 'ready'
})

const performAction = async () => {
  // Direct API call to MADSci services
  await fetch(`${urls.value.node_server_url}/action`, {
    method: 'POST',
    body: JSON.stringify({ action: props.action })
  })
}
</script>
```

## State Integration

All components connect to global state via imports from `@/store`:

```typescript
import {
  workcell_state,
  active_workflows,
  resources,
  locations,
  labContext
} from '@/store'

// Reactive data binding - updates automatically
const currentStatus = computed(() => workcell_state.value?.status)
```

## Vuetify Integration

Components use Vuetify 3 Material Design components:
- `v-card`, `v-data-table`, `v-dialog` for layout
- `v-btn`, `v-text-field`, `v-select` for interactions
- `v-icon` from `@mdi/font` for iconography
- `v-alert`, `v-progress-circular` for feedback

## Error Handling

All components implement graceful error handling:
```vue
<template>
  <v-alert v-if="error" type="error">
    {{ error.message }}
  </v-alert>
  <v-progress-circular v-else-if="loading" />
  <MainContent v-else :data="data" />
</template>
```
