<template>
  <v-card>
    <v-card-title class="text-center">
      <h2>Experiments</h2>
    </v-card-title>
    <v-card-text>
      <v-data-table :headers="arg_headers" :items="experiment_objects" item-value="experiment_id" :sort-by="sortBy"
        @click:row="openExperimentDetails" density="compact">
        <template v-slot:item.campaign_id="{ value }">
          <td>{{ (value != null && campaigns !== undefined && value in campaigns) ? campaigns[value].campaign_name : "-"
            }}</td>
        </template>
      </v-data-table>
      <v-dialog v-model="dialogVisible">
        <v-card v-if="selectedExperiment">
          <v-card-title>
            <span class="text-h5">Experiment Details</span>
          </v-card-title>
          <v-card-text>
            <v-list>
              <v-list-item>
                <v-list-item-title>Name:</v-list-item-title>
                <v-list-item-subtitle>{{ selectedExperiment.experiment_name }}</v-list-item-subtitle>
              </v-list-item>
              <v-list-item>
                <v-list-item-title>ID:</v-list-item-title>
                <v-list-item-subtitle>{{ selectedExperiment.experiment_id }}</v-list-item-subtitle>
              </v-list-item>
              <v-list-item>
                <v-list-item-title>Campaign:</v-list-item-title>
                <v-list-item-subtitle>
                  {{ selectedExperiment.campaign_id ? campaigns[selectedExperiment.campaign_id]?.campaign_name : '-' }}
                </v-list-item-subtitle>
              </v-list-item>
              <v-list-item>
                <v-list-item-title>Description:</v-list-item-title>
                <v-list-item-subtitle>{{ selectedExperiment.experiment_description || '-' }}</v-list-item-subtitle>
              </v-list-item>
              <v-list-item>
                <v-list-item-title>Last Check-in:</v-list-item-title>
                <v-list-item-subtitle>{{ selectedExperiment.check_in_timestamp || '-' }}</v-list-item-subtitle>
              </v-list-item>
              <v-list-item>
                <v-list-item-title>Email Addresses:</v-list-item-title>
                <v-list-item-subtitle>{{ selectedExperiment.email_addresses.join(', ') || '-' }}</v-list-item-subtitle>
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
import { VDataTable } from 'vuetify/lib/components/index.mjs';
/// <reference path="../store.d.ts" />
import { campaigns, experiment_objects } from "@/store";

const sortBy: VDataTable['sortBy'] = [{ key: 'experiment_id', order: 'desc' }];

const arg_headers = [
  { title: 'Name', key: 'experiment_name' },
  { title: 'ID', key: 'experiment_id' },
  { title: 'Campaign', key: 'campaign_id' },
  { title: 'Last Check-in', key: 'check_in_timestamp' }
];

const dialogVisible = ref(false);
const selectedExperiment = ref();

const openExperimentDetails = (event: Event, { item }: { item: any }) => {
  selectedExperiment.value = item;
  dialogVisible.value = true;
};
</script>
