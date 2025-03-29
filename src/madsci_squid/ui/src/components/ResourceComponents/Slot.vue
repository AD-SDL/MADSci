<template>
    <h5>Base Type:</h5>
     {{ resource.base_type }}
     <h5>Quantity:</h5>
     {{ resources.find((element: any) => element.resource_id == resource.resource_id).quantity }}

     <h5>Children</h5>
     <v-data-table :headers="arg_headers" hover
      :items="resources.find((element: any) => element.resource_id == resource.resource_id).children"
      no-data-text="No Children" density="compact" :hide-default-footer="resource.children.length <= 10">
      <template v-slot:item="{ item }: { item: any }">
        <tr>
          <td>{{ item.resource_name }}</td>
          <td>{{ item.base_type }}</td>
          <td>{{ item.created_at }}</td>
          <td>{{ item.resource_id }}</td>
        </tr>
      </template>
    </v-data-table>
    <v-btn @click=pop(resource.resource_id)>Pop</v-btn>
    <h3>Push:</h3>
    <v-select class="pt-5 mr-2 w-50" height="20px" v-model="push_id" :items="resource_list"
                          dense>
                          <template #append>
                            <v-btn @click="push(resource.resource_id, push_id)">Push</v-btn>
                          </template>
    </v-select>

    <vue-json-pretty :data="resource" />
</template>

<script setup lang="ts">

import VueJsonPretty from 'vue-json-pretty';
import 'vue-json-pretty/lib/styles.css';
const props = defineProps(['resource'])
import { resources, urls } from "@/store";
import { VDataTable } from 'vuetify/components';
import { ref } from 'vue';
const push_id = ref()
const arg_headers = [
  { title: 'Name', key: 'resource_name' },
  { title: 'Base Type', key: 'base_type' },
  { title: 'Created At', key: 'created_at' },
  { title: 'ID', key: 'resource_id' },
]
const resource_list = ref()

resource_list.value = []
const test_res = ref()

resources.value.forEach((new_resource: any) => {if(new_resource.resource_id != props.resource.resource_id) {resource_list.value.push({"title": new_resource.resource_name.concat(" : ").concat(new_resource.resource_id), "value": new_resource.resource_id})}})



const push = (resource_id: string, push_id: string) => {
  fetch(urls.value.resource_manager.concat('resource/').concat(resource_id).concat('/push'), {
    body: JSON.stringify({"child_id": push_id}),
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    }
  });

}
const pop = (resource_id: string) => {
  fetch(urls.value.resource_manager.concat('resource/').concat(resource_id).concat('/pop'), {
    method: "POST",
  });
}


</script>
