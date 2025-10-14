<template>
  <v-dialog class="pa-3" v-slot:default="{ isActive }" max-width="800px">
    <v-card>
      <v-card-title class="d-flex justify-space-between align-center">
        <h2 class="title">Location: {{ location_name }}</h2>
        <v-btn
          icon
          color="error"
          @click="confirmDelete"
          :disabled="deleting"
          v-tooltip="'Delete Location'"
        >
          <v-icon>mdi-delete</v-icon>
        </v-btn>
      </v-card-title>

      <v-card-text>
        <!-- Location ID -->
        <v-row class="mb-3">
          <v-col>
            <v-chip color="primary" variant="outlined">
              <strong>ID:</strong> {{ location.location_id }}
            </v-chip>
          </v-col>
        </v-row>

        <!-- Representations Section -->
        <v-row class="mb-4">
          <v-col>
            <h3 class="mb-2">Representations:</h3>
            <v-card variant="outlined" class="pa-3">
              <div v-if="Object.keys((location as any).representations || {}).length === 0" class="text-grey">
                No representations defined
              </div>
              <div v-else>
                <v-chip
                  v-for="(value, key) in ((location as any).representations || {})"
                  :key="key"
                  class="ma-1"
                  color="primary"
                  variant="outlined"
                  closable
                  @click:close="confirmRemoveRepresentation(String(key))"
                >
                  <strong>{{ key }}:</strong> {{ JSON.stringify(value) }}
                </v-chip>
              </div>

              <!-- Add/Replace Representation -->
              <v-btn
                v-if="!add_representation_toggle"
                @click="add_representation_toggle = !add_representation_toggle"
                color="primary"
                variant="outlined"
                class="mt-2"
              >
                <v-icon start>mdi-plus</v-icon>
                Add or Replace Representation
              </v-btn>

              <v-expand-transition>
                <div v-if="add_representation_toggle" class="mt-3">
                  <v-select
                    v-model="node_to_add"
                    :items="Object.keys(workcell_state?.nodes ?? {})"
                    label="Select Node"
                    variant="outlined"
                    density="compact"
                    class="mb-2"
                  />
                  <v-text-field
                    v-model="add_representation_value"
                    label="Representation Value (JSON)"
                    variant="outlined"
                    density="compact"
                    rows="3"
                    multiline
                  >
                    <template #append>
                      <v-btn
                        @click="get_location(node_to_add)"
                        color="secondary"
                        variant="outlined"
                        size="small"
                        class="mr-1"
                      >
                        Get Current Position
                      </v-btn>
                      <v-btn
                        @click="submit_location_representation(node_to_add); add_representation_toggle = !add_representation_toggle"
                        color="primary"
                        size="small"
                      >
                        Submit
                      </v-btn>
                    </template>
                  </v-text-field>
                  <v-btn
                    @click="add_representation_toggle = false"
                    color="grey"
                    variant="text"
                    size="small"
                  >
                    Cancel
                  </v-btn>
                </div>
              </v-expand-transition>
            </v-card>
          </v-col>
        </v-row>

        <!-- Resource Section -->
        <v-row class="mb-4">
          <v-col>
            <h3 class="mb-2">Resource Info:</h3>
            <v-card variant="outlined" class="pa-3">
              <div v-if="get_resource(resources, location) != null">
                <div class="d-flex justify-space-between align-center mb-2">
                  <v-chip color="success" variant="outlined">
                    Resource Attached: {{ get_resource(resources, location).resource_id }}
                  </v-chip>
                  <v-btn
                    @click="confirmDetachResource"
                    color="warning"
                    variant="outlined"
                    size="small"
                    :disabled="detaching"
                  >
                    <v-icon start>mdi-link-off</v-icon>
                    Detach Resource
                  </v-btn>
                </div>

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
              <div v-else class="d-flex justify-space-between align-center">
                <span class="text-grey">No resource attached</span>
                <v-btn
                  @click="attach_resource_toggle = !attach_resource_toggle"
                  color="primary"
                  variant="outlined"
                  size="small"
                >
                  <v-icon start>mdi-link</v-icon>
                  Attach Resource
                </v-btn>
              </div>

              <!-- Attach Resource Interface -->
              <v-expand-transition>
                <div v-if="attach_resource_toggle" class="mt-3">
                  <v-text-field
                    v-model="resource_to_attach"
                    label="Resource ID to Attach"
                    variant="outlined"
                    density="compact"
                  >
                    <template #append>
                      <v-btn
                        @click="submit_attach_resource(); attach_resource_toggle = false"
                        color="primary"
                        size="small"
                        :disabled="!resource_to_attach || attaching"
                      >
                        Attach
                      </v-btn>
                    </template>
                  </v-text-field>
                  <v-btn
                    @click="attach_resource_toggle = false"
                    color="grey"
                    variant="text"
                    size="small"
                  >
                    Cancel
                  </v-btn>
                </div>
              </v-expand-transition>
            </v-card>
          </v-col>
        </v-row>
      </v-card-text>

      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn
          @click="isActive.value = false; resetToggles()"
          color="primary"
          variant="text"
        >
          Close
        </v-btn>
      </v-card-actions>
    </v-card>

    <!-- Confirmation Dialogs -->
    <v-dialog v-model="deleteConfirmDialog" max-width="400">
      <v-card>
        <v-card-title class="text-h6">Confirm Delete</v-card-title>
        <v-card-text>
          Are you sure you want to delete location "{{ location_name }}"? This action cannot be undone.
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="deleteConfirmDialog = false" color="grey" variant="text">Cancel</v-btn>
          <v-btn @click="deleteLocation" color="error" :loading="deleting">Delete</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="removeRepConfirmDialog" max-width="400">
      <v-card>
        <v-card-title class="text-h6">Remove Representation</v-card-title>
        <v-card-text>
          Are you sure you want to remove the "{{ representationToRemove }}" representation from this location?
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="removeRepConfirmDialog = false" color="grey" variant="text">Cancel</v-btn>
          <v-btn @click="removeRepresentation" color="warning" :loading="removing">Remove</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="detachConfirmDialog" max-width="400">
      <v-card>
        <v-card-title class="text-h6">Detach Resource</v-card-title>
        <v-card-text>
          Are you sure you want to detach the resource from this location?
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="detachConfirmDialog = false" color="grey" variant="text">Cancel</v-btn>
          <v-btn @click="detachResource" color="warning" :loading="detaching">Detach</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue';

