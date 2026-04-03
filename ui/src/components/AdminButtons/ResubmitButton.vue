<template>
  <div>
    <v-tooltip location="bottom">
      <template v-slot:activator="{ props: tooltipProps }">
        <div v-bind="tooltipProps">
          <v-btn
            @click="confirmDialog = true"
            color="blue-darken-2"
            dark
            elevation="5"
          >
            <v-icon>mdi-refresh</v-icon>
          </v-btn>
        </div>
      </template>
      <span>Resubmit Workflow</span>
    </v-tooltip>

    <v-dialog v-model="confirmDialog" max-width="400">
      <v-card>
        <v-card-title>Resubmit Workflow</v-card-title>
        <v-card-text>
          Create a new workflow from the same definition? This will start a fresh run.
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="confirmDialog = false">Cancel</v-btn>
          <v-btn color="primary" variant="flat" @click="resubmitWorkflow">Resubmit</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-snackbar v-model="snackbar" :color="snackbarColor" :timeout="3000">
      {{ snackbarText }}
    </v-snackbar>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useWorkflowActions } from '@/composables/useWorkflowActions'

const props = defineProps<{
  wf_id: string
}>()

const confirmDialog = ref(false)
const snackbar = ref(false)
const snackbarText = ref('')
const snackbarColor = ref('success')

const { resubmitWorkflow: resubmitWorkflowAction } = useWorkflowActions()

async function resubmitWorkflow() {
  const result = await resubmitWorkflowAction(props.wf_id)
  if (result.success) {
    confirmDialog.value = false
  }
  snackbarColor.value = result.success ? 'success' : 'error'
  snackbarText.value = result.message
  snackbar.value = true
}
</script>
