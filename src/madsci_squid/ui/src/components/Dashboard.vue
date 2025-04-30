<template>


  <v-tabs v-model="tab" align-tabs="center" color="deep-purple-accent-4">
    <v-tab :value="1">
      Workcells
    </v-tab>
    <v-tab :value="2">
      Workflows
    </v-tab>
    <v-tab :value="3">
      Resources
    </v-tab>
    <v-tab :value="4">
      Experiments
    </v-tab>

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
          <h3>Active</h3>
          <WorkflowTable :workflows="active_workflows"/>
          <h3>Archived</h3>
          <WorkflowTable :workflows="archived_workflows"/>
          </v-card-text>
        </v-card>
      </v-container>
    </v-window-item>
    <v-window-item :key="3" :value="3">
      <v-container class="pa-1 ma-1 justify-center" fluid>
      <v-card>
        <v-card-title class="text-center">
          <h2>Resources</h2>
        </v-card-title>
        <v-card-text>
          <ResourcesPanel />
          </v-card-text>
        </v-card>
      </v-container>
    </v-window-item>
    <v-window-item :key="4" :value="4">
      <v-container class="pa-1 ma-1 justify-center" fluid>
      <v-card>
        <v-card-text>
          <Experiments />
          </v-card-text>
        </v-card>
      </v-container>
    </v-window-item>
  </v-window>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import 'vue-json-pretty/lib/styles.css';
import Experiments from './Experiments.vue';
import { resources, active_workflows, archived_workflows } from "@/store";
import WorkcellPanel from './WorkcellPanel.vue';
import WorkflowTable from './WorkflowTable.vue';
import ResourcesPanel from './ResourcesPanel.vue';
const tab = ref(1)

</script>

<script lang="ts">

export default {
  data: () => ({ drawer: false }),
}
</script>

<style>
.node_indicator {
  color: white;
  border-radius: 5px;
    padding: 3px;
  }

.wf_status_completed,
.node_status_idle,
.node_status_ready {
  background-color: green;
  color: white;
}

.wf_status_running,
.node_status_running {
  background-color: blue;
  color: white;
}

.wf_status_failed,
.node_status_errored {
  background-color: red;
  color: white;
}

.wf_status_unknown,
.node_status_unknown {
  background-color: darkslategray;
  color: white;
}

.wf_status_new,
.node_status_initializing {
  background-color: aquamarine;
  color: black;
}

.wf_status_queued,
.wf_status_paused,
.node_status_paused {
  background-color: gold;
  color: black;
}

.wf_status_in_progress {
  background-color: darkblue;
  color: white;
}

.node_status_locked {
  background-color: darkslategray;
  color: white;
}

.wf_status_cancelled,
.node_status_cancelled {
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
