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
          <v-data-table v-if="Object.keys(action.args).length > 0" :headers="arg_headers" :items="Object.values(action.args)" hover items-per-page="-1"
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
                      <v-checkbox :model-value="get_value(arg_values, action.name, item.name) ?? false" :true-value="true" :false-value="false" hide-details density="compact"
                        @update:modelValue="set_value(arg_values, action.name, item.name, $event)"/>
                    </template>
                    <template v-else-if="['int', 'float'].includes(item.argument_type)">
                      <v-text-field :model-value="get_value(arg_values, action.name, item.name)" type="number" density="compact" hide-details
                        @update:modelValue="set_value(arg_values, action.name, item.name, to_number($event))"/>
                    </template>
                    <template v-else>
                      <v-text-field height="20px" :model-value="get_value(arg_values, action.name, item.name)"
                        @update:modelValue="set_value(arg_values, action.name, item.name, $event); set_text(action)"/>
                    </template>
                  </td>
                </tr>
              </template>
              <template #bottom></template>
            </v-data-table>
          <h5 v-if="Object.keys(action.files).length > 0">Files</h5>
          <v-data-table v-if="Object.keys(action.files).length > 0" :headers="file_headers" :items="Object.values(action.files)" hover
              items-per-page="-1" no-data-text="No Files" density="compact">
              <template v-slot:item="{ item }: { item: any }">
                <tr>
                  <td>{{ item.name }}</td>
                  <td>{{ item.required }}</td>
                  <td>{{ item.description }}</td>
                  <td><v-file-input :model-value="get_value(file_values, action.name, item.name)" label="File input"
                    @update:modelValue="set_value(file_values, action.name, item.name, $event)"></v-file-input></td>
                </tr>
              </template>
            </v-data-table>
          <h5 v-if="Object.keys(action.locations).length > 0">Locations</h5>
          <v-data-table v-if="Object.keys(action.locations).length > 0" :headers="locations_headers" :items="Object.values(action.locations)" hover
              items-per-page="-1" no-data-text="No Locations" density="compact">
              <template v-slot:item="{ item }: { item: any }">
                <tr>
                  <td>{{ item.name }}</td>
                  <td>{{ item.required }}</td>
                  <td>{{ item.description }}</td>
                  <td>
                    <v-text-field :model-value="get_value(location_values, action.name, item.name)" list="locations" id="locations_id" name="locations_name"
                      @update:modelValue="set_value(location_values, action.name, item.name, $event); set_text(action)" />
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
import { ref, watch, type Ref } from 'vue';
import { urls } from '@/store';
import * as yaml from 'js-yaml';
import VueJsonPretty from 'vue-json-pretty';
import 'vue-json-pretty/lib/styles.css';

const props = defineProps(['modal_title', 'modal_text', 'locations'])
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

type ValueStore = Record<string, Record<string, any>>
const arg_values: Ref<ValueStore> = ref({})
const location_values: Ref<ValueStore> = ref({})
const file_values: Ref<ValueStore> = ref({})

function get_value(store: ValueStore, action_name: string, key: string) {
  return store[action_name]?.[key]
}

function set_value(store: ValueStore, action_name: string, key: string, value: any) {
  if (!store[action_name]) {
    store[action_name] = {}
  }
  store[action_name][key] = value
}

function to_number(value: any) {
  return value === '' || value === null || value === undefined ? undefined : Number(value)
}

function seed_defaults() {
  const actions = props.modal_text?.actions
  if (!actions) {
    return
  }
  Object.values(actions).forEach(function (action: any) {
    const args = arg_values.value[action.name] ?? (arg_values.value[action.name] = {})
    Object.values(action.args ?? {}).forEach(function (arg: any) {
      if (!(arg.name in args) && arg.default !== undefined && arg.default !== null) {
        args[arg.name] = arg.default
      }
    })
    if (!location_values.value[action.name]) {
      location_values.value[action.name] = {}
    }
    if (!file_values.value[action.name]) {
      file_values.value[action.name] = {}
    }
  })
}

watch(() => props.modal_text, seed_defaults, { immediate: true })

function collect_args(action: any) {
  var args: { [k: string]: any } = {};
  Object.values(action.args).forEach(function (arg: any) {
    const value = get_value(arg_values.value, action.name, arg.name)

    if (value === undefined) {
      args[arg.name] = arg.default
    } else if (typeof value === "boolean") {
      args[arg.name] = value
    } else {
      try {
        args[arg.name] = JSON.parse(value)
      } catch (e) {
        args[arg.name] = value
      }
    }
  })
  return args
}

function collect_locations(action: any) {
  var locations: { [k: string]: any } = {};
  Object.values(action.locations).forEach(function (location: any) {
    const value = get_value(location_values.value, action.name, location.name)

    if (value === undefined) {
      locations[location.name] = location.default
    }
    else {
      try {
        locations[location.name] = JSON.parse(value)
      } catch (e) {
        locations[location.name] = value
      }
    }
  })
  return locations
}

function set_text(action: any) {
  json_text.value = {
    "name": action.name,
    "node": props.modal_title,
    "action": action.name,
    "args": collect_args(action),
    "locations": collect_locations(action),
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
  var args = collect_args(action)
  var locations = collect_locations(action)
  var files: { [k: string]: any } = {};
  var file_inputs = Object.values(action.files)
  let file_input_params: any[] = []
  let file_input_values: any = {}
  file_inputs.forEach(function (file: any) {
    const value = get_value(file_values.value, action.name, file.name)
    if (value === undefined || value === null) {
      files[file.name] = ""
    }
    else {
      files[file.name] = value.name
      file_input_params = file_input_params.concat([{"key": value.name}])
      file_input_values[value.name] = value.name
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
    const value = get_value(file_values.value, action.name, file.name)
    if (value) {
      formData.append("files", value)
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