import {
  locations_url,
  refreshLocations,
  resources,
  urls,
  workcell_state,
} from '../store';
import { Location } from '../types/workcell_types';
import Resource from './ResourceComponents/Resource.vue';
import Slot from './ResourceComponents/Slot.vue';
import Stack from './ResourceComponents/Stack.vue';

interface LocationModalProps {
  location_name: string;
  location: Location;
}

const props = defineProps<LocationModalProps>()

// UI state
const add_representation_toggle = ref(false)
const attach_resource_toggle = ref(false)
const node_to_add = ref()
const add_representation_value = ref()
const resource_to_attach = ref()

// Confirmation dialogs
const deleteConfirmDialog = ref(false)
const removeRepConfirmDialog = ref(false)
const detachConfirmDialog = ref(false)
const representationToRemove = ref('')

// Loading states
const deleting = ref(false)
const removing = ref(false)
const detaching = ref(false)
const attaching = ref(false)

// Reset UI toggles
function resetToggles() {
  add_representation_toggle.value = false
  attach_resource_toggle.value = false
  deleteConfirmDialog.value = false
  removeRepConfirmDialog.value = false
  detachConfirmDialog.value = false
}

// Get the current location representation from a node
async function get_location(node_name: string): Promise<void>{
  try {
    const loc_data = await ((await fetch(urls.value.workcell_server_url.concat('admin/get_location/').concat(node_name), {method: 'POST'})).json())
    console.log(loc_data)
    add_representation_value.value = JSON.stringify(loc_data.data)
  } catch (error) {
    console.error('Failed to get location position:', error)
  }
}

// Submit new/updated representation
async function submit_location_representation(node_name: string): Promise<void>{
  try {
    const api_url = locations_url.value ?
      locations_url.value.replace('/locations', '/location/').concat(props.location.location_id || '').concat("/set_representation/").concat(node_name) :
      urls.value.workcell_server_url.concat('location/').concat(props.location.location_id || '').concat("/set_representation/").concat(node_name);

    await fetch(api_url, {
      method: "POST",
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(JSON.parse(add_representation_value.value))
    })

    // Refresh locations data
    await refreshLocations()
  } catch (error) {
    console.error('Failed to submit representation:', error)
    alert('Failed to submit representation. Please try again.')
  }
}

