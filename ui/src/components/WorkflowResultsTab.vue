<template>
  <div class="workflow-results-tab pa-4">
    <v-data-table
      v-if="allResults.length > 0"
      :headers="resultHeaders"
      :items="allResults"
      :loading="loadingDatapoints"
      density="compact"
      items-per-page="-1"
    >
      <template v-slot:item="{ item }: { item: any }">
        <tr>
          <td>{{ item.stepName }}</td>
          <td>
            <v-chip :color="getStatusColor(item.stepStatus)" size="x-small" variant="flat">
              {{ item.stepStatus }}
            </v-chip>
          </td>
          <td>{{ item.label || item.key }}</td>
          <td>{{ item.data_type || 'Loading...' }}</td>
          <td>{{ item.timestamp || '' }}</td>
          <td>
            <v-btn v-if="item.data_type === 'file'" size="small" variant="text" @click="trydownload(item.datapoint_id, item.label || item.key)" :disabled="!item.datapoint_id">
              Download
            </v-btn>
            <v-btn v-else-if="item.data_type === 'json'" size="small" variant="text" @click="showDatapointValue(item.datapoint_id)" :disabled="!item.datapoint_id">
              View Data
            </v-btn>
            <span v-else class="text-grey">{{ item.datapoint_id }}</span>
          </td>
        </tr>
      </template>
      <template #bottom></template>
    </v-data-table>
    <div v-else class="text-center text-grey pa-8">
      No results available yet.
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useDatapoints } from '@/composables/useDatapoints'

const props = defineProps(['steps', 'wf'])

const { loadingDatapoints, getDatapointDisplayItems, trydownload, showDatapointValue } = useDatapoints()

const resultHeaders = [
  { title: 'Step', key: 'stepName' },
  { title: 'Status', key: 'stepStatus' },
  { title: 'Label', key: 'label' },
  { title: 'Type', key: 'data_type' },
  { title: 'Timestamp', key: 'timestamp' },
  { title: 'Actions', key: 'actions' },
]

const allResults = computed(() => {
  if (!props.steps) return []

  const items: any[] = []

  for (const step of props.steps) {
    if (!step.result?.datapoints) continue

    const datapointItems = getDatapointDisplayItems(step.result.datapoints)
    for (const dp of datapointItems) {
      items.push({
        ...dp,
        stepName: step.name,
        stepStatus: step.result?.status || step.status || 'unknown',
      })
    }
  }

  return items
})

function getStatusColor(status: string): string {
  const s = String(status).toLowerCase()
  if (s === 'succeeded') return 'green'
  if (s === 'failed') return 'red'
  if (s === 'running') return 'blue'
  if (s === 'paused') return 'amber'
  if (s === 'cancelled') return 'orange'
  return 'grey'
}
</script>
