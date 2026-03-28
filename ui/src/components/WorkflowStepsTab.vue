<template>
  <div class="workflow-steps-tab pa-4">
    <v-expansion-panels>
      <v-expansion-panel
        v-for="(step, index) in steps"
        :key="step.step_id || index"
        :class="'step-border-' + getStepStatusKey(step)"
      >
        <v-expansion-panel-title>
          <div class="d-flex align-center w-100">
            <v-icon
              :icon="getStepIcon(step)"
              :color="getStepColor(step)"
              :class="{ 'spin-animation': getStepStatusKey(step) === 'running' }"
              class="mr-3"
              size="24"
            />
            <div class="flex-grow-1">
              <span class="font-weight-bold">{{ index + 1 }}. {{ step.name }}</span>
              <span class="text-grey-lighten-1 ml-2 text-body-2">
                {{ step.node }} &bull; {{ step.action }}
                <template v-if="step.duration"> &bull; {{ step.duration }}</template>
              </span>
            </div>
            <v-chip
              :color="getStepColor(step)"
              size="small"
              variant="flat"
              class="ml-2"
            >
              {{ getStepStatusLabel(step) }}
            </v-chip>
            <v-btn
              v-if="isTerminal"
              size="small"
              variant="text"
              color="primary"
              class="ml-2"
              @click.stop="retryFromStep(index)"
            >
              Retry from here
            </v-btn>
          </div>
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <div v-if="step.comment" class="mb-2">
            <b>Description</b>: {{ step.comment }}
          </div>
          <div class="mb-2">
            <b>Node</b>: {{ step.node }}
          </div>
          <div class="mb-2">
            <b>Action</b>: {{ step.action }}
          </div>
          <div v-if="step.args && Object.keys(step.args).length > 0" class="mb-2">
            <b>Args</b>:
            <v-list density="compact">
              <v-list-item v-for="(argValue, argKey) in step.args" :key="argKey">
                <b>{{ argKey }}</b>: {{ argValue }}
              </v-list-item>
            </v-list>
          </div>
          <div v-if="step.start_time" class="mb-1">
            <b>Start Time</b>: {{ step.start_time }}
          </div>
          <div v-if="step.end_time" class="mb-1">
            <b>End Time</b>: {{ step.end_time }}
          </div>
          <div v-if="step.result" class="mt-3">
            <b>Status</b>: {{ step.result.status }}
            <div v-if="step.result.datapoints && Object.keys(step.result.datapoints).length > 0" class="mt-2">
              <b>Datapoints:</b>
              <v-data-table
                :headers="data_headers"
                :items="getDatapointDisplayItems(step.result.datapoints)"
                :loading="loadingDatapoints"
                density="compact"
              >
                <template v-slot:item="{ item }: { item: any }">
                  <tr>
                    <td>{{ item.label || item.key }}</td>
                    <td>{{ item.data_type || 'Loading...' }}</td>
                    <td>{{ item.timestamp || '' }}</td>
                    <td v-if="item.data_type === 'file'">
                      <v-btn size="small" @click="trydownload(item.datapoint_id, item.label || item.key)" :disabled="!item.datapoint_id">
                        Download
                      </v-btn>
                    </td>
                    <td v-else-if="item.data_type === 'json'">
                      <v-btn size="small" @click="showDatapointValue(item.datapoint_id)" :disabled="!item.datapoint_id">
                        View Data
                      </v-btn>
                    </td>
                    <td v-else>
                      {{ item.datapoint_id }}
                    </td>
                  </tr>
                </template>
                <template #bottom></template>
              </v-data-table>
            </div>
            <div v-if="step.result.errors" class="mt-2">
              <b>Errors:</b> {{ step.result.errors }}
            </div>
          </div>
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { urls } from '@/store'
import { useDatapoints, data_headers } from '@/composables/useDatapoints'

const props = defineProps(['steps', 'wf'])
const emit = defineEmits(['retry-from-step'])

const { loadingDatapoints, getDatapointDisplayItems, trydownload, showDatapointValue } = useDatapoints()

const isTerminal = computed(() => {
  const status = props.wf?.status
  return status?.completed || status?.failed || status?.cancelled
})

function getStepStatusKey(step: any): string {
  const status = step.status || step.result?.status
  if (!status) return 'not_started'
  const s = String(status).toLowerCase()
  if (s === 'succeeded') return 'succeeded'
  if (s === 'failed') return 'failed'
  if (s === 'running') return 'running'
  if (s === 'paused') return 'paused'
  if (s === 'cancelled') return 'cancelled'
  if (s === 'not_ready') return 'not_started'
  return 'not_started'
}

function getStepIcon(step: any): string {
  const key = getStepStatusKey(step)
  switch (key) {
    case 'succeeded': return 'mdi-check-circle'
    case 'failed': return 'mdi-close-circle'
    case 'running': return 'mdi-loading'
    case 'paused': return 'mdi-pause-circle'
    case 'cancelled': return 'mdi-cancel'
    default: return 'mdi-circle-outline'
  }
}

function getStepColor(step: any): string {
  const key = getStepStatusKey(step)
  switch (key) {
    case 'succeeded': return 'green'
    case 'failed': return 'red'
    case 'running': return 'blue'
    case 'paused': return 'amber'
    case 'cancelled': return 'orange'
    default: return 'grey'
  }
}

function getStepStatusLabel(step: any): string {
  const key = getStepStatusKey(step)
  return key.toUpperCase().replace('_', ' ')
}

function retryFromStep(index: number) {
  emit('retry-from-step', index)
}
</script>

<style scoped>
.step-border-succeeded :deep(.v-expansion-panel-title) {
  border-left: 4px solid #4caf50;
}
.step-border-failed :deep(.v-expansion-panel-title) {
  border-left: 4px solid #f44336;
}
.step-border-running :deep(.v-expansion-panel-title) {
  border-left: 4px solid #2196f3;
}
.step-border-paused :deep(.v-expansion-panel-title) {
  border-left: 4px solid #ffc107;
}
.step-border-cancelled :deep(.v-expansion-panel-title) {
  border-left: 4px solid #ff9800;
}
.step-border-not_started :deep(.v-expansion-panel-title) {
  border-left: 4px solid #9e9e9e;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
.spin-animation {
  animation: spin 1s linear infinite;
}
</style>
