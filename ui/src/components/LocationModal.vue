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
                <v-card
                  v-for="(value, nodeName) in ((location as any).representations || {})"
                  :key="nodeName"
                  variant="tonal"
                  class="mb-2"
                >
                  <v-card-title class="d-flex align-center py-2 text-body-1">
                    <v-icon start size="small">mdi-robot</v-icon>
                    <strong>{{ nodeName }}</strong>
                    <v-chip
                      v-if="getTemplateForNode(String(nodeName))"
                      size="x-small"
                      color="info"
                      variant="outlined"
                      class="ml-2"
                    >
                      {{ getTemplateForNode(String(nodeName))!.template_name }}
                    </v-chip>
                    <v-spacer />
                    <v-btn
                      v-if="editingRepresentation !== String(nodeName)"
                      icon
                      size="x-small"
                      variant="text"
                      @click="startEditRepresentation(String(nodeName), value as Record<string, unknown>)"
                      v-tooltip="'Edit'"
                    >
                      <v-icon size="small">mdi-pencil</v-icon>
                    </v-btn>
                    <v-btn
                      icon
                      size="x-small"
                      variant="text"
                      color="error"
                      @click="confirmRemoveRepresentation(String(nodeName))"
                      v-tooltip="'Remove'"
                    >
                      <v-icon size="small">mdi-close</v-icon>
                    </v-btn>
                  </v-card-title>

                  <v-card-text class="pt-0">
                    <!-- Editing mode with SchemaForm -->
                    <div v-if="editingRepresentation === String(nodeName)">
                      <SchemaForm
                        v-if="getTemplateForNode(String(nodeName))"
                        :template="getTemplateForNode(String(nodeName))!"
                        v-model="editFormValues"
                      />
                      <v-textarea
                        v-else
                        v-model="editJsonValue"
                        label="Representation Value (JSON)"
                        variant="outlined"
                        density="compact"
                        rows="4"
                        auto-grow
                      />
                      <div class="d-flex ga-2 mt-2">
                        <v-btn
                          @click="get_location_for_edit(String(nodeName))"
                          color="secondary"
                          variant="outlined"
                          size="small"
                        >
                          Get Current Position
                        </v-btn>
                        <v-btn
                          @click="saveEditRepresentation(String(nodeName))"
                          color="primary"
                          size="small"
                        >
                          Save
                        </v-btn>
                        <v-btn
                          @click="cancelEditRepresentation()"
                          color="grey"
                          variant="text"
                          size="small"
                        >
                          Cancel
                        </v-btn>
                      </div>
                    </div>

                    <!-- Read-only display -->
                    <div v-else>
                      <!-- Structured display when template is available -->
                      <v-table v-if="getTemplateForNode(String(nodeName))" density="compact">
                        <tbody>
                          <tr
                            v-for="field in getDisplayFields(String(nodeName), value as Record<string, unknown>)"
                            :key="field.key"
                          >
                            <td class="text-grey-darken-1" style="width: 40%;">
                              {{ field.label }}
                              <span v-if="field.required" class="text-error">*</span>
                            </td>
                            <td>
                              <code v-if="field.isJson">{{ field.displayValue }}</code>
                              <span v-else>{{ field.displayValue }}</span>
                            </td>
                          </tr>
                        </tbody>
                      </v-table>

                      <!-- Fallback: formatted JSON when no template -->
                      <pre v-else class="text-body-2" style="white-space: pre-wrap; word-break: break-word;">{{ JSON.stringify(value, null, 2) }}</pre>
                    </div>
                  </v-card-text>
                </v-card>
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
                    @update:model-value="onNodeSelected"
                  />

                  <!-- Template-based form (when node has representation templates) -->
                  <div v-if="selectedNodeTemplates.length > 0">
                    <v-select
                      v-if="selectedNodeTemplates.length > 1"
                      v-model="selectedTemplate"
                      :items="selectedNodeTemplates"
                      item-title="template_name"
                      :item-value="(item: any) => item"
                      label="Select Representation Template"
                      variant="outlined"
                      density="compact"
                      class="mb-2"
                    >
                      <template #item="{ props: itemProps, item }">
                        <v-list-item v-bind="itemProps">
                          <v-list-item-subtitle v-if="item.raw.description">
                            {{ item.raw.description }}
                          </v-list-item-subtitle>
                        </v-list-item>
                      </template>
                    </v-select>
                    <v-chip
                      v-else-if="selectedTemplate"
                      color="info"
                      variant="outlined"
                      class="mb-2"
                      size="small"
                    >
                      Template: {{ selectedTemplate.template_name }}
                    </v-chip>

                    <SchemaForm
                      v-if="selectedTemplate"
                      :template="selectedTemplate"
                      v-model="schemaFormValues"
                    />
                  </div>

                  <!-- Fallback: plain JSON editor (when no templates available) -->
                  <v-text-field
                    v-else
                    v-model="add_representation_value"
                    label="Representation Value (JSON)"
                    variant="outlined"
                    density="compact"
                    rows="3"
                    multiline
                  />

                  <div class="d-flex ga-2 mt-2">
                    <v-btn
                      @click="get_location(node_to_add)"
                      color="secondary"
                      variant="outlined"
                      size="small"
                    >
                      Get Current Position
                    </v-btn>
                    <v-btn
                      @click="submitRepresentation(); add_representation_toggle = false"
                      color="primary"
                      size="small"
                    >
                      Submit
                    </v-btn>
                    <v-btn
                      @click="add_representation_toggle = false"
                      color="grey"
                      variant="text"
                      size="small"
                    >
                      Cancel
                    </v-btn>
                  </div>
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
import { Location, NodeRepresentationTemplateDefinition } from '../types/workcell_types';
import { collectFormValues, templateToFormFields, type FormField } from '../utils/schemaForm';
import Resource from './ResourceComponents/Resource.vue';
import SchemaForm from './SchemaForm.vue';
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

