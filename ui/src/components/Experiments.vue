<template>
  <v-card>
    <v-card-title class="text-center">
      <h2>Experiments</h2>
    </v-card-title>
    <v-card-text>
      <v-data-table :headers="arg_headers" :items="experiments" item-value="_id" :sort-by="sortBy"
        density="compact">
        <template v-slot:item="{ item, internalItem, isExpanded, toggleExpand}: { item: any, internalItem: any, isExpanded: any, toggleExpand: any}">
        <tr >
          <td @click="openExperimentDetails(item)">{{ item.experiment_design.experiment_name }}</td>
          <td @click="openExperimentDetails(item)">{{ item._id }}</td>
          <td @click="openExperimentDetails(item)" :class="'status_button wf_status_' + item.status">{{ item.status }}</td>
          <td @click="openExperimentDetails(item)" >{{ item.started_at }}</td>
          <td><v-btn
        :icon="isExpanded(internalItem) ? 'mdi-chevron-up' : 'mdi-chevron-down'"
        variant="plain"
        @click="toggleExpand(internalItem)"
      /></td>
        </tr>
      </template>
      <template v-slot:expanded-row="{ columns, item}: {columns: any, item: any}">
          <tr>
            <td :colspan="columns.length"><WorkflowTable :workflows="filter_workflows(active_workflows, archived_workflows, item._id)" /></td>
          </tr>
        </template>
      </v-data-table>
      <v-dialog v-model="dialogVisible">
        <v-card v-if="selectedExperiment">
          <v-card-title>
            <span class="text-h5">Experiment Details</span>
          </v-card-title>
          <v-card-text>
            <p  :class="'status_button wf_status_' + selectedExperiment.status">{{ selectedExperiment.status }}</p>
            <v-list>
              <v-list-item>
                <v-list-item-title>Name:</v-list-item-title>
                <v-list-item-subtitle>{{ selectedExperiment.experiment_design.experiment_name }}</v-list-item-subtitle>
              </v-list-item>
              <v-list-item>
                <v-list-item-title>ID:</v-list-item-title>
                <v-list-item-subtitle>{{ selectedExperiment._id }}</v-list-item-subtitle>
              </v-list-item>
              <v-list-item>
                <v-list-item-title>Description:</v-list-item-title>
                <v-list-item-subtitle>{{ selectedExperiment.experiment_design.experiment_description || '-' }}</v-list-item-subtitle>
              </v-list-item>
              <v-list-item>
                <v-list-item-title>Start Time:</v-list-item-title>
                <v-list-item-subtitle>{{ selectedExperiment.started_at || '-' }}</v-list-item-subtitle>
              </v-list-item>
              <v-list-item>
                <v-list-item-title>End Time:</v-list-item-title>
                <v-list-item-subtitle>{{ selectedExperiment.ended_at || '-' }}</v-list-item-subtitle>
              </v-list-item>
            </v-list>
          </v-card-text>
          <v-card-actions>
            <v-spacer></v-spacer>
            <v-btn color="blue-darken-1" variant="text" @click="dialogVisible = false">Close</v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { ref } from 'vue';

/// <reference path="../store.d.ts" />
import { active_workflows, archived_workflows,  experiments } from "@/store";
import { VDataTable } from 'vuetify/components';

const sortBy: VDataTable['sortBy'] = [{ key: 'started_at', order: 'desc' }];

const arg_headers = [
  { title: 'Name', key: 'experiment_design.experiment_name' },
  { title: 'ID', key: '_id' },
  { title: 'Status', key: 'status' },
  { title: 'Started_at', key: 'started_at' }
];

const dialogVisible = ref(false);
const selectedExperiment = ref();

const openExperimentDetails = (item: any) => {
  selectedExperiment.value = item;
  dialogVisible.value = true;
};


function filter_workflows(active_workflows: any, archived_workflows: any, experiment_id: any)  {
  var active_workflow_list = Object.values(active_workflows).filter( (workflow: any) => workflow.ownership_info.experiment_id == experiment_id)
  var archived_workflow_list = Object.values(archived_workflows).filter( (workflow: any) => workflow.ownership_info.experiment_id == experiment_id)

  var dict: any = {}
  active_workflow_list.forEach((workflow: any) => dict[workflow.workflow_id] = workflow)
  archived_workflow_list.forEach((workflow: any) => dict[workflow.workflow_id] = workflow)
  return dict
}
</script>

<style>
.status_button {
  border-radius: 5px;
  text-align: center;
  color: white;
    padding: 2px;
  }
</style>