// Confirm remove representation
function confirmRemoveRepresentation(nodeName: string) {
  representationToRemove.value = nodeName
  removeRepConfirmDialog.value = true
}

// Remove representation
async function removeRepresentation(): Promise<void> {
  removing.value = true
  try {
    const api_url = locations_url.value ?
      locations_url.value.replace('/locations', '/location/').concat(props.location.location_id || '').concat("/remove_representation/").concat(representationToRemove.value) :
      null;

    if (!api_url) {
      throw new Error('LocationManager not available for removing representations')
    }

    const response = await fetch(api_url, {
      method: "DELETE",
      headers: {
        'Content-Type': 'application/json'
      }
    })

    if (!response.ok) {
      throw new Error(`Failed to remove representation: ${response.statusText}`)
    }

    removeRepConfirmDialog.value = false
    // Refresh locations data
    await refreshLocations()
  } catch (error) {
    console.error('Failed to remove representation:', error)
    alert('Failed to remove representation. Please try again.')
  } finally {
    removing.value = false
  }
}

// Confirm delete location
function confirmDelete() {
  deleteConfirmDialog.value = true
}

// Delete location
async function deleteLocation(): Promise<void> {
  deleting.value = true
  try {
    const api_url = locations_url.value ?
      locations_url.value.replace('/locations', '/location/').concat(props.location.location_id || '') :
      null;

    if (!api_url) {
      throw new Error('LocationManager not available for deleting locations')
    }

    const response = await fetch(api_url, {
      method: "DELETE",
      headers: {
        'Content-Type': 'application/json'
      }
    })

    if (!response.ok) {
      throw new Error(`Failed to delete location: ${response.statusText}`)
    }

    deleteConfirmDialog.value = false
    // Refresh locations data
    await refreshLocations()
  } catch (error) {
    console.error('Failed to delete location:', error)
    alert('Failed to delete location. Please try again.')
  } finally {
    deleting.value = false
  }
}

// Confirm detach resource
function confirmDetachResource() {
  detachConfirmDialog.value = true
}

// Detach resource
async function detachResource(): Promise<void> {
  detaching.value = true
  try {
    const api_url = locations_url.value ?
      locations_url.value.replace('/locations', '/location/').concat(props.location.location_id || '').concat("/detach_resource") :
      null;

    if (!api_url) {
      throw new Error('LocationManager not available for detaching resources')
    }

    const response = await fetch(api_url, {
      method: "DELETE",
      headers: {
        'Content-Type': 'application/json'
      }
    })

    if (!response.ok) {
      throw new Error(`Failed to detach resource: ${response.statusText}`)
    }

    detachConfirmDialog.value = false
    // Refresh locations data
    await refreshLocations()
  } catch (error) {
    console.error('Failed to detach resource:', error)
    alert('Failed to detach resource. Please try again.')
  } finally {
    detaching.value = false
  }
}

// Attach resource
async function submit_attach_resource(): Promise<void> {
  attaching.value = true
  try {
    const api_url = locations_url.value ?
      locations_url.value.replace('/locations', '/location/').concat(props.location.location_id || '').concat("/attach_resource") :
      null;

    if (!api_url) {
      throw new Error('LocationManager not available for attaching resources')
    }

    // Use query parameters instead of request body
    const url = new URL(api_url)
    url.searchParams.append('resource_id', resource_to_attach.value)

    const response = await fetch(url.toString(), {
      method: "POST",
      headers: {
        'Content-Type': 'application/json'
      }
    })

    if (!response.ok) {
      throw new Error(`Failed to attach resource: ${response.statusText}`)
    }

    resource_to_attach.value = ''
    // Refresh locations data
    await refreshLocations()
  } catch (error) {
    console.error('Failed to attach resource:', error)
    alert('Failed to attach resource. Please try again.')
  } finally {
    attaching.value = false
  }
}

function get_resource(resources: any, location: Location) {
  if ("resource_id" in location && location.resource_id != null) {
   var resource = resources.find((element: any) => element.resource_id == location["resource_id"])
    return resource
  }
  return null
}
</script>
