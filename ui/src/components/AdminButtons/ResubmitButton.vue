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
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { urls } from '@/store'

const props = defineProps<{
  wf_id: string
}>()

const confirmDialog = ref(false)

async function resubmitWorkflow() {
  try {
    const resubmitUrl = `${urls.value.workcell_server_url}workflow/${props.wf_id}/resubmit`
    const response = await fetch(resubmitUrl, { method: 'POST' })
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    console.log('Resubmit successful')
    confirmDialog.value = false
  } catch (error) {
    console.error('Error resubmitting workflow:', error)
  }
}
</script>
