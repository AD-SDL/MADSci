<template>
  <v-dialog class="pa-3" v-slot:default="{ isActive }">
    <v-card>
      <v-card-title>
        <h2 class="title">Add Location:</h2>
      </v-card-title>
      <v-card-text>
        <h4>Location Name:</h4>
        <v-text-field class="pt-5 mr-2 w-25" height="20px" v-model="location_name"
                          dense>
                        </v-text-field>
        <h4>Representation Info:</h4>
        <div v-for="(value, key) in representations">
          {{ key }} : {{ value}}
        </div>
        <div>
        <v-select class="w-25" height="20px" v-model="node_to_add" :items="Object.keys(workcell_state?.nodes ?? {})"
                          dense>


      </v-select>
      <v-text-field v-model="add_representation_value"
                          dense>
                          <template #append>

                            <v-btn @click="get_location(node_to_add)">Get Current Location</v-btn>
                            <v-btn @click="append_representation_to_location(node_to_add)">Add or Update Representation</v-btn>

                          </template>
      </v-text-field>
      <v-btn v-if="!add_resource" @click="add_resource=true">Add Resource</v-btn>
      </div>
        <div v-if="add_resource">
        <h4 class="title">Resource Definition:</h4>
        <label for="base_type"> base_type</label>

        <v-select id="base_type" class="w-25" v-model="base_type" :items="base_types"/>
  <div v-for="(field, index) in formFields" :key="index">

    <label :for="field.label">{{ field.label }}</label>
  <div class="d-flex w-25">
    <v-text-field class="pt-5 mr-2 w-25" :id="field.label" height="20px" v-model="field.value"
                          dense>
                          <template #append>
                            <v-btn @click="removeField(index)">Remove</v-btn>
                          </template>
                        </v-text-field>

  </div>
</div>

  <h4 class="mt-3">Add more fields:</h4>
  <label for="new_field">New Field Name</label>
  <v-text-field
    solo class="pt-5 w-25" id="new_field" height="20px" v-model="new_name"
                          dense>
                          <template #append>
                            <v-btn type="button" @click="addField">Add Field</v-btn>
                          </template>
                        </v-text-field>
                      </div>
  <v-btn @click="submitLocation(); isActive.value=false">Submit Location</v-btn>
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn flat @click="isActive.value = false" class="primary--text">close</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>

</template>

<script setup lang="ts">
import { ref } from 'vue';

import { locations_url, urls } from '@/store';

import { workcell_state } from '../store';

const new_name = ref()
const base_type = ref()
const node_to_add = ref()
const add_representation_value = ref()
const representations = ref()
const location_name = ref()
const add_resource = ref(false)
const formFields =  ref([
{ label: 'resource_name', value: null, placeholder: 'Enter value' },
])
const base_types = ref([
  "resource",
  "asset",
   "consumable",
    "discrete_consumable",
     "continuous_consumable",
      "container",
      "collection",
         "row",
         "grid",
        "voxel_grid",
         "stack",
         "queue",
         "pool",
         "slot",

])
representations.value = {}

function addField() {
      formFields.value.push({ label: new_name.value, value: null, placeholder: 'Enter value' });
    }

async function get_location(node: string): Promise<any>{
  var loc_data = await ((await fetch(urls.value.workcell_server_url.concat('admin/get_location/').concat(node))).json())
  add_representation_value.value = JSON.stringify(loc_data[0].data)
}


function append_representation_to_location(node: string) {
      representations.value[node] = add_representation_value.value
    }

function removeField(index: any) {
      formFields.value.splice(index, 1);
    }
function submitLocation() {
    var location: any = {}
    location["name"] = location_name.value // Use 'name' instead of 'location_name' for new API
    var new_representations: any  = {}
    Object.keys(representations.value).forEach((key: string) => {new_representations[key] = JSON.parse(representations.value[key])})
    location["representations"] = new_representations // Use 'representations' instead of 'references' or 'lookup_values'
    location["coordinates"] = { x: 0.0, y: 0.0, z: 0.0 } // Add default coordinates
    location["resource_ids"] = [] // Add empty resource_ids array
    var resource: any = {}
    formFields.value.forEach(function (field: any) {
      resource[field.label] = field.value
    });
    resource["base_type"] = base_type.value
    if(base_type.value != null) {
    location["resource_definition"] = resource
    }

    // Use LocationManager API if available, fallback to WorkcellManager
    const api_url = locations_url.value ?
      locations_url.value.replace('/locations', '/location') :
      urls.value.workcell_server_url.concat('location');

    fetch(api_url, {
    method: "POST",
    headers: {
    'Content-Type': 'application/json'
    },
     body: JSON.stringify(location)
  });

    }
</script>
