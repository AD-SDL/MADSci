<template>
    <ResourceModal :modal_title="modal_title" :modal_text="modal_text" v-model="modal" />
    <AddResourceModal :modal_title="modal_title" :modal_text="modal_text" v-model="add_modal" />
    <!-- eslint-disable vue/no-parsing-error-->
    <v-data-table :headers="arg_headers" hover
      :items="resources"
      no-data-text="No Resources" density="compact" :sort-by="sortBy" :hide-default-footer="resources.length <= 10">
      <template v-slot:item="{ item }: { item: any }">
        <tr @click="set_modal(item.resource_name, item)">
          <td>{{ item.resource_name }}</td>
          <td>{{ item.base_type }}</td>
          <td>{{ item.created_at }}</td>
          <td>{{ item.resource_id }}</td>
          <td><v-btn @click.stop=delete_resource(item.resource_id)>Delete</v-btn></td>
        </tr>
      </template>
    </v-data-table>
    <v-btn @click="active_add()">Add Resource</v-btn>
</template>

<script setup lang="ts">
import { resources, urls } from "@/store";
import { ref } from 'vue';
import { VDataTable } from 'vuetify/components';
import AddResourceModal from "./AddResourceModal.vue";

const modal = ref(false)
const add_modal = ref(false)
const modal_text = ref()
const modal_title = ref()
const sortBy: VDataTable['sortBy'] = [{ key: 'created_at', order: 'desc' }];
const arg_headers = [
  { title: 'Name', key: 'resource_name' },
  { title: 'Base Type', key: 'base_type' },
  { title: 'Created At', key: 'created_at' },
  { title: 'ID', key: 'resource_id' },
]
const set_modal = (title: string, value: Object) => {
  modal_title.value = title
  modal_text.value = value
  modal.value = true
}

const active_add = () => {
  add_modal.value = true
}


const delete_resource = (resource_id: string) => {
  fetch(urls.value.resource_manager.concat('resource/').concat(resource_id), {
    method: "DELETE",
  });

}
</script>
