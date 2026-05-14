<template>
  <div class="workflow-details-tab pa-4">
    <v-row>
      <v-col cols="12" md="6">
        <h4 class="mb-2">Metadata</h4>
        <v-table density="compact">
          <tbody>
            <tr>
              <td class="font-weight-bold">Name</td>
              <td>{{ wf?.name }}</td>
            </tr>
            <tr v-if="wf?.label">
              <td class="font-weight-bold">Label</td>
              <td>{{ wf.label }}</td>
            </tr>
            <tr>
              <td class="font-weight-bold">Workflow ID</td>
              <td><code>{{ wf?.workflow_id }}</code></td>
            </tr>
            <tr v-if="wf?.workflow_definition_id">
              <td class="font-weight-bold">Definition ID</td>
              <td><code>{{ wf.workflow_definition_id }}</code></td>
            </tr>
          </tbody>
        </v-table>
      </v-col>
      <v-col cols="12" md="6">
        <h4 class="mb-2">Timing</h4>
        <v-table density="compact">
          <tbody>
            <tr v-if="wf?.submitted_time">
              <td class="font-weight-bold">Submitted</td>
              <td>{{ wf.submitted_time }}</td>
            </tr>
            <tr v-if="wf?.start_time">
              <td class="font-weight-bold">Start Time</td>
              <td>{{ wf.start_time }}</td>
            </tr>
            <tr v-if="wf?.end_time">
              <td class="font-weight-bold">End Time</td>
              <td>{{ wf.end_time }}</td>
            </tr>
            <tr v-if="wf?.duration">
              <td class="font-weight-bold">Duration</td>
              <td>{{ wf.duration }}</td>
            </tr>
          </tbody>
        </v-table>
      </v-col>
    </v-row>

    <div v-if="wf?.parameter_values && Object.keys(wf.parameter_values).length > 0" class="mt-4">
      <h4 class="mb-2">Parameters</h4>
      <v-table density="compact">
        <thead>
          <tr>
            <th>Key</th>
            <th>Value</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(value, key) in wf.parameter_values" :key="key">
            <td class="font-weight-bold">{{ key }}</td>
            <td>{{ typeof value === 'object' ? JSON.stringify(value) : value }}</td>
          </tr>
        </tbody>
      </v-table>
    </div>

    <div v-if="wf?.ownership_info" class="mt-4">
      <h4 class="mb-2">Ownership</h4>
      <vue-json-pretty :data="wf.ownership_info" :deep="2" />
    </div>

    <div class="mt-4">
      <h4 class="mb-2">Raw Workflow Data</h4>
      <vue-json-pretty :data="wf" :deep="1" />
    </div>
  </div>
</template>

<script setup lang="ts">
import VueJsonPretty from 'vue-json-pretty'
import 'vue-json-pretty/lib/styles.css'

defineProps(['wf'])
</script>
