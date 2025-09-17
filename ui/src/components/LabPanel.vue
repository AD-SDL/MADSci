<template>
  <v-container class="pa-4" fluid>
    <v-row>
      <!-- Lab Context Information -->
      <v-col cols="12" md="6">
        <v-card>
          <v-card-title class="text-center">
            <h3>Lab Context</h3>
          </v-card-title>
          <v-card-text>
            <v-list v-if="labContext">
              <v-list-item>
                <v-list-item-title>Lab Server URL</v-list-item-title>
                <v-list-item-subtitle>{{ labContext.lab_server_url || 'Not configured' }}</v-list-item-subtitle>
              </v-list-item>
              <v-list-item>
                <v-list-item-title>Event Server URL</v-list-item-title>
                <v-list-item-subtitle>{{ labContext.event_server_url || 'Not configured' }}</v-list-item-subtitle>
              </v-list-item>
              <v-list-item>
                <v-list-item-title>Experiment Server URL</v-list-item-title>
                <v-list-item-subtitle>{{ labContext.experiment_server_url || 'Not configured' }}</v-list-item-subtitle>
              </v-list-item>
              <v-list-item>
                <v-list-item-title>Data Server URL</v-list-item-title>
                <v-list-item-subtitle>{{ labContext.data_server_url || 'Not configured' }}</v-list-item-subtitle>
              </v-list-item>
              <v-list-item>
                <v-list-item-title>Resource Server URL</v-list-item-title>
                <v-list-item-subtitle>{{ labContext.resource_server_url || 'Not configured' }}</v-list-item-subtitle>
              </v-list-item>
              <v-list-item>
                <v-list-item-title>Workcell Server URL</v-list-item-title>
                <v-list-item-subtitle>{{ labContext.workcell_server_url || 'Not configured' }}</v-list-item-subtitle>
              </v-list-item>
              <v-list-item>
                <v-list-item-title>Location Server URL</v-list-item-title>
                <v-list-item-subtitle>{{ labContext.location_server_url || 'Not configured' }}</v-list-item-subtitle>
              </v-list-item>
            </v-list>
            <v-alert v-else type="warning" class="mt-4">
              Failed to load lab context
            </v-alert>
          </v-card-text>
        </v-card>
      </v-col>

      <!-- Lab Health Information -->
      <v-col cols="12" md="6">
        <v-card>
          <v-card-title class="text-center">
            <h3>Lab Health</h3>
          </v-card-title>
          <v-card-text>
            <div v-if="labHealth">
              <!-- Overall Health Status -->
              <v-row class="mb-4">
                <v-col cols="12">
                  <v-chip
                    :color="labHealth.healthy ? 'success' : 'error'"
                    variant="flat"
                    size="large"
                    class="mb-2"
                  >
                    <v-icon start>{{ labHealth.healthy ? 'mdi-check-circle' : 'mdi-alert-circle' }}</v-icon>
                    {{ labHealth.healthy ? 'Healthy' : 'Unhealthy' }}
                  </v-chip>
                  <p class="text-body-2">{{ labHealth.description }}</p>
                </v-col>
              </v-row>

              <!-- Manager Summary -->
              <v-row class="mb-4">
                <v-col cols="4">
                  <v-card variant="outlined">
                    <v-card-text class="text-center">
                      <div class="text-h4">{{ labHealth.total_managers }}</div>
                      <div class="text-caption">Total Managers</div>
                    </v-card-text>
                  </v-card>
                </v-col>
                <v-col cols="4">
                  <v-card variant="outlined">
                    <v-card-text class="text-center">
                      <div class="text-h4 text-success">{{ labHealth.healthy_managers }}</div>
                      <div class="text-caption">Healthy</div>
                    </v-card-text>
                  </v-card>
                </v-col>
                <v-col cols="4">
                  <v-card variant="outlined">
                    <v-card-text class="text-center">
                      <div class="text-h4 text-error">{{ labHealth.total_managers - labHealth.healthy_managers }}</div>
                      <div class="text-caption">Unhealthy</div>
                    </v-card-text>
                  </v-card>
                </v-col>
              </v-row>

              <!-- Individual Manager Status -->
              <v-list v-if="labHealth.managers && Object.keys(labHealth.managers).length > 0">
                <v-list-subheader>Manager Status</v-list-subheader>
                <v-list-item
                  v-for="(manager, name) in labHealth.managers"
                  :key="name"
                >
                  <template v-slot:prepend>
                    <v-icon
                      :color="manager.healthy ? 'success' : 'error'"
                    >
                      {{ manager.healthy ? 'mdi-check-circle' : 'mdi-alert-circle' }}
                    </v-icon>
                  </template>
                  <v-list-item-title>{{ formatManagerName(String(name)) }}</v-list-item-title>
                  <v-list-item-subtitle>{{ manager.description }}</v-list-item-subtitle>
                </v-list-item>
              </v-list>
              <v-alert v-else type="info" class="mt-4">
                No manager health information available
              </v-alert>
            </div>
            <v-alert v-else type="warning" class="mt-4">
              Failed to load lab health status
            </v-alert>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Refresh Button -->
    <v-row class="mt-4">
      <v-col cols="12" class="text-center">
        <v-btn
          @click="refreshLabInfo"
          :loading="isRefreshing"
          color="primary"
          variant="elevated"
        >
          <v-icon start>mdi-refresh</v-icon>
          Refresh Lab Information
        </v-btn>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { labContext, labHealth, refreshLabInfo, isRefreshing } from '@/store';

// Helper function to format manager names
function formatManagerName(name: string): string {
  return name
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

// Refresh lab information on component mount
onMounted(() => {
  refreshLabInfo();
});
</script>

<style scoped>
.v-card {
  height: 100%;
}

.v-chip {
  font-weight: bold;
}
</style>
