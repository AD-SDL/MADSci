<template>
  <v-dialog class="pa-3" v-slot:default="{ isActive }">
    <v-card>
      <v-card-title>
        <div class="d-flex align-center w-100">
          <h2 class="title py-3 my-3">Node: {{ modal_title }}</h2>

          <!-- Display pause/resume button only if node has 'pause' and 'resume' admin actions -->
          <template v-if="wc_state.nodes[modal_title].info.capabilities.admin_commands.includes('pause') && wc_state.nodes[modal_title].info.capabilities.admin_commands.includes('resume')">
            <PauseResumeButton
              :node="modal_title"
              :node_status="get_status(wc_state.nodes[modal_title].status)"
              class="ml-2" />
          </template>

          <CancelButton
            :node="modal_title"
            :node_status="get_status(wc_state.nodes[modal_title].status)"
            class="ml-2" />

          <ResetButton
            :node="modal_title"
            :node_status="wc_state.nodes[modal_title].state.status"
            class="ml-2" />

          <template v-if="wc_state.nodes[modal_title].info.capabilities.admin_commands.includes('home')">
            <HomeButton
              :node="modal_title"
              :node_status="wc_state.nodes[modal_title].state.status"
              class="ml-2"/>
          </template>

          <LockUnlockButton
            :node="modal_title"
            :node_status="wc_state.nodes[modal_title].state.status"
            class="ml-2" />

          <template v-if="wc_state.nodes[modal_title].info.capabilities.admin_commands.includes('shutdown')">
            <ShutdownButton
              :node="modal_title"
              :node_status="wc_state.nodes[modal_title].state.status"
              class="ml-2"/>
          </template>

          <template v-if="wc_state.nodes[modal_title].info.capabilities.admin_commands.includes('safety_stop')">
            <SafetyStopButton
              :node="modal_title"
              :node_status="wc_state.nodes[modal_title].state.status"
              class="ml-2"/>
          </template>
        </div>
        <v-sheet class="pa-2 rounded-lg text-md-center" :class="'node_status_' + get_status(wc_state.nodes[modal_title].status)">
          {{ get_status(wc_state.nodes[modal_title].status) }}
        </v-sheet>
      </v-card-title>

      <v-card-text class="subheading grey--text">
        <v-tabs v-model="tab" align-tabs="center" color="deep-purple-accent-4">
          <v-tab :value="1">Overview</v-tab>
          <v-tab :value="2">Info</v-tab>
          <v-tab :value="3">Actions</v-tab>
        </v-tabs>
        <v-window v-model="tab">
          <v-window-item :key="1" :value="1">
            <div class="pa-4">
              <NodeOverviewTab
                :node_status="wc_state.nodes[modal_title].status"
                :node_state="wc_state.nodes[modal_title].state"
              />
            </div>
          </v-window-item>
          <v-window-item :key="2" :value="2">
            <div class="pa-4">
              <NodeInfoTab :node_info="modal_text" />
            </div>
          </v-window-item>
          <v-window-item :key="3" :value="3">
            <div class="pa-4">
              <NodeActionsTab
                :modal_title="modal_title"
                :modal_text="modal_text"
                :wc_state="wc_state"
                :locations="locations"
                @action-sent="isActive.value = false"
              />
            </div>
          </v-window-item>
        </v-window>
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn flat @click="isActive.value = false" class="primary--text">close</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { get_status } from '../store';
import LockUnlockButton from './AdminButtons/LockUnlockButton.vue';
import ShutdownButton from './AdminButtons/ShutdownButton.vue';
import HomeButton from './AdminButtons/HomeButton.vue';

const props = defineProps(['modal_title', 'modal_text', 'main_url', 'wc_state', 'locations'])
const tab = ref(1)
const arg_headers = [
  { title: 'Name', key: 'name' },
  { title: 'Type', key: 'argument_type' },
  { title: 'Required', key: 'required' },
  { title: 'Default', key: 'default' },
  { title: 'Description', key: 'description' },
  { title: "Value", minWidth: "200px"}
]
const copy = ref(false)
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

const actions: any = computed(() =>
  Object.values(props.modal_text.actions).filter((a: any) =>
    props.wc_state.nodes[props.modal_title].info.capabilities.admin_commands.includes(a.name)
  )
)

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
  text.value = "- name : ".concat(action.name).concat("\n\t").concat(
    "node : ").concat(props.modal_title).concat("\n\t").concat(
      "action : ").concat(action.name).concat("\n\t").concat(
        "args : \n\t\t").concat(cleanArgs(input_args)).concat("locations : \n\t\t").concat(cleanArgs(input_locations)).concat("checks : null \n\tcomment: a comment! \n\t")
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

}
function cleanArgs(args: any) {
  var test: string = ""
  args.forEach((arg: any) => {
    var precursor = ""
    if (test !== "") {
      precursor = "\t"
    }

    if (arg.value) {
      test = test.concat((precursor.concat(arg.name.concat(" : ").concat(arg.value).concat("\n\t"))));
    } else {
      test = test.concat((precursor.concat(arg.name.concat(" : ").concat(arg.default).concat("\n\t"))));
    }
  }
  )
  return test
}
function copyAction(test: any) {
  navigator.clipboard.writeText(test)
  alert("Copied!")
}
</script>

<style scoped>
.title {
  margin-right: 30px;
}
</style>
