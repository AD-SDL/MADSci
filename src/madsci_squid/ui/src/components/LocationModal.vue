<template>
  <v-dialog class="pa-3" v-slot:default="{ isActive }">
    <v-card>
      <v-card-title>
        <h2 class="title">Location: {{ modal_title }}</h2>
        {{modal_text.location_id}}
        <h3>Lookup Values:</h3>
        <div v-for="value, key in get_location_object(workcell_state, modal_text).lookup">

          {{ key }} : {{ value }}

        </div>
        <v-btn v-if="!add_lookup_toggle" @click="add_lookup_toggle = !add_lookup_toggle">Add or Replace Lookup</v-btn>
      <div v-if="add_lookup_toggle" >
        <v-select class="w-25" height="20px" v-model="node_to_add" :items="Object.keys(workcell_state.nodes)"
                          dense>


    </v-select>
    <v-text-field v-model="add_lookup_value"
                          dense>
                          <template #append>

                            <v-btn @click="get_location(node_to_add)">Get Current Location</v-btn>
                            <v-btn @click="submit_location(node_to_add); add_lookup_toggle = !add_lookup_toggle">Submit</v-btn>
                          </template>
      </v-text-field>
      </div>
      <h3>Resource Info: </h3>
      <div v-if="get_resource(resources, modal_text) != null">
        <div v-if="get_resource(resources, modal_text).base_type=='stack'">
          <Stack :resource="get_resource(resources, modal_text)"/>
        </div>
        <div v-else-if="get_resource(resources, modal_text).base_type=='slot'">
          <Slot :resource="get_resource(resources, modal_text)" />
        </div>
        <div v-else>
          <Resource :resource="get_resource(resources, modal_text)" />
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
const props = defineProps(['modal_title', 'modal_text'])
const flowdef = ref(false)
import { urls, resources, workcell_state } from '../store';
import Stack from "./ResourceComponents/Stack.vue";
import Slot from "./ResourceComponents/Slot.vue";
import Resource from "./ResourceComponents/Resource.vue";
const loc_text = ref(props.modal_text)
const add_lookup_toggle = ref(false)
const node_to_add = ref()
const add_lookup_value = ref()
loc_text.value=props.modal_text


async function get_location(node: string): Promise<any>{
  var loc_data = await ((await fetch(urls.value.workcell_manager.concat('admin/get_location/').concat(node))).json())
  add_lookup_value.value = JSON.stringify(loc_data[0].data)
}

async function submit_location(node: string): Promise<any>{
  var test = await ((await fetch(urls.value.workcell_manager.concat('location/').concat(props.modal_text.location_id).concat("/add_lookup/").concat(node),
    {method: "POST",
    headers: {
    'Content-Type': 'application/json'
    },
     body: JSON.stringify({"lookup_val": JSON.parse(add_lookup_value.value)})
  }

)

).json())
}

function get_location_object(workcell_state: any, location: any) {
  console.log(workcell_state.locations)
   var new_location = workcell_state.locations[location["location_id"]]
    return new_location
}


function get_resource(resources: any, location: any) {
  if ("resource_id" in location && location.resource_id != null) {
   var resource = resources.find((element: any) => element.resource_id == location["resource_id"])
    return resource
  }
  return null
}
</script>