// Template-aware representation state (for adding)
const selectedNodeTemplates = ref<NodeRepresentationTemplateDefinition[]>([])
const selectedTemplate = ref<NodeRepresentationTemplateDefinition | null>(null)
const schemaFormValues = ref<Record<string, unknown>>({})

// Inline editing state (for existing representations)
const editingRepresentation = ref<string | null>(null)
const editFormValues = ref<Record<string, unknown>>({})
const editJsonValue = ref('')

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
  editingRepresentation.value = null
}

// Look up the representation template for a given node name
function getTemplateForNode(nodeName: string): NodeRepresentationTemplateDefinition | null {
  const nodeInfo = workcell_state.value?.nodes?.[nodeName]?.info
  const templates = (nodeInfo?.location_representation_templates ?? []) as NodeRepresentationTemplateDefinition[]
  // Return the first template (most nodes define one)
  return templates.length > 0 ? templates[0] : null
}

// Build display fields for a representation's current data
function getDisplayFields(nodeName: string, data: Record<string, unknown>): Array<{
  key: string; label: string; displayValue: string; required: boolean; isJson: boolean;
}> {
  const template = getTemplateForNode(nodeName)
  if (!template) return []

  const fields = templateToFormFields(template)
  const result: Array<{
    key: string; label: string; displayValue: string; required: boolean; isJson: boolean;
  }> = []

  // Show fields from the template that have values in the data
  for (const field of fields) {
    const val = data[field.key]
    const isJson = field.type === 'json'
    let displayValue: string
    if (val === undefined || val === null) {
      displayValue = field.required ? '(not set)' : '-'
    } else if (isJson || typeof val === 'object') {
      displayValue = JSON.stringify(val)
    } else {
      displayValue = String(val)
    }
    result.push({
      key: field.key,
      label: field.label,
      displayValue,
      required: field.required,
      isJson,
    })
  }

  // Show any extra data keys not in the template
  for (const key of Object.keys(data)) {
    if (!result.some(f => f.key === key)) {
      const val = data[key]
      result.push({
        key,
        label: key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
        displayValue: typeof val === 'object' ? JSON.stringify(val) : String(val),
        required: false,
        isJson: typeof val === 'object',
      })
    }
  }

  return result
}

// Start editing an existing representation
function startEditRepresentation(nodeName: string, currentData: Record<string, unknown>) {
  editingRepresentation.value = nodeName
  const template = getTemplateForNode(nodeName)
  if (template) {
    // Populate form values from current data
    const fields = templateToFormFields(template)
    const values: Record<string, unknown> = {}
    for (const field of fields) {
      if (field.key in currentData) {
        values[field.key] = field.type === 'json'
          ? JSON.stringify(currentData[field.key], null, 2)
          : currentData[field.key]
      } else if (field.defaultValue !== undefined) {
        values[field.key] = field.type === 'json'
          ? JSON.stringify(field.defaultValue, null, 2)
          : field.defaultValue
      }
    }
    editFormValues.value = values
  } else {
    editJsonValue.value = JSON.stringify(currentData, null, 2)
  }
}

// Cancel editing
function cancelEditRepresentation() {
  editingRepresentation.value = null
  editFormValues.value = {}
  editJsonValue.value = ''
}

