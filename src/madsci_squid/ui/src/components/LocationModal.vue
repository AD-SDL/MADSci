<template>
  <v-dialog class="pa-3" v-slot:default="{ isActive }">
    <v-card>
      <v-card-title>
        <h2 class="title">Location: {{ modal_title }}</h2>
        {{modal_text.location_id}}
        <v-sheet class="pa-2 rounded-lg text-md-center text-white" :class="'wf_status_' + modal_text.status">{{ modal_text.status }}</v-sheet>
      </v-card-title>
      <v-card-text>
        <div v-if="toggle==true">
       {{  modal_text }}
       <v-btn @click="toggle=!toggle; loc_text = JSON.stringify(modal_text)">Edit</v-btn>
      </div>
      <div v-else>
        <v-text-field class="pt-5 mr-2 w-25"   height="20px"
                        v-model="loc_text"  dense>

                     </v-text-field>
                     <v-btn @click="submit_location(loc_text); toggle=!toggle; modal_text.value = loc_text">Submit</v-btn>
      </div>

      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn flat @click="isActive.value = false; toggle=false" class="primary--text">close</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue';
const props = defineProps(['modal_title', 'modal_text'])
const flowdef = ref(false)
import { urls, workcell_state } from '../store';
const toggle = ref(true)
const loc_text = ref()
async function test_location(node: string): Promise<any>{
  var test = await ((await fetch(urls.value.workcell_manager.concat('admin/get_location/').concat(node)))).json()
  console.log(test)
}

async function submit_location(node: string): Promise<any>{
  var test = await ((await fetch(urls.value.workcell_manager.concat('admin/get_location/').concat(node)))).json()
  console.log(test)
}
</script>
