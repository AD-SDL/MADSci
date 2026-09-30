<template>
  <v-dialog class="pa-3" v-slot:default="{ isActive}">
    <v-card>
     <v-card-title>
        <h2 class="title">Delete These Resources?</h2>
      </v-card-title>
   <ResourceTable :resources="get_resources()" :parent_id="null" :hide_header="true" :show_checkboxes="false" :show_children="true"/>
   <v-btn @click="delete_resources(); isActive.value=false">Confirm</v-btn>
   <v-btn @click="isActive.value=false">Cancel</v-btn>
    </v-card>
  </v-dialog>

</template>

<script setup lang="ts">
import { ref, Ref} from 'vue';
import { urls } from "@/store";
import vSelect from 'vue-select'
import {to_delete_list,  delete_resource, resources } from "@/store";
import 'vue-select/dist/vue-select.css';

import ResourceTable from './ResourceTable.vue';
import { DirectiveBinding } from 'vue';

const show_resources: Ref<Array<any>> = ref([])
function get_resources() {
  show_resources.value = []
  to_delete_list.value.forEach((resource_id: string) => {
    if(resources.value != undefined){
        show_resources.value.push(resources.value.filter((resource: any) => resource.resource_id === resource_id)[0])
    }
    }
  );
  
  return show_resources.value;
}



function delete_resources() {
  to_delete_list.value.forEach((resource_id: string) => {
    delete_resource(resource_id);
  });
  to_delete_list.value = [];
}

</script>
