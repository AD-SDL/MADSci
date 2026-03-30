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
      <h3 class="mb-2">Node Details</h3>
      <v-list density="compact" lines="one">
        <v-list-item>
          <template #prepend>
            <span class="text-subtitle-2 text-medium-emphasis mr-2" style="min-width: 140px;">Node Name</span>
          </template>
          <v-list-item-title>{{ node_info?.node_name || 'N/A' }}</v-list-item-title>
        </v-list-item>
        <v-list-item>
          <template #prepend>
            <span class="text-subtitle-2 text-medium-emphasis mr-2" style="min-width: 140px;">Node ID</span>
          </template>
          <v-list-item-title>{{ node_info?.node_id || 'N/A' }}</v-list-item-title>
        </v-list-item>
        <v-list-item>
          <template #prepend>
            <span class="text-subtitle-2 text-medium-emphasis mr-2" style="min-width: 140px;">Description</span>
          </template>
          <v-list-item-title>{{ node_info?.node_description || node_info?.description || 'N/A' }}</v-list-item-title>
        </v-list-item>
        <v-list-item>
          <template #prepend>
            <span class="text-subtitle-2 text-medium-emphasis mr-2" style="min-width: 140px;">Module Name</span>
          </template>
          <v-list-item-title>{{ node_info?.module_name || 'N/A' }}</v-list-item-title>
        </v-list-item>
        <v-list-item>
          <template #prepend>
            <span class="text-subtitle-2 text-medium-emphasis mr-2" style="min-width: 140px;">Module Version</span>
          </template>
          <v-list-item-title>{{ node_info?.module_version || 'N/A' }}</v-list-item-title>
        </v-list-item>
        <v-list-item>
          <template #prepend>
            <span class="text-subtitle-2 text-medium-emphasis mr-2" style="min-width: 140px;">Node URL</span>
          </template>
          <v-list-item-title>{{ node_info?.node_url || 'N/A' }}</v-list-item-title>
        </v-list-item>
      </v-list>

      <template v-if="node_info?.capabilities">
        <h3 class="mt-4 mb-2">Capabilities</h3>
        <vue-json-pretty :data="node_info.capabilities" :deep="1" :showLength="true"></vue-json-pretty>
      </template>

      <template v-if="node_info?.config">
        <h3 class="mt-4 mb-2">Config</h3>
        <vue-json-pretty :data="node_info.config" :deep="1" :showLength="true"></vue-json-pretty>
      </template>
    </template>

    <!-- JSON View -->
    <template v-if="viewMode === 'json'">
      <vue-json-pretty :data="node_info" :deep="2" :showLength="true"></vue-json-pretty>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import VueJsonPretty from 'vue-json-pretty';
import 'vue-json-pretty/lib/styles.css';

defineProps(['node_info'])

const viewMode = ref<string>('structured')
</script>
