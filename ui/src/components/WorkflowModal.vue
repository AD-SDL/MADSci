<template>
  <v-dialog class="pa-3" v-slot:default="{ isActive }">
    <v-card>
      <v-card-title>
        <div class="d-flex align-center w-100">
          <h2 class="title py-3 my-3">Workflow: {{ modal_title }}</h2>
          <PauseResumeButton
            :wf_id="modal_text.workflow_id"
            :wf_status="modal_text.status"
            class="ml-2" />
          <CancelButton
            :wf_id="modal_text.workflow_id"
            :wf_status="modal_text.status"
            class="ml-2" />
          <RetryDialog
            :wf_id="modal_text.workflow_id"
            :wf_status="modal_text.status"
            :steps="modal_text.steps || []"
            class="ml-2" />
          <ResubmitButton
            :wf_id="modal_text.workflow_id"
            class="ml-2" />
        </div>
        <v-sheet class="pa-2 rounded-lg text-md-center text-white" :class="'wf_status_' + process_status(modal_text.status)">{{ process_status(modal_text.status) }}</v-sheet>
      </v-card-title>
      <v-card-text>
        <v-tabs v-model="tab" align-tabs="center" color="deep-purple-accent-4">
          <v-tab :value="1">Steps</v-tab>
          <v-tab :value="2">Results</v-tab>
          <v-tab :value="3">Details</v-tab>
        </v-tabs>
        <v-window v-model="tab">
          <v-window-item :key="1" :value="1">
            <WorkflowStepsTab :steps="modal_text.steps" :wf="modal_text" @retry-from-step="retryFromStep" />
          </v-window-item>
          <v-window-item :key="2" :value="2">
            <WorkflowResultsTab :steps="modal_text.steps" :wf="modal_text" />
          </v-window-item>
          <v-window-item :key="3" :value="3">
            <WorkflowDetailsTab :wf="modal_text" />
          </v-window-item>
        </v-window>
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn flat @click="isActive.value = false" class="primary--text">close</v-btn>
      </v-card-actions>
    </v-card>

    <v-snackbar v-model="snackbar" :color="snackbarColor" :timeout="3000">
      {{ snackbarText }}
    </v-snackbar>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { urls } from '@/store'

const props = defineProps(['modal_title', 'modal_text'])
const tab = ref(1)
const snackbar = ref(false)
const snackbarText = ref('')
const snackbarColor = ref('success')

function process_status(status: any) {
  if (status.completed) {
    return "completed"
  }
  else if (status.cancelled) {
    return "cancelled"
  }
  else if (status.failed) {
    return "failed"
  }
  else if (status.paused) {
    return "paused"
  }
  else if(status.running) {
    return "running"
  }
  else if(status.queued) {
    return "queued"
  }
}

async function retryFromStep(index: number) {
  try {
    const retryUrl = `${urls.value.workcell_server_url}workflow/${props.modal_text.workflow_id}/retry?index=${index}`
    const response = await fetch(retryUrl, { method: 'POST' })
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    snackbarColor.value = 'success'
    snackbarText.value = `Retry from step ${index + 1} started`
    snackbar.value = true
  } catch (error) {
    console.error('Error retrying workflow:', error)
    snackbarColor.value = 'error'
    snackbarText.value = 'Failed to retry workflow'
    snackbar.value = true
  }
}
</script>

<style scoped>
.title {
  margin-right: 30px;
}
</style>
