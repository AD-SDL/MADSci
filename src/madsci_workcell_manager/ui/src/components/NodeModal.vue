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
              :node_status="wc_state.nodes[modal_title].state.status"
              class="ml-2" />
          </template>

          <CancelButton
            :node="modal_title"
            :node_status="wc_state.nodes[modal_title].state.status"
            class="ml-2" />

          <ResetButton
            :node="modal_title"
            :node_status="wc_state.nodes[modal_title].state.status"
            class="ml-2" />

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
        <v-sheet class="pa-2 rounded-lg text-md-center text-white" :class="'node_status_' + get_status(wc_state.nodes[modal_title].status)">
          {{ Object.entries(wc_state.nodes[modal_title].status).filter(([_, value]) => value === true).map(([key, _]) => key).join(' ') }}
        </v-sheet>
      </v-card-title>

      <v-card-text class="subheading grey--text">
        <div>
          <h3>Actions</h3>
          <v-expansion-panels>
            <v-expansion-panel v-for="action in modal_text.actions" :key="action.name">
              <v-expansion-panel-title @click="set_text(action)">
                <h4>{{ action.name }}</h4>
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <h5>Description</h5>
                <p class="py-1 my-1">{{ action.description }}</p>
                <h5>Arguments</h5>
                <v-data-table :headers="arg_headers" :items="Object.keys(action.args).map(function(key){
    return action.args[key];})" hover items-per-page="-1"
                  no-data-text="No Arguments" density="compact">
                  <!-- eslint-disable vue/no-parsing-error-->
                  <template v-slot:item="{ item }: { item: any }">
                    <tr>
                      <td>{{ item.name }}</td>
                      <td>{{ item.type }}</td>
                      <td>{{ item.required }}</td>
                      <td>{{ item.default }}</td>
                      <td>{{ item.description }}</td>
                      <td v-if="item.type == 'Location'"><v-select @update:menu="set_text(action)" v-model="item.value"
                          :items="Object.keys(wc_state.locations)"></v-select></td>
                      <td v-else><v-text-field @update:focused="set_text(action)" height="20px" v-model="item.value"
                          dense>
                        </v-text-field></td>
                    </tr>
                  </template>
                  <template #bottom></template>
                </v-data-table>
                <h5 v-if="action.files.length > 0">Files</h5>
                <v-data-table v-if="action.files.length > 0" :headers="file_headers" :items="action.files" hover
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
                <h5 v-if="action.results.length > 0">Results</h5>
                <v-data-table v-if="action.results.length > 0" :headers="result_headers" :items="action.results" hover
                  items-per-page="-1" no-data-text="No Results" density="compact">
                  <template v-slot:item="{ item }: { item: any }">
                    <tr>
                      <td>{{ item.label }}</td>
                      <td>{{ item.type }}</td>
                      <td>{{ item.description }}</td>
                    </tr>
                  </template>
                </v-data-table>
                <v-btn @click="send_wf(action); isActive.value = false">Send Action</v-btn>
                <v-btn @click="copy = !copy; set_text(action)">
                  <p v-if="(copy == false) ">Show Copyable Workflow Step</p>
                  <p v-else>Hide copyable workflow step</p>
                </v-btn>
                <div v-if="copy">
                  <vue-json-pretty :data="json_text" />
                  Copy YAML Step to Clipboard: <v-icon hover @click=copyAction(text)>
                    mdi-clipboard-plus-outline
                  </v-icon>
                </div>
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>
          <v-container fluid>
            <v-row dense wrap justify-content="space-evenly">
              <v-col cols="12" md="6" lg="4" xl="3">
                <h3>State</h3>
                <vue-json-pretty :data="wc_state.nodes[modal_title].state"></vue-json-pretty>
              </v-col>
              <v-col cols="12" md="6" lg="4" xl="3">
                <h3>Info</h3>
                <vue-json-pretty :data="modal_text" :deep="1"></vue-json-pretty>
              </v-col>
              <v-col cols="12" md="6" lg="4" xl="3">
                <h3>Resources</h3>
                  <p>Coming Soon</p>
              </v-col>
            </v-row>
          </v-container>
        </div>
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn flat @click="isActive.value = false" class="primary--text">close</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { get_status } from '../store';

import VueJsonPretty from 'vue-json-pretty';
import 'vue-json-pretty/lib/styles.css';
import LockUnlockButton from './AdminButtons/LockUnlockButton.vue';
import ShutdownButton from './AdminButtons/ShutdownButton.vue';
const props = defineProps(['modal_title', 'modal_text', 'main_url', 'wc_state'])
const arg_headers = [
  { title: 'Name', key: 'name' },
  { title: 'Type', key: 'type' },
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

const result_headers = [
  { title: 'Default Label', key: 'name' },
  { title: 'Type', key: 'type' },
  { title: 'Description', key: 'description' },
]
const text = ref()
const json_text = ref()

function set_text(action: any) {
  var input_args = Object.keys(action.args).map(function(key){
    return action.args[key];});
  text.value = "- name : ".concat(action.name).concat("\n\t").concat(
    "node : ").concat(props.modal_title).concat("\n\t").concat(
      "action : ").concat(action.name).concat("\n\t").concat(
        "args : \n\t\t").concat(cleanArgs(input_args)).concat("checks : null \n\tcomment: a comment! \n\t")
  var args: { [k: string]: any } = {};
  
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
  }
  )
  json_text.value = {
    "name": action.name,
    "node": props.modal_title,
    "action": action.name,
    "args": args,
    "checks": null,
    "comment": "Test"
  }
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
  var files: { [k: string]: any } = {};
  var input_files = Object.keys(action.files).map(function(key){
    return action.files[key];});
  input_files.forEach(function (file: any) {
    if (file.value === undefined) {
      files[file.name] = ""
    }
    else {

      files[file.name] = file.value.name
    }
  })
  wf.steps = [{
    "name": action.name,
    "node": props.modal_title,
    "action": action.name,
    "args": args,
    "checks": null,
    "comment": "Test",
    "files": files
  }]
  formData.append("workflow", JSON.stringify(wf))
  input_files.forEach(function (file: any) {
    if (file.value) {
      formData.append("files", file.value)
    }
  })
  fetch(props.main_url.concat('/workflows/start'), {
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

<style>
  .title {
    margin-right: 30px;
  }
</style>
