<template>
 <LocationModal :location="modal_text" :location_name="modal_title" v-model="modal" />
 <AddLocationModal v-model="add_modal" />

 <!-- Conditional Layout: Tabbed view, stacked view, or responsive grid -->
 <div v-if="tabbedLayout">
   <!-- Tabbed Layout -->
   <v-card class="pa-1 ma-1">
     <v-tabs v-model="activeTab" color="primary" align-tabs="center">
       <v-tab value="graph">
         <v-icon start>mdi-graph-outline</v-icon>
         Transfer Graph
       </v-tab>
       <v-tab value="table">
         <v-icon start>mdi-table</v-icon>
         Locations Table
       </v-tab>
     </v-tabs>

     <v-window v-model="activeTab">
       <v-window-item value="graph">
         <v-card-text>
           <TransferGraph
             :locations="locations"
             :resources="resources"
             @node-click="handleNodeClick"
           />
         </v-card-text>
       </v-window-item>

       <v-window-item value="table">
         <v-card-text>
           <v-data-table :headers="location_headers" hover
           :items="location_items(locations, resources)"
           no-data-text="No Locations" density="compact" :sort-by="sortBy" :hide-default-footer="location_items(locations, resources).length <= 10">
           <template v-slot:item="{ item }: { item: any }">
             <tr @click="set_modal(item.name || item.location_name, item)">
               <td>{{ item.name || item.location_name }}</td>
               <td>{{ get_resource(resources, item) }}</td>
               <td>{{ item.location_id }}</td>
               <td>{{ Object.keys(item.representations || {}) }}</td>
             </tr>
           </template>
         </v-data-table>
         <v-btn @click="active_add()">Add Location</v-btn>
         </v-card-text>
       </v-window-item>
     </v-window>
   </v-card>
 </div>

 <div v-else-if="!responsiveLayout">
   <!-- Always Stacked Layout -->
   <!-- Transfer Graph Section -->
   <div class="mb-4">
     <TransferGraph
       :locations="locations"
       :resources="resources"
       @node-click="handleNodeClick"
     />
   </div>

   <!-- Locations Table Section -->
   <v-card class="pa-1 ma-1" title="Locations">
      <v-card-text>
        <v-data-table :headers="location_headers" hover
        :items="location_items(locations, resources)"
        no-data-text="No Locations" density="compact" :sort-by="sortBy" :hide-default-footer="location_items(locations, resources).length <= 10">
        <template v-slot:item="{ item }: { item: any }">
          <tr @click="set_modal(item.name || item.location_name, item)">
            <td>{{ item.name || item.location_name }}</td>
            <td>{{ get_resource(resources, item) }}</td>
            <td>{{ item.location_id }}</td>
            <td>{{ Object.keys(item.representations || {}) }}</td>
          </tr>
        </template>
      </v-data-table>
      <v-btn @click="active_add()">Add Location</v-btn>
      </v-card-text>
    </v-card>
 </div>

 <v-row v-else>
   <!-- Responsive Layout: Side by side on large screens, stacked on smaller screens -->
   <!-- Transfer Graph Section -->
   <v-col cols="12" lg="6" xl="6">
     <TransferGraph
       :locations="locations"
       :resources="resources"
       @node-click="handleNodeClick"
     />
   </v-col>

   <!-- Locations Table Section -->
   <v-col cols="12" lg="6" xl="6">
     <v-card class="pa-1 ma-1" title="Locations">
        <v-card-text>
          <v-data-table :headers="location_headers" hover
          :items="location_items(locations, resources)"
          no-data-text="No Locations" density="compact" :sort-by="sortBy" :hide-default-footer="location_items(locations, resources).length <= 10">
          <template v-slot:item="{ item }: { item: any }">
            <tr @click="set_modal(item.name || item.location_name, item)">
              <td>{{ item.name || item.location_name }}</td>
              <td>{{ get_resource(resources, item) }}</td>
              <td>{{ item.location_id }}</td>
              <td>{{ Object.keys(item.representations || {}) }}</td>
            </tr>
          </template>
        </v-data-table>
        <v-btn @click="active_add()">Add Location</v-btn>
        </v-card-text>
      </v-card>
   </v-col>
 </v-row>
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
import TransferGraph from './TransferGraph.vue';

// Props
interface LocationsPanelProps {
  responsiveLayout?: boolean;
  tabbedLayout?: boolean;
}

const props = withDefaults(defineProps<LocationsPanelProps>(), {
  responsiveLayout: true, // Default to responsive layout
  tabbedLayout: false, // Default to no tabs
});

const modal_title = ref()
const modal_text = ref()
const modal = ref(false)
const add_modal = ref(false)
const activeTab = ref('graph') // Default to showing the graph tab

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

function handleNodeClick(node: any) {
  // Open the location modal when a node is clicked in the transfer graph
  set_modal(node.name, node.originalLocation);
}
</script>
