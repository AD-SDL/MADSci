<template>
  <v-dialog class="pa-3" v-slot:default="{ isActive }">
    <v-card>
      <v-card-title>
        <h2 class="title">Add Resource:</h2>
      </v-card-title>
      <v-card-text>
        <label for="base_type"> base_type</label>

        <v-select id="base_type" class="w-25" v-model="base_type" :options="base_types"/>
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
  <v-btn @click="submitResource(); isActive.value=false">Submit</v-btn>
  <h4 class="mt-3">Add more fields:</h4>
  <label for="new_field">New Field Name</label>
  <v-text-field
    solo class="pt-5 w-25" id="new_field" height="20px" v-model="new_name"
                          dense>
                          <template #append>
                            <v-btn type="button" @click="addField">Add Field</v-btn>
                          </template>
                        </v-text-field>


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
import { urls } from "@/store";
import vSelect from 'vue-select'
import 'vue-select/dist/vue-select.css';
const flowdef = ref(false)
const new_name = ref()
const base_type = ref()
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

function addField() {
      formFields.value.push({ label: new_name.value, value: null, placeholder: 'Enter value' });
    }
function removeField(index: any) {
      formFields.value.splice(index, 1);
    }
function submitResource() {
    var resource: any = {}
    formFields.value.forEach(function (field: any) {
      resource[field.label] = field.value
    });
    resource["base_type"] = base_type.value
    fetch(urls.value.resource_manager.concat('resource/add'), {
    method: "POST",
    headers: {
    'Content-Type': 'application/json'
    },
     body: JSON.stringify(resource)
  });

    }
</script>
