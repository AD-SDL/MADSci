<template>
  <v-dialog class="pa-3" v-slot:default="{ isActive }">
    <v-card>
      <v-card-title>
        <div class="d-flex align-center w-100">
          <h2 class="title py-3 my-3">Workflow: {{ modal_title }}</h2>
          <!-- {{modal_text.run_id}} -->
          <!-- <v-spacer></v-spacer> -->
          <CancelButton
            :wf_id="modal_text.workflow_id"
            :wf_status="modal_text.status"
            class="ml-2" />
        </div>
        <v-sheet class="pa-2 rounded-lg text-md-center text-white" :class="'wf_status_' + process_status(modal_text.status)">{{ process_status(modal_text.status) }}</v-sheet>
      </v-card-title>
      <v-card-text>
        <Workflow :steps="modal_text.steps" :wf="modal_text" />
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn flat @click="isActive.value = false" class="primary--text">close</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import CancelButton from './AdminButtons/CancelButton.vue';
const props = defineProps(['modal_title', 'modal_text'])
const flowdef = ref(false)

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
</script>
