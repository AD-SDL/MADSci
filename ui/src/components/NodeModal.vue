<template>
  <v-dialog class="pa-3" v-slot:default="{ isActive }">
    <v-card>
      <v-card-title>
        <div class="d-flex align-center w-100">
          <h2 class="title py-3 my-3">Node: {{ modal_title }}</h2>

          <!-- Display pause/resume button only if node has 'pause' and 'resume' admin actions -->
          <template v-if="wc_state.nodes[modal_title].info.capabilities.admin_commands.includes('pause') && wc_state.nodes[modal_title].info.capabilities.admin_commands.includes('resume')">
            <PauseResumeButton
              :node="modal_title"
              :node_status="get_status(wc_state.nodes[modal_title].status)"
              class="ml-2" />
          </template>

          <CancelButton
            :node="modal_title"
            :node_status="get_status(wc_state.nodes[modal_title].status)"
            class="ml-2" />

          <ResetButton
            :node="modal_title"
            :node_status="wc_state.nodes[modal_title].state.status"
            class="ml-2" />

          <LockUnlockButton
            :node="modal_title"
            :node_status="wc_state.nodes[modal_title].state.status"
            class="ml-2" />

          <template v-if="wc_state.nodes[modal_title].info.capabilities.admin_commands.includes('shutdown')">
            <ShutdownButton
              :node="modal_title"
              :node_status="wc_state.nodes[modal_title].state.status"
              class="ml-2"/>
          </template>

          <template v-if="wc_state.nodes[modal_title].info.capabilities.admin_commands.includes('safety_stop')">
            <SafetyStopButton
              :node="modal_title"
              :node_status="wc_state.nodes[modal_title].state.status"
              class="ml-2"/>
          </template>
        </div>
        <v-sheet class="pa-2 rounded-lg text-md-center" :class="'node_status_' + get_status(wc_state.nodes[modal_title].status)">
          {{ get_status(wc_state.nodes[modal_title].status) }}
        </v-sheet>
      </v-card-title>

      <v-card-text class="subheading grey--text">
        <v-tabs v-model="tab" align-tabs="center" color="deep-purple-accent-4">
          <v-tab :value="1">Overview</v-tab>
          <v-tab :value="2">Info</v-tab>
          <v-tab :value="3">Actions</v-tab>
        </v-tabs>
        <v-window v-model="tab">
          <v-window-item :key="1" :value="1">
            <div class="pa-4">
              <NodeOverviewTab
                :node_status="wc_state.nodes[modal_title].status"
                :node_state="wc_state.nodes[modal_title].state"
              />
            </div>
          </v-window-item>
          <v-window-item :key="2" :value="2">
            <div class="pa-4">
              <NodeInfoTab :node_info="modal_text" />
            </div>
          </v-window-item>
          <v-window-item :key="3" :value="3">
            <div class="pa-4">
              <NodeActionsTab
                :modal_title="modal_title"
                :modal_text="modal_text"
                :wc_state="wc_state"
                :locations="locations"
                @action-sent="isActive.value = false"
              />
            </div>
          </v-window-item>
        </v-window>
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
import { get_status } from '../store';
import LockUnlockButton from './AdminButtons/LockUnlockButton.vue';
import ShutdownButton from './AdminButtons/ShutdownButton.vue';

const props = defineProps(['modal_title', 'modal_text', 'main_url', 'wc_state', 'locations'])
const tab = ref(1)
</script>

<style scoped>
.title {
  margin-right: 30px;
}
</style>
