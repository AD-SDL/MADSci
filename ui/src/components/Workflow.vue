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
          <div v-if="!(value.result.data == null)"> <b>Data:</b><br>
            <v-data-table :headers="data_headers" :items="Object.values(test[value.step_id])">
              <template v-slot:item="{ item }: { item: any }">
                <tr>
                  <td>{{ item.label }}</td>
                  <td>{{ item.data_type }}</td>
                  <td v-if="item.data_type == 'file'"><v-btn @click="trydownload(item._id, item.label)">Download</v-btn>
                  </td>
                  <td v-if="item.data_type == 'json'">
                    <VueJsonPretty :data="item.value" />
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

const test = ref()
test.value = {}
const data_headers = [
  { title: 'Label', key: 'label' },
  { title: 'Type', key: 'type' },
  { title: 'Value', key: 'value' },


]
watch (() => props.steps, async(newSteps) => {
  const tmp: Record<string, Record<string, any>> = {}
  for (const step of newSteps) {
    tmp[step.step_id] = {}
    if (step.result?.data) {
      for (const [label, datapointId] of Object.entries(step.result.data)) {
        try { const resp = await fetch(urls.value["data_server_url"] + "datapoint/" + datapointId)
          const val = await resp.json()
          const key = val.datapoint_id ?? val._id
          if (!key) { console.warn("No valid ID found", val)
            continue
          }
          tmp[step.step_id][key] = val;
        } catch (err) { console.error("Failed to fetch datapoint", datapointId, err)}
    }}}
  test.value = tmp;
  console.log(test.value)
  },
  { immediate: true, deep: false}
)

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
  let val = await (await fetch(urls.value["data_server_url"].concat('datapoint/').concat(id).concat('/value'))).blob()
  forceFileDownload(val, label)
}
</script>
