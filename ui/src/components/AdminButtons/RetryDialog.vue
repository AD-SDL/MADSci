<template>
  <div>
    <v-tooltip location="bottom">
      <template v-slot:activator="{ props: tooltipProps }">
        <div v-bind="tooltipProps">
          <v-btn
            @click="dialog = true"
            color="light-green-darken-2"
            dark
            elevation="5"
            :disabled="!canRetry"
          >
            <v-icon>mdi-restart</v-icon>
          </v-btn>
        </div>
      </template>
      <span>{{ canRetry ? 'Retry Workflow' : 'Retry Workflow (unavailable)' }}</span>
    </v-tooltip>

    <v-dialog v-model="dialog" max-width="500">
      <v-card>
        <v-card-title>Retry Workflow</v-card-title>
        <v-card-text>
          <p class="mb-4">Retry this workflow from a specific step:</p>
          <v-select
            v-model="selectedStepIndex"
            :items="stepOptions"
            item-title="title"
            item-value="value"
            label="Retry from step"
            density="compact"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="dialog = false">Cancel</v-btn>
          <v-btn color="primary" variant="flat" @click="retryWorkflow">Retry</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-snackbar v-model="snackbar" :color="snackbarColor" :timeout="3000">
      {{ snackbarText }}
    </v-snackbar>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watchEffect } from 'vue'
import { urls } from '@/store'
import type { WorkflowStatus } from '@/types/workflow_types'

const props = defineProps<{
  wf_id: string
  wf_status: WorkflowStatus
  steps: any[]
}>()

const dialog = ref(false)
const selectedStepIndex = ref(0)
const snackbar = ref(false)
const snackbarText = ref('')
const snackbarColor = ref('success')

const canRetry = computed(() => {
  return props.wf_status?.terminal === true
})

const stepOptions = computed(() => {
  if (!props.steps) return []
  return props.steps.map((step: any, index: number) => ({
    title: `Step ${index + 1}: ${step.name}${step.status ? ' (' + step.status + ')' : ''}`,
    value: index,
  }))
})

watchEffect(() => {
  if (props.wf_status?.failed) {
    selectedStepIndex.value = props.wf_status?.current_step_index ?? 0
  } else {
    selectedStepIndex.value = 0
  }
})

async function retryWorkflow() {
  try {
    const retryUrl = `${urls.value.workcell_server_url}workflow/${props.wf_id}/retry?index=${selectedStepIndex.value}`
    const response = await fetch(retryUrl, { method: 'POST' })
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    dialog.value = false
    snackbarColor.value = 'success'
    snackbarText.value = `Retry from step ${selectedStepIndex.value + 1} started`
    snackbar.value = true
  } catch (error) {
    console.error('Error retrying workflow:', error)
    snackbarColor.value = 'error'
    snackbarText.value = 'Failed to retry workflow'
    snackbar.value = true
  }
}

defineExpose({ openDialog: () => { dialog.value = true } })
</script>
