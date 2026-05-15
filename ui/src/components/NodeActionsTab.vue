<template>
  <div>
    <v-expansion-panels>
      <v-expansion-panel v-for="action in modal_text.actions" :key="action.name">
        <v-expansion-panel-title @click="set_text(action)">
          <h4>{{ action.name }}</h4>
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <h5>Description</h5>
          <p class="py-1 my-1">{{ action.description }}</p>
          <h5 v-if="Object.keys(action.args).length > 0">Arguments</h5>
          <v-data-table v-if="Object.keys(action.args).length > 0" :headers="arg_headers" :items="Object.keys(action.args).map(function(key){
    const arg = action.args[key];
    if (arg.value === undefined && arg.default !== undefined && arg.default !== null) {
      arg.value = arg.default;
    }
    return arg;})" hover items-per-page="-1"
              no-data-text="No Arguments" density="compact">
              <!-- eslint-disable vue/no-parsing-error-->
              <template v-slot:item="{ item }: { item: any }">
                <tr>
                  <td>{{ item.name }}</td>
                  <td>{{ item.argument_type }}</td>
                  <td>{{ item.required }}</td>
                  <td>{{ item.default }}</td>
                  <td>{{ item.description }}</td>
                  <td>
                    <template v-if="item.argument_type === 'bool'">
                      <v-checkbox v-model="item.value" :true-value="true" :false-value="false" hide-details density="compact"/>
                    </template>
                    <template v-else-if="['int', 'float'].includes(item.argument_type)">
                      <v-text-field v-model.number="item.value" type="number" density="compact" hide-details/>
                    </template>
                    <template v-else>
                      <v-text-field @update:modelValue="set_text(action)" height="20px" v-model="item.value"/>
                    </template>
                  </td>
                </tr>
              </template>
              <template #bottom></template>
            </v-data-table>
          <h5 v-if="Object.keys(action.files).length > 0">Files</h5>
          <v-data-table v-if="Object.keys(action.files).length > 0" :headers="file_headers" :items="Object.keys(action.files).map(function(key){
    return action.files[key];})" hover
              items-per-page="-1" no-data-text="No Files" density="compact">
              <template v-slot:item="{ item }: { item: any }">
                <tr>
                  <td>{{ item.name }}</td>
                  <td>{{ item.required }}</td>
                  <td>{{ item.description }}</td>
                  <td><v-file-input v-model="item.value" label="File input"></v-file-input></td>
                </tr>
              </template>
            </v-data-table>
          <h5 v-if="Object.keys(action.locations).length > 0">Locations</h5>
          <v-data-table v-if="Object.keys(action.locations).length > 0" :headers="locations_headers" :items="Object.keys(action.locations).map(function(key){
    return action.locations[key];})" hover
              items-per-page="-1" no-data-text="No Locations" density="compact">
              <template v-slot:item="{ item }: { item: any }">
                <tr>
                  <td>{{ item.name }}</td>
                  <td>{{ item.required }}</td>
                  <td>{{ item.description }}</td>
                  <td>
                    <v-text-field @update:modelValue="set_text(action)" v-model=item.value list="locations" id="locations_id" name="locations_name" />
                    <datalist id="locations">
                    <option v-for="option in locations.map(function(location: any){return location.location_name;})" :value="option">{{option}}</option>
                    </datalist>
                    </td>
                </tr>
              </template>
            </v-data-table>
          <h5 v-if="Object.keys(action.results).length > 0">Results</h5>
          <v-data-table v-if="Object.keys(action.results).length > 0" :headers="result_headers" :items="Object.values(action.results)" hover
              items-per-page="-1" no-data-text="No Results" density="compact">
              <template v-slot:item="{ item }: { item: any }">
                <tr>
                  <td>{{ item.result_label }}</td>
                  <td>{{ item.result_type }}</td>
                  <td>{{ item.data_type }}</td>
                </tr>
              </template>
            </v-data-table>
          <v-btn @click="send_wf(action)">Send Action</v-btn>
          <v-btn @click="copyVisible[action.name] = !copyVisible[action.name]; set_text(action)">
            <p v-if="!copyVisible[action.name]">Show Copyable Workflow Step</p>
            <p v-else>Hide copyable workflow step</p>
          </v-btn>
          <div v-if="copyVisible[action.name]">
            <vue-json-pretty :data="json_text" :deep="2" :showLength="true" />
            Copy YAML Step to Clipboard: <v-icon hover @click=copyAction(text)>
              mdi-clipboard-plus-outline
            </v-icon>
          </div>
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { urls } from '@/store';
import * as yaml from 'js-yaml';
import VueJsonPretty from 'vue-json-pretty';
import 'vue-json-pretty/lib/styles.css';

