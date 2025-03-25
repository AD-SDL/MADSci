<template>
    <ResourceModal :modal_title="modal_title" :modal_text="modal_text" v-model="modal" />
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
        </tr>
      </template>
    </v-data-table>
</template>

<script setup lang="ts">
import { resources } from "@/store";
import { ref } from 'vue';
import { VDataTable } from 'vuetify/components';

const modal = ref(false)
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
</script>
