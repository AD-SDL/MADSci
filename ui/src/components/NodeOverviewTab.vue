<template>
  <div>
    <div class="d-flex justify-end mb-3">
      <v-btn-toggle v-model="viewMode" mandatory density="compact" color="primary">
        <v-btn value="structured">Structured</v-btn>
        <v-btn value="json">JSON</v-btn>
      </v-btn-toggle>
    </div>

    <!-- Structured View -->
    <template v-if="viewMode === 'structured'">
      <h3 class="mb-2">Status</h3>
      <v-row dense>
        <v-col cols="12" sm="6" md="4" lg="3">
          <v-card variant="outlined" class="pa-3">
            <div class="text-subtitle-2 text-medium-emphasis">Ready</div>
            <v-chip :color="node_status?.ready ? 'success' : 'error'" size="small" label>
              {{ node_status?.ready ? 'Yes' : 'No' }}
            </v-chip>
          </v-card>
        </v-col>
        <v-col cols="12" sm="6" md="4" lg="3">
          <v-card variant="outlined" class="pa-3">
            <div class="text-subtitle-2 text-medium-emphasis">Busy</div>
            <v-chip :color="node_status?.busy ? 'warning' : 'default'" size="small" label>
              {{ node_status?.busy ? 'Yes' : 'No' }}
            </v-chip>
          </v-card>
        </v-col>
        <v-col cols="12" sm="6" md="4" lg="3">
          <v-card variant="outlined" class="pa-3">
            <div class="text-subtitle-2 text-medium-emphasis">Running Actions</div>
            <v-chip size="small" label>
              {{ node_status?.running_actions?.length ?? 0 }}
            </v-chip>
            <div v-if="node_status?.running_actions?.length > 0" class="mt-1">
              <v-chip v-for="action in node_status.running_actions" :key="action" size="x-small" class="mr-1 mt-1">
                {{ action }}
              </v-chip>
            </div>
          </v-card>
        </v-col>
        <v-col cols="12" sm="6" md="4" lg="3">
          <v-card variant="outlined" class="pa-3">
            <div class="text-subtitle-2 text-medium-emphasis">Paused</div>
            <v-chip :color="node_status?.paused ? 'warning' : 'default'" size="small" label>
              {{ node_status?.paused ? 'Yes' : 'No' }}
            </v-chip>
          </v-card>
        </v-col>
        <v-col cols="12" sm="6" md="4" lg="3">
          <v-card variant="outlined" class="pa-3">
            <div class="text-subtitle-2 text-medium-emphasis">Locked</div>
            <v-chip :color="node_status?.locked ? 'error' : 'default'" size="small" label>
              {{ node_status?.locked ? 'Yes' : 'No' }}
            </v-chip>
          </v-card>
        </v-col>
        <v-col cols="12" sm="6" md="4" lg="3">
          <v-card variant="outlined" class="pa-3">
            <div class="text-subtitle-2 text-medium-emphasis">Errored</div>
            <v-chip :color="node_status?.errored ? 'error' : 'default'" size="small" label>
              {{ node_status?.errored ? 'Yes' : 'No' }}
            </v-chip>
            <div v-if="node_status?.errored && node_status?.error_messages?.length > 0" class="mt-1">
              <div v-for="(msg, idx) in node_status.error_messages" :key="idx" class="text-error text-caption">
                {{ msg }}
              </div>
            </div>
          </v-card>
        </v-col>
        <v-col cols="12" sm="6" md="4" lg="3">
          <v-card variant="outlined" class="pa-3">
            <div class="text-subtitle-2 text-medium-emphasis">Initializing</div>
            <v-chip :color="node_status?.initializing ? 'info' : 'default'" size="small" label>
              {{ node_status?.initializing ? 'Yes' : 'No' }}
            </v-chip>
          </v-card>
        </v-col>
        <v-col cols="12" sm="6" md="4" lg="3">
          <v-card variant="outlined" class="pa-3">
            <div class="text-subtitle-2 text-medium-emphasis">Description</div>
            <span class="text-body-2">{{ node_status?.description || 'N/A' }}</span>
          </v-card>
        </v-col>
      </v-row>

      <h3 class="mt-4 mb-2">State</h3>
      <vue-json-pretty :data="node_state" :deep="2" :showLength="true"></vue-json-pretty>
    </template>

    <!-- JSON View -->
    <template v-if="viewMode === 'json'">
      <h3 class="mb-2">Status</h3>
      <vue-json-pretty :data="node_status" :deep="2" :showLength="true"></vue-json-pretty>

      <h3 class="mt-4 mb-2">State</h3>
      <vue-json-pretty :data="node_state" :deep="2" :showLength="true"></vue-json-pretty>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import VueJsonPretty from 'vue-json-pretty';
import 'vue-json-pretty/lib/styles.css';

defineProps(['node_status', 'node_state'])

const viewMode = ref<string>('structured')
</script>
