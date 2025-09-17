<template>
 <LocationModal :location="modal_text" :location_name="modal_title" v-model="modal" />
 <AddLocationModal v-model="add_modal" />
  <v-card class="pa-1 ma-1" col="3" title="Locations">
    <v-card-text>
      <v-data-table :headers="location_headers" hover
      :items="location_items(locations, resources)"
      no-data-text="No Locations" density="compact" :sort-by="sortBy" :hide-default-footer="location_items(locations, resources).length <= 10">
      <template v-slot:item="{ item }: { item: any }">
        <tr @click="set_modal(item.name || item.location_name, item)">
          <td>{{ item.name || item.location_name }}</td>
          <td>{{ get_resource(resources, item) }}</td>
          <td>{{ item.location_id }}</td>
          <td>{{ Object.keys(item.lookup_values || item.lookup || {}) }}</td>
        </tr>
      </template>
    </v-data-table>
    <v-btn @click="active_add()">Add Location</v-btn>


    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { ref } from 'vue';

import { VDataTable } from 'vuetify/components';

import {
  locations,
  resources,
  workcell_state,
} from '@/store';

import AddLocationModal from './AddLocationModal.vue';
import LocationModal from './LocationModal.vue';

const modal_title = ref()
const modal_text = ref()
const modal = ref(false)
const add_modal = ref(false)

const sortBy: VDataTable['sortBy'] = [{ key: 'occupied', order: 'desc' }];
const location_headers = [
  { title: 'Name', key: 'name' },
  { title: 'Occupied', key: 'occupied', sort: (a: string, b: string) => occupied_compare(a, b) },
  { title: 'ID', key: 'location_id' },
  { title: 'Nodes', key: 'nodes' },

]

function occupied_compare(a: string, b: string) {
  if (a == "Occupied") {
    return 1
   } else if(a == "Empty") {
     if (b == "Occupied") {
      return -1

     } else {
      return 1
     }


   } else {
    return -1
   }
}


const set_modal = (title: string, value: Object) => {
  modal_title.value = title
  modal_text.value = value
  modal.value = true
}

function get_resource (resources: any, location: any) {
  if (location && "resource_id" in location && location.resource_id != null) {
   var resource = resources.find((element: any) => element.resource_id == location["resource_id"])
  } else {
    return "None"
  }
  if (resource && "quantity" in resource) {
    if (resource.quantity > 0) {
      return "Occupied"
    }
    return "Empty"
  }
  return "None"
}


function location_items(locations: any, resources: any) {
  var new_locations: any = []
  Object.values(locations || {}).forEach((location: any) => {
    location["occupied"] = get_resource(resources, location);
    location["name"] = location.name || location.location_name; // Ensure backwards compatibility
    new_locations.push(location);
  })
  return new_locations

}
function active_add() {
  add_modal.value=true
}
</script>
