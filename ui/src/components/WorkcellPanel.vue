<template>
  <v-card class="pa-1" v-if="workcell_state">
    <v-card-title class="text-center">
      <h2>{{ workcell_info.name }}</h2>
      <div class="d-flex justify-center">
        <PauseResumeButton class="ml-2"/>
        <CancelButton class="ml-2" />
        <ResetButton class="ml-2" />
        <LockUnlockButton class="ml-2"/>
        <ShutdownButton class="ml-2" />
        <SafetyStopButton class="ml-2"/>
      </div>
    </v-card-title>
    <v-card-text>
      <v-container class="pa-1" fluid>
        <v-row dense wrap justify-content="space-evenly">
          <v-col cols="12" md="6" lg="6" xl="6">
            <NodesPanel :nodes="workcell_state.nodes" :main_url="main_url" :wc_state="workcell_state" :locations="workcell_info.locations"/>
            <LocationsPanel :locations="workcell_info.locations" />
          </v-col>
          <v-col cols="12" md="6" lg="6" xl="6">
            <WorkflowsPanel @view-workflows="$emit('view-workflows')" />
          </v-col>
        </v-row>
      </v-container>
    </v-card-text>
    <v-card-actions>
      <v-spacer />
      <v-dialog>
        <template #activator="{ props: activatorProps }">
          <v-btn color="blue" dark v-bind="activatorProps">
            Workcell Info
          </v-btn>
        </template>
        <template #default="{ isActive }">
          <v-card>
            <v-card-title>
              <h3>Workcell Info</h3>
            </v-card-title>
            <v-card-text>
              <vue-json-pretty :data="workcell_info" :deep="2" />
            </v-card-text>
            <v-card-actions>
              <v-spacer />
              <v-btn text="Close Dialog" @click="isActive.value = false" />
            </v-card-actions>
          </v-card>
        </template>
      </v-dialog>
    </v-card-actions>
  </v-card>
  <div class="d-flex justify-center" v-else>
    <v-progress-circular
      indeterminate
      color="primary"
      size="64"
    ></v-progress-circular>
  </div>
</template>

<script setup lang="ts">
import { main_url, workcell_info, workcell_state, active_workflows } from "@/store";
import VueJsonPretty from 'vue-json-pretty';
import 'vue-json-pretty/lib/styles.css';
import CancelButton from './AdminButtons/CancelButton.vue';
import LockUnlockButton from './AdminButtons/LockUnlockButton.vue';
import PauseResumeButton from './AdminButtons/PauseResumeButton.vue';
import ResetButton from './AdminButtons/ResetButton.vue';
import SafetyStopButton from './AdminButtons/SafetyStopButton.vue';
import ShutdownButton from './AdminButtons/ShutdownButton.vue';
import LocationsPanel from './LocationsPanel.vue';
import WorkflowsPanel from './WorkflowsPanel.vue';

defineEmits(['view-workflows']);
</script>
