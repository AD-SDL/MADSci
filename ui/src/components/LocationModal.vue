<template>
  <v-dialog class="pa-3" v-slot:default="{ isActive }">
    <v-card>
      <v-card-title>
        <h2 class="title">Location: {{ location_name }}</h2>
        {{location.location_id}}
        <h3>Lookup Values:</h3>
        <div v-for="value, key in ((location as any).lookup_values || location.lookup)">

          {{ key }} : {{ value }}

        </div>
        <v-btn v-if="!add_lookup_toggle" @click="add_lookup_toggle = !add_lookup_toggle">Add or Replace Lookup</v-btn>
      <div v-if="add_lookup_toggle" >
        <v-select class="w-25" height="20px" v-model="node_to_add" :items="Object.keys(workcell_state?.nodes ?? {})"
                          dense>


    </v-select>
    <v-text-field v-model="add_lookup_value"
                          dense>
                          <template #append>

                            <v-btn @click="get_location(node_to_add)">Get Current Position</v-btn>
                            <v-btn @click="submit_location_lookup(node_to_add); add_lookup_toggle = !add_lookup_toggle">Submit</v-btn>
                          </template>
      </v-text-field>
      </div>
      <h3>Resource Info: </h3>
      <div v-if="get_resource(resources, location) != null">
        <div v-if="get_resource(resources, location).base_type=='stack'">
          <Stack :resource="get_resource(resources, location)"/>
        </div>
        <div v-else-if="get_resource(resources, location).base_type=='slot'">
          <Slot :resource="get_resource(resources, location)" />
        </div>
        <div v-else>
          <Resource :resource="get_resource(resources, location)" />
      </div>
    </div>
      </v-card-title>
      <v-card-text>

      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn flat @click="isActive.value = false; add_lookup_toggle=false" class="primary--text">close</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue';

import {
  locations_url,
  resources,
  urls,
  workcell_state,
} from '../store';
import { Location } from '../types/workcell_types';
import Resource from './ResourceComponents/Resource.vue';
import Slot from './ResourceComponents/Slot.vue';
import Stack from './ResourceComponents/Stack.vue';

const flowdef = ref(false)

interface LocationModalProps {
      location_name: string;
      location: Location;
    }


const props = defineProps<LocationModalProps>()
const loc_text = ref(props.location)
const add_lookup_toggle = ref(false)
const node_to_add = ref()
const add_lookup_value = ref()
loc_text.value=props.location


async function get_location(location_name: string): Promise<void>{
  var loc_data = await ((await fetch(urls.value.workcell_server_url.concat('admin/get_location/').concat(location_name))).json())
  add_lookup_value.value = JSON.stringify(loc_data[0].data)
}

async function submit_location_lookup(node_name: string): Promise<void>{
  // Use LocationManager API if available, fallback to WorkcellManager
  const api_url = locations_url.value ?
    locations_url.value.replace('/locations', '/location/').concat(props.location.location_id || '').concat("/add_lookup/").concat(node_name) :
    urls.value.workcell_server_url.concat('location/').concat(props.location.location_id || '').concat("/add_lookup/").concat(node_name);

  await ((await fetch(api_url,
    {method: "POST",
    headers: {
    'Content-Type': 'application/json'
    },
     body: JSON.stringify({"lookup_val": JSON.parse(add_lookup_value.value)})
  }

)

))
}




function get_resource(resources: any, location: Location) {
  if ("resource_id" in location && location.resource_id != null) {
   var resource = resources.find((element: any) => element.resource_id == location["resource_id"])
    return resource
  }
  return null
}
</script>
