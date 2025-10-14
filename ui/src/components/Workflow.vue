<template>
  <h3>Steps</h3>
  <v-expansion-panels title="Steps">
    <v-expansion-panel v-for="(value, key) in steps" :key="key">
      <v-expansion-panel-title>
        <h4>{{ value.name }}</h4>
      </v-expansion-panel-title>
      <v-expansion-panel-text>
        <b>Description</b>: {{ value.comment }} <br>
        <b> Node</b>: {{ value.node }} <br>
        <b>Node Action</b>: {{ value.action }} <br>
        <b>Args</b>: <v-list>
          <v-list-item v-for="(arg_value, arg_key) in value.args" :key="arg_key">
            <b>{{ arg_key }}</b>: {{ arg_value }}
          </v-list-item>
        </v-list>
        <div v-if="!(value.start_time == '') && !(value.start_time == null)"><b>Start Time</b>: {{ value.start_time }}
        </div>
        <div v-if="!(value.end_time == '') && !(value.end_time == null)"><b>End Time</b>: {{ value.end_time }}</div>
        <div v-if="!(value.result == '') && !(value.result == null)"><b>Status</b>: {{
          value.result.status }} <br>
          <div v-if="Object.keys(value.result.datapoints || {}).length !== 0"> <b>Datapoints:</b><br>
            <v-data-table :headers="data_headers" :items="getDatapointDisplayItems(value.result.datapoints)" :loading="loadingDatapoints">
              <template v-slot:item="{ item }: { item: any }">
                <tr>
                  <td>{{ item.label || item.key }}</td>
                  <td>{{ item.data_type || 'Loading...' }}</td>
                  <td>{{ item.timestamp || '' }}</td>
                  <td v-if="item.data_type == 'file'">
                    <v-btn @click="trydownload(item.datapoint_id, item.label || item.key)" :disabled="!item.datapoint_id">
                      Download
                    </v-btn>
                  </td>
                  <td v-else-if="item.data_type == 'json'">
                    <v-btn @click="showDatapointValue(item.datapoint_id)" :disabled="!item.datapoint_id">
                      View Data
                    </v-btn>
                  </td>
                  <td v-else>
                    {{ item.datapoint_id }}
                  </td>
                </tr>
              </template>
            </v-data-table>
          </div>
          <div v-if="!(value.result.errors == null)"><b>Errors:</b> {{ value.result.errors }}</div>
        </div>
      </v-expansion-panel-text>
    </v-expansion-panel>
  </v-expansion-panels>
  <h3>Details</h3>
  <vue-json-pretty :data="wf" :deep="1"></vue-json-pretty>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import VueJsonPretty from 'vue-json-pretty';
import { VDataTable } from 'vuetify/components';
const props = defineProps(['steps', 'wf'])
import {urls} from "@/store"

const loadingDatapoints = ref(false)
const datapointMetadataCache = ref(new Map())

const data_headers = [
  { title: 'Label', key: 'label' },
  { title: 'Type', key: 'data_type' },
  { title: 'Timestamp', key: 'timestamp' },
  { title: 'Actions', key: 'actions' },
]

// Convert datapoints object (ID mappings) to display items with metadata
function getDatapointDisplayItems(datapoints: any) {
  if (!datapoints) return []

  const items: any[] = []

  for (const [key, value] of Object.entries(datapoints)) {
    if (typeof value === 'string') {
      // Value is a datapoint ID
      const metadata = datapointMetadataCache.value.get(value)
      items.push({
        key,
        datapoint_id: value,
        label: metadata?.label || key,
        data_type: metadata?.data_type || 'unknown',
        timestamp: metadata?.data_timestamp ? new Date(metadata.data_timestamp).toLocaleString() : '',
      })

      // Fetch metadata if not cached
      if (!metadata) {
        fetchDatapointMetadata(value)
      }
    } else if (Array.isArray(value)) {
      // Value is a list of datapoint IDs
      value.forEach((id, index) => {
        if (typeof id === 'string') {
          const metadata = datapointMetadataCache.value.get(id)
          items.push({
            key: `${key}[${index}]`,
            datapoint_id: id,
            label: metadata?.label || `${key}[${index}]`,
            data_type: metadata?.data_type || 'unknown',
            timestamp: metadata?.data_timestamp ? new Date(metadata.data_timestamp).toLocaleString() : '',
          })

          if (!metadata) {
            fetchDatapointMetadata(id)
          }
        }
      })
    }
  }

  return items
}

// Fetch metadata for a datapoint ID
async function fetchDatapointMetadata(datapointId: string) {
  try {
    loadingDatapoints.value = true
    const response = await fetch(`${urls.value["data_server_url"]}datapoint/${datapointId}`)
    if (response.ok) {
      const datapoint = await response.json()
      datapointMetadataCache.value.set(datapointId, {
        label: datapoint.label,
        data_type: datapoint.data_type,
        data_timestamp: datapoint.data_timestamp,
      })
    }
  } catch (error) {
    console.error(`Failed to fetch metadata for datapoint ${datapointId}:`, error)
  } finally {
    loadingDatapoints.value = false
  }
}

const forceFileDownload = (val: any, title: any) => {
  console.log(title)
  const url = window.URL.createObjectURL(new Blob([val]))
  const link = document.createElement('a')
  link.href = url
  link.setAttribute('download', title)
  document.body.appendChild(link)
  link.click()
}

async function trydownload(id: string, label: string) {
  try {
    const response = await fetch(`${urls.value["data_server_url"]}datapoint/${id}/value`)
    if (response.ok) {
      const val = await response.blob()
      forceFileDownload(val, label || id)
    } else {
      console.error('Failed to download datapoint:', response.statusText)
    }
  } catch (error) {
    console.error('Error downloading datapoint:', error)
  }
}

async function showDatapointValue(id: string) {
  try {
    const response = await fetch(`${urls.value["data_server_url"]}datapoint/${id}/value`)
    if (response.ok) {
      const value = await response.json()
      // For now, just log to console. Could show in a modal in the future.
      console.log('Datapoint value:', value)
      alert(`Datapoint value: ${JSON.stringify(value, null, 2)}`)
    } else {
      console.error('Failed to fetch datapoint value:', response.statusText)
    }
  } catch (error) {
    console.error('Error fetching datapoint value:', error)
  }
}
</script>