// Save edited representation
async function saveEditRepresentation(nodeName: string) {
  const template = getTemplateForNode(nodeName)
  if (template) {
    const fields = templateToFormFields(template)
    const values = collectFormValues(fields, editFormValues.value)
    await submit_location_representation_data(nodeName, values)
  } else {
    try {
      const data = JSON.parse(editJsonValue.value)
      await submit_location_representation_data(nodeName, data)
    } catch {
      alert('Invalid JSON')
      return
    }
  }
  editingRepresentation.value = null
}

// Get current position for edit mode
async function get_location_for_edit(nodeName: string): Promise<void> {
  try {
    const loc_data = await ((await fetch(
      urls.value.workcell_server_url.concat('admin/get_location/').concat(nodeName),
      { method: 'POST' }
    )).json())

    const template = getTemplateForNode(nodeName)
    if (template && loc_data.data && typeof loc_data.data === 'object') {
      const fields = templateToFormFields(template)
      for (const field of fields) {
        if (field.key in loc_data.data) {
          editFormValues.value[field.key] = field.type === 'json'
            ? JSON.stringify(loc_data.data[field.key], null, 2)
            : loc_data.data[field.key]
        }
      }
    } else {
      editJsonValue.value = JSON.stringify(loc_data.data, null, 2)
    }
  } catch (error) {
    console.error('Failed to get location position:', error)
  }
}

// Handle node selection — look up representation templates
function onNodeSelected(nodeName: string) {
  const nodeInfo = workcell_state.value?.nodes?.[nodeName]?.info
  const templates = (nodeInfo?.location_representation_templates ?? []) as NodeRepresentationTemplateDefinition[]
  selectedNodeTemplates.value = templates
  if (templates.length === 1) {
    selectedTemplate.value = templates[0]
  } else {
    selectedTemplate.value = null
  }
  schemaFormValues.value = {}
  add_representation_value.value = ''
}

// Submit representation — uses template form or raw JSON
function submitRepresentation() {
  if (selectedNodeTemplates.value.length > 0 && selectedTemplate.value) {
    // Collect values from the schema form
    const fields = templateToFormFields(selectedTemplate.value)
    const values = collectFormValues(fields, schemaFormValues.value)
    submit_location_representation_data(node_to_add.value, values)
  } else {
    // Fall back to raw JSON submission
    submit_location_representation(node_to_add.value)
  }
}

// Get the current location representation from a node
async function get_location(node_name: string): Promise<void>{
  try {
    const loc_data = await ((await fetch(urls.value.workcell_server_url.concat('admin/get_location/').concat(node_name), {method: 'POST'})).json())
    console.log(loc_data)
    const jsonStr = JSON.stringify(loc_data.data)
    add_representation_value.value = jsonStr

    // If using template form, try to populate form values from the fetched data
    if (selectedNodeTemplates.value.length > 0 && selectedTemplate.value && loc_data.data) {
      const data = typeof loc_data.data === 'object' ? loc_data.data : {}
      // Merge fetched data into form values (stringify json-type values)
      const fields = templateToFormFields(selectedTemplate.value)
      for (const field of fields) {
        if (field.key in data) {
          schemaFormValues.value[field.key] = field.type === 'json'
            ? JSON.stringify(data[field.key], null, 2)
            : data[field.key]
        }
      }
    }
  } catch (error) {
    console.error('Failed to get location position:', error)
  }
}

// Submit new/updated representation
async function submit_location_representation(node_name: string): Promise<void>{
  try {
    const api_url = locations_url.value ?
      locations_url.value.replace('/locations', '/location/').concat(encodeURIComponent(props.location_name)).concat("/set_representation/").concat(node_name) :
      urls.value.workcell_server_url.concat('location/').concat(encodeURIComponent(props.location_name)).concat("/set_representation/").concat(node_name);

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

// Submit representation from structured data (template form)
async function submit_location_representation_data(node_name: string, data: Record<string, unknown>): Promise<void>{
  try {
    const api_url = locations_url.value ?
      locations_url.value.replace('/locations', '/location/').concat(encodeURIComponent(props.location_name)).concat("/set_representation/").concat(node_name) :
      urls.value.workcell_server_url.concat('location/').concat(encodeURIComponent(props.location_name)).concat("/set_representation/").concat(node_name);

    await fetch(api_url, {
      method: "POST",
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(data)
    })

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
      locations_url.value.replace('/locations', '/location/').concat(encodeURIComponent(props.location_name)).concat("/remove_representation/").concat(representationToRemove.value) :
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
      locations_url.value.replace('/locations', '/location/').concat(encodeURIComponent(props.location_name)) :
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
      locations_url.value.replace('/locations', '/location/').concat(encodeURIComponent(props.location_name)).concat("/detach_resource") :
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
      locations_url.value.replace('/locations', '/location/').concat(encodeURIComponent(props.location_name)).concat("/attach_resource") :
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
