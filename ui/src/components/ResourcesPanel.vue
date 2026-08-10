
<template>
<AddResourceModal v-model="add_modal" />
<ResourceTable :resources=resources :parent_id="null" :hide_header="false"/>
<v-btn @click="active_add()">Add Resource</v-btn>
<v-btn @click="delete_selected()">Delete Selected</v-btn>

</template>


<script setup lang="ts">

import ResourceTable from './ResourceTable.vue';
import AddResourceModal from './AddResourceModal.vue';
import { ref } from 'vue';
import { resources, to_delete_list,  delete_resource } from "@/store";
const add_modal = ref(false)
function active_add() {
  add_modal.value=true
}
function delete_selected() {
  console.log("Deleting selected resources: ", to_delete_list.value)
  to_delete_list.value.forEach((resource_id: string) => {
    delete_resource(resource_id);
  });
  to_delete_list.value = [];

}


</script>
