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
            <v-table v-if="labContext" density="compact">
              <thead>
                <tr>
                  <th class="text-left">Manager</th>
                  <th class="text-left">Server URL</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td><strong>Lab Server</strong></td>
                  <td>{{ labContext.lab_server_url || 'Not configured' }}</td>
                </tr>
                <tr>
                  <td><strong>Event Manager</strong></td>
                  <td>{{ labContext.event_server_url || 'Not configured' }}</td>
                </tr>
                <tr>
                  <td><strong>Experiment Manager</strong></td>
                  <td>{{ labContext.experiment_server_url || 'Not configured' }}</td>
                </tr>
                <tr>
                  <td><strong>Data Manager</strong></td>
                  <td>{{ labContext.data_server_url || 'Not configured' }}</td>
                </tr>
                <tr>
                  <td><strong>Resource Manager</strong></td>
                  <td>{{ labContext.resource_server_url || 'Not configured' }}</td>
                </tr>
                <tr>
                  <td><strong>Workcell Manager</strong></td>
                  <td>{{ labContext.workcell_server_url || 'Not configured' }}</td>
                </tr>
                <tr>
                  <td><strong>Location Manager</strong></td>
                  <td>{{ labContext.location_server_url || 'Not configured' }}</td>
                </tr>
              </tbody>
            </v-table>
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
              <v-expansion-panels v-if="labHealth.managers && Object.keys(labHealth.managers).length > 0" variant="accordion" class="mt-4">
                <v-expansion-panel
                  v-for="(manager, name) in labHealth.managers"
                  :key="name"
                >
                  <v-expansion-panel-title>
                    <div class="d-flex align-center w-100">
                      <v-icon
                        :color="manager.healthy ? 'success' : 'error'"
                        class="mr-3"
                      >
                        {{ manager.healthy ? 'mdi-check-circle' : 'mdi-alert-circle' }}
                      </v-icon>
                      <span class="font-weight-medium mr-4">{{ formatManagerName(String(name)) }}</span>
                      <v-spacer></v-spacer>
                      <v-chip
                        :color="manager.healthy ? 'success' : 'error'"
                        size="small"
                        variant="flat"
                        class="ml-4"
                      >
                        {{ manager.healthy ? 'Healthy' : 'Unhealthy' }}
                      </v-chip>
                    </div>
                  </v-expansion-panel-title>
                  <v-expansion-panel-text>
                    <v-card variant="outlined">
                      <v-card-text>
                        <div class="mb-3">
                          <strong>Status:</strong> {{ manager.description }}
                        </div>

                        <!-- Manager-specific details -->
                        <div v-if="getManagerSpecificDetails(manager)" class="mt-3">
                          <v-divider class="mb-3"></v-divider>
                          <div class="text-subtitle-2 mb-2">Manager Details:</div>
                          <v-table density="compact">
                            <tbody>
                              <tr
                                v-for="(value, key) in getManagerSpecificDetails(manager)"
                                :key="key"
                              >
                                <td class="text-left font-weight-medium" style="width: 40%;">
                                  {{ formatDetailKey(key) }}
                                </td>
                                <td class="text-left">
                                  <span v-if="typeof value === 'boolean'" class="d-flex align-center">
                                    <v-icon
                                      :color="value ? 'success' : 'error'"
                                      size="small"
                                      class="mr-1"
                                    >
                                      {{ value ? 'mdi-check' : 'mdi-close' }}
                                    </v-icon>
                                    {{ value ? 'Yes' : 'No' }}
                                  </span>
                                  <span v-else>{{ value }}</span>
                                </td>
                              </tr>
                            </tbody>
                          </v-table>
                        </div>
                      </v-card-text>
                    </v-card>
                  </v-expansion-panel-text>
                </v-expansion-panel>
              </v-expansion-panels>
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
import { onMounted } from 'vue';
import { labContext, labHealth, refreshLabInfo, isRefreshing } from '@/store';

// Helper function to format manager names
function formatManagerName(name: string): string {
  return name
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

// Helper function to format detail keys
function formatDetailKey(key: string): string {
  return key
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

// Helper function to extract manager-specific details
function getManagerSpecificDetails(manager: any): Record<string, any> | null {
  if (!manager || typeof manager !== 'object') return null;

  // Extract fields that are not common ManagerHealth fields
  const commonFields = ['healthy', 'description'];
  const specificDetails: Record<string, any> = {};

  for (const [key, value] of Object.entries(manager)) {
    if (!commonFields.includes(key) && value != null) {
      specificDetails[key] = value;
    }
  }

  return Object.keys(specificDetails).length > 0 ? specificDetails : null;
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