const props = defineProps(['modal_title', 'modal_text', 'wc_state', 'locations'])
const emit = defineEmits(['action-sent'])

const arg_headers = [
  { title: 'Name', key: 'name' },
  { title: 'Type', key: 'argument_type' },
  { title: 'Required', key: 'required' },
  { title: 'Default', key: 'default' },
  { title: 'Description', key: 'description' },
  { title: "Value", minWidth: "200px"}
]

const file_headers = [
  { title: 'Name', key: 'name' },
  { title: 'Required', key: 'required' },
  { title: 'Description', key: 'description' },
]

const locations_headers = [
  { title: 'Name', key: 'name' },
  { title: 'Required', key: 'required' },
  { title: 'Description', key: 'description' },
]

const result_headers = [
  { title: 'Default Label', key: 'name' },
  { title: 'Type', key: 'type' },
  { title: 'JSON Data Type', key: 'data_type' },
]

const text = ref()
const json_text = ref()
const copyVisible = ref<Record<string, boolean>>({})

function set_text(action: any) {
  var input_args = Object.keys(action.args).map(function(key){
    return action.args[key];});

  var args: { [k: string]: any } = {};

  input_args.forEach(function (arg: any) {

    if (arg.value === undefined) {
      args[arg.name] = arg.default
    } else if (typeof arg.value === "boolean") {
      args[arg.name] = arg.value
    } else {
      try {
        args[arg.name] = JSON.parse(arg.value)
      } catch (e) {
        args[arg.name] = arg.value
      }
    }
  }
  )
  var locations: { [k: string]: any } = {};
  var input_locations = Object.keys(action.locations).map(function(key){
    return action.locations[key];});
  input_locations.forEach(function (location: any) {

    if (location.value === undefined) {
      locations[location.name] = location.default
    }
    else {
      try {
        locations[location.name] = JSON.parse(location.value)
      } catch (e) {
        locations[location.name] = location.value
      }
    }

  })

  json_text.value = {
    "name": action.name,
    "node": props.modal_title,
    "action": action.name,
    "args": args,
    "locations": locations,
    "checks": null,
    "comment": "Test"
  }
  text.value = yaml.dump([json_text.value], { indent: 2, flowLevel: -1 })
}

async function send_wf(action: any) {
  var wf: any = {}
  wf.name = action.name
  wf.metadata = {
    "author": "dashboard",
    "info": "testing node",
    "version": "0"

  }
  wf.nodes = [props.modal_title]
  const formData = new FormData();
  var args: { [k: string]: any } = {};
  var input_args = Object.keys(action.args).map(function(key){
    return action.args[key];});
  input_args.forEach(function (arg: any) {

    if (arg.value === undefined) {
      args[arg.name] = arg.default
    }
    else {
      try {
        args[arg.name] = JSON.parse(arg.value)
      } catch (e) {
        args[arg.name] = arg.value
      }
    }

  })

  var locations: { [k: string]: any } = {};
  var input_locations = Object.keys(action.locations).map(function(key){
    return action.locations[key];});
  input_locations.forEach(function (location: any) {

    if (location.value === undefined) {
      locations[location.name] = location.default
    }
    else {
      try {
        locations[location.name] = JSON.parse(location.value)
      } catch (e) {
        locations[location.name] = location.value
      }
    }

  })
  var files: { [k: string]: any } = {};
  var file_inputs = Object.values(action.files)
  let i = 0;
  let file_input_params: any[] = []
  let file_input_values: any = {}
  file_inputs.forEach(function (file: any) {
    if (file.value === undefined) {
      files[file.name] = ""
    }
    else {
      i = i +  1
      files[file.name] = file.value.name
      file_input_params = file_input_params.concat([{"key": file.value.name}])
      file_input_values[file.value.name] = file.value.name
    }

  })
  wf.parameters = {
    "file_inputs": file_input_params
  }

  wf.steps = [{
    "name": action.name,
    "node": props.modal_title,
    "action": action.name,
    "args": args,
    "locations": locations,
    "checks": null,
    "comment": "Test",
    "files": files
  }]
  let workflow_definition_id = await ((await fetch(urls.value.workcell_server_url.concat('workflow_definition'),  {
    method: "POST",
    headers: {
      'Accept': 'application/json',
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(wf)
  })).json())
  formData.append("workflow_definition_id", workflow_definition_id)
  formData.append("file_input_paths", JSON.stringify(file_input_values))
  file_inputs.forEach(function (file: any) {
    if (file.value) {
      formData.append("files", file.value)
    }
  })

  fetch(urls.value.workcell_server_url.concat('workflow'), {
    method: "POST",

    body: formData
  });

  emit('action-sent')
}

function copyAction(test: any) {
  navigator.clipboard.writeText(test)
  alert("Copied!")
}
</script>
