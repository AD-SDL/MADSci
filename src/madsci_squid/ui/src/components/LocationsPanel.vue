<template>
 <LocationModal :modal_title="modal_title" :modal_text="modal_text" v-model="modal" />
 <AddLocationModal v-model="add_modal" />
  <v-card class="pa-1 ma-1" col="3" title="Locations">
    <v-card-text>
      <v-container v-if="Object.keys(workcell_state.locations).length > 0" fluid class="pa-1">
        <v-row no-gutter wrap justify-content class="pa-1">
          <v-col v-for="value, key in workcell_state.locations" class="pa-1" cols=12 sm=6 md=4 lg=3 xl=2>
            <v-card-text @click="set_modal(value.location_name, value)">
              <h3 wrap>{{ value.location_name }}</h3>
              <p wrap class="text-caption">
                {{ value.reservation }}
              </p>
              <p v-if="get_resource(resources, value)"> Occupied</p>
              <p v-else> Empty</p>
            </v-card-text>
          </v-col>
          <v-col  class="pa-1" cols=12 sm=6 md=4 lg=3 xl=2>
            <v-card-text @click="add_modal = true">
              <h2>+</h2>
            </v-card-text>
          </v-col>
        </v-row>
      </v-container>
      <p v-else>No Locations Yet</p>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import LocationModal from './LocationModal.vue';
import AddLocationModal from './AddLocationModal.vue';
import { ref } from 'vue';
const props = defineProps(['locations'])
const modal_title = ref()
const modal_text = ref()
const modal = ref(false)
const add_modal = ref(false)
import { resources, workcell_state } from "@/store";

const set_modal = (title: string, value: Object) => {
  modal_title.value = title
  modal_text.value = value
  modal.value = true
}

function get_resource (resources: any, location: any) {
  if ("resource_id" in location && location.resource_id != null) {
   var resource = resources.find((element: any) => element.resource_id == location["resource_id"])
  } else {
    return false
  }
  if ("quantity" in resource) {
    if (resource.quantity > 0) {
      return true
    }
    return false
  }
  return false
}
</script>
