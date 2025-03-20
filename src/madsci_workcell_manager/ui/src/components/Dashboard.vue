<template>
  <v-tabs v-model="tab" align-tabs="center" color="deep-purple-accent-4">
    <v-tab :value="1">
      Workcells
    </v-tab>
    <v-tab :value="2">
      Workflows
    </v-tab>
    <v-tab :value="3">
      Experiments
    </v-tab>
    <!-- <v-tab :value="4">Events</v-tab>
        <v-tab :value="5">Admin</v-tab>
        <v-tab :value="6">Resources</v-tab> -->
  </v-tabs>
  <v-window v-model="tab">
    <v-window-item :key="1" :value="1">
      <v-container class="pa-1 ma-1 justify-center" fluid>
        <WorkcellPanel @view-workflows="tab = 2" />
      </v-container>
    </v-window-item>
    <v-window-item :key="2" :value="2">
      <v-container class="pa-1 ma-1 justify-center" fluid>
      <v-card>
        <v-card-title class="text-center">
          <h2>Workflows</h2>
        </v-card-title>
        <v-card-text>
          <WorkflowTable/>
          </v-card-text>
        </v-card>
      </v-container>
    </v-window-item>
    <v-window-item :key="3" :value="3">
      <v-container class="pa-1 ma-1 justify-center" fluid>
        <Experiments/>
      </v-container>
    </v-window-item>
  </v-window>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import 'vue-json-pretty/lib/styles.css';
import Experiments from './Experiments.vue';
import WorkcellPanel from './WorkcellPanel.vue';
import WorkflowTable from './WorkflowTable.vue';

const tab = ref(1)
</script>

<script lang="ts">
export default {
  data: () => ({ drawer: false }),
}
</script>

<style>
.module_indicator {
  color: white;
  border-radius: 5px;
    padding: 3px;
  }

.wf_status_completed,
.module_status_IDLE,
.module_status_READY {
  background-color: green;
}

.wf_status_running,
.module_status_BUSY {
  background-color: blue;
}

.wf_status_failed,
.module_status_ERROR {
  background-color: red;
}

.wf_status_unknown,
.module_status_UNKNOWN {
  background-color: darkslategray;
}

.wf_status_new,
.module_status_INIT {
  background-color: aquamarine;
  color: black;
}

.wf_status_queued,
.wf_status_paused,
.wf_status_in_progress,
.module_status_PAUSED {
  background-color: gold;
  color: black;
}

.wf_status_in_progress {
  background-color: darkblue;
  color: black;
}

.module_status_LOCKED {
  background-color: darkslategray;
  color: white;
}

.wf_status_cancelled,
.module_status_CANCELLED {
  background-color: darkorange;
  color: black;
}

.wf_indicator {
  width: 10px;
  height: 10px;
  border-radius: 5px;
  margin-left: 10px;
}
</style>
