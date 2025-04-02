
<template>
<AddResourceModal v-model="add_modal" />
<ResourceTable :resources=resources :parent_id="null" :hide_header="false"/>
<v-btn @click="active_add()">Add Resource</v-btn>

</template>


<script setup lang="ts">

import ResourceTable from './ResourceTable.vue';
import AddResourceModal from './AddResourceModal.vue';
import { ref } from 'vue';
import { resources } from "@/store";
const add_modal = ref(false)
function active_add() {
  add_modal.value=true
}
</script>
