<template>
    <WorkflowModal :modal_title="modal_title" :modal_text="modal_text" v-model="modal" />
    <!-- eslint-disable vue/no-parsing-error-->
    <v-data-table :headers="arg_headers" hover
      :items="Object.values(workflows)"
      no-data-text="No Workflows" density="compact" :sort-by="sortBy" :hide-default-footer="workflows.length <= 10">
      <template v-slot:item="{ item }: { item: any }">
        <tr @click="set_modal(workflows[item.workflow_id].name, workflows[item.workflow_id])">
          <td>{{ item.name }}</td>
          <td><v-sheet class="pa-2 rounded-lg text-md-center text-white" :class="'wf_status_' + process_status(item.status)"> {{
      process_status(item.status) }}
            </v-sheet>
          </td>
          <td>{{ item.start_time }}</td>
          <td>Step {{ item.status.current_step_index }}: {{ item.steps[item.status.current_step_index].name }}</td>
          <td>{{ item.end_time }}</td>
        </tr>
      </template>
    </v-data-table>
</template>

<script setup lang="ts">
const props = defineProps(['workflows'])
import { ref } from 'vue';
import { VDataTable } from 'vuetify/components';

const modal = ref(false)
const modal_text = ref()
const modal_title = ref()
const sortBy: VDataTable['sortBy'] = [{ key: 'submitted_time', order: 'desc' }];
const arg_headers = [
  { title: 'Name', key: 'name' },
  { title: 'Status', key: 'status' },
  { title: 'Submitted', key: 'submitted_time' },
  { title: 'Start Time', key: 'start_time' },
  { title: 'Latest Step', key: 'latest_step' },
  { title: 'End Time', key: 'end_time' }
]
const set_modal = (title: string, value: Object) => {
  modal_title.value = title
  modal_text.value = value
  modal.value = true
}

function process_status(status: any) {
  if (status.completed) {
    return "completed"
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

<style>
.status_button {
  border-radius: 5px;
  color: white;
    padding: 2px;
  }
</style>
