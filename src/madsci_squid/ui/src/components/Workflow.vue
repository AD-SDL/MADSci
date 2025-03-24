<template>
  <h3>Steps</h3>
  <v-expansion-panels title="Steps">
    <v-expansion-panel v-for="(value, key) in steps" :key="key">
      <v-expansion-panel-title>
        <h4>{{ value.name }}</h4>
      </v-expansion-panel-title>
      <v-expansion-panel-text>
        <b>Description</b>: {{ value.comment }} <br>
        <b> Module</b>: {{ value.module }} <br>
        <b>Module Action</b>: {{ value.action }} <br>
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
            <v-data-table :headers="data_headers" :items="Object.values(test[value.id])">
              <template v-slot:item="{ item }: { item: any }">
                <tr>
                  <td>{{ item.label }}</td>
                  <td>{{ item.type }}</td>
                  <td v-if="item.type == 'local_file'"><v-btn @click="trydownload(item.id, item.label)">Download</v-btn>
                  </td>
                  <td v-if="item.type == 'data_value'">
                    <VueJsonPretty :data="item.value" />
                  </td>

                </tr>
              </template>
            </v-data-table>
          </div>
          <div v-if="!(value.result.error == null)"><b>Error:</b> {{ value.result.error }}</div>
        </div>
      </v-expansion-panel-text>
    </v-expansion-panel>
  </v-expansion-panels>
  <h3>Details</h3>
  <vue-json-pretty :data="wf" :deep="1"></vue-json-pretty>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import VueJsonPretty from 'vue-json-pretty';
import { VDataTable } from 'vuetify/components';
const props = defineProps(['steps', 'wf'])

const test = ref()
test.value = {}
const data_headers = [
  { title: 'Label', key: 'label' },
  { title: 'Type', key: 'type' },
  { title: 'Value', key: 'value' },


]
props.steps.forEach((step: any) => {
  test.value[step.id] = {}; if (step.result && step.result.data) {
    Object.keys(step.result.data).forEach(async (key: string) => {

      let val = await ((await fetch("http://".concat(window.location.host).concat("/data/").concat(step.result.data[key]).concat("/info"))).json())
      console.log(val)
      test.value[step.id][val.id] = val

    })

  }
});

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
  let val = await (await fetch("http://".concat(window.location.host).concat('/data/').concat(id))).blob()
  forceFileDownload(val, label)


}
</script>
