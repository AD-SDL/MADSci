<template>
  <v-dialog v-model="dialogModel" max-width="800px" class="pa-3">
    <v-card>
      <v-card-title>
        <h2 class="title">Create Location from Template</h2>
      </v-card-title>

      <v-card-text>
        <!-- Template Selection -->
        <v-select
          v-model="selectedTemplateName"
          :items="templateItems"
          item-title="template_name"
          item-value="template_name"
          label="Location Template"
          variant="outlined"
          density="compact"
          class="mb-3"
          :hint="selectedTemplateDescription"
          :persistent-hint="!!selectedTemplateDescription"
          @update:model-value="onTemplateSelected"
        >
          <template #item="{ props: itemProps, item }">
            <v-list-item v-bind="itemProps">
              <v-list-item-subtitle v-if="item.raw.description">
                {{ item.raw.description }}
              </v-list-item-subtitle>
            </v-list-item>
          </template>
        </v-select>

        <!-- Location Name -->
        <v-text-field
          v-model="locationName"
          label="Location Name *"
          variant="outlined"
          density="compact"
          class="mb-3"
          :rules="[v => !!v || 'Location name is required']"
        />

        <!-- Description -->
        <v-text-field
          v-model="locationDescription"
          label="Description"
          variant="outlined"
          density="compact"
          class="mb-3"
        />

        <!-- Node Bindings -->
        <div v-if="selectedTemplate && Object.keys(selectedTemplate.representation_templates || {}).length > 0">
          <h3 class="mb-2">Node Bindings</h3>
          <p class="text-body-2 text-grey mb-2">
            Assign a concrete node to each role defined by the template.
          </p>
          <v-card variant="outlined" class="pa-3 mb-3">
            <div
              v-for="(reprTemplateName, role) in (selectedTemplate.representation_templates || {})"
              :key="role"
              class="mb-2"
            >
              <v-select
                v-model="nodeBindings[String(role)]"
                :items="Object.keys(workcell_state?.nodes ?? {})"
                :label="role + ' (uses: ' + reprTemplateName + ')'"
                variant="outlined"
                density="compact"
              />
            </div>
          </v-card>
        </div>

        <!-- Representation Overrides (expandable) -->
        <div v-if="selectedTemplate && Object.keys(selectedTemplate.representation_templates || {}).length > 0">
          <v-btn
            v-if="!showOverrides"
            @click="showOverrides = true"
            color="secondary"
            variant="text"
            size="small"
            class="mb-3"
          >
            <v-icon start>mdi-tune</v-icon>
            Customize representation defaults
          </v-btn>

          <v-expand-transition>
            <div v-if="showOverrides">
              <h3 class="mb-2">Representation Overrides</h3>
              <p class="text-body-2 text-grey mb-2">
                Override the default values for each role's representation.
              </p>
              <v-card
                v-for="(reprTemplateName, role) in (selectedTemplate.representation_templates || {})"
                :key="'override-' + role"
                variant="outlined"
                class="pa-3 mb-2"
              >
                <h4 class="mb-1">{{ role }} ({{ reprTemplateName }})</h4>
                <SchemaForm
                  v-if="resolvedReprTemplates[reprTemplateName as string]"
                  :template="resolvedReprTemplates[reprTemplateName as string]"
                  v-model="representationOverrides[String(role)]"
                />
                <div v-else class="text-grey text-body-2">
                  Representation template "{{ reprTemplateName }}" not found
                </div>
              </v-card>
              <v-btn
                @click="showOverrides = false"
                color="grey"
                variant="text"
                size="small"
                class="mb-3"
              >
                Hide overrides
              </v-btn>
            </div>
          </v-expand-transition>
        </div>

        <!-- Validation Errors -->
        <v-alert
          v-if="validationErrors.length > 0"
          type="error"
          variant="outlined"
          density="compact"
          class="mb-3"
        >
          <ul class="pl-4">
            <li v-for="(error, idx) in validationErrors" :key="idx">{{ error }}</li>
          </ul>
        </v-alert>
      </v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn @click="dialogModel = false" color="grey" variant="text">Cancel</v-btn>
        <v-btn @click="submitLocation" color="primary" :loading="submitting">
          Create Location
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue';

import {
  location_templates,
  refreshLocations,
  representation_templates,
  workcell_state,
} from '../store';
import { locationBaseUrl } from '../utils/locationApi';
import { collectFormValues, templateToFormFields, validateFormValues } from '../utils/schemaForm';
import SchemaForm from './SchemaForm.vue';

interface CreateLocationFromTemplateModalProps {
  /** Pre-selected template name (optional) */
  preselectedTemplate?: string;
}

const props = defineProps<CreateLocationFromTemplateModalProps>();

const dialogModel = defineModel<boolean>();

// Form state
const selectedTemplateName = ref<string>('');
const locationName = ref('');
const locationDescription = ref('');
const nodeBindings = ref<Record<string, string>>({});
const representationOverrides = ref<Record<string, Record<string, unknown>>>({});
const showOverrides = ref(false);
const submitting = ref(false);
const validationErrors = ref<string[]>([]);

// Computed
const templateItems = computed(() => location_templates.value || []);

const selectedTemplate = computed(() =>
  templateItems.value.find((t: any) => t.template_name === selectedTemplateName.value) ?? null
);

const selectedTemplateDescription = computed(() =>
  selectedTemplate.value?.description ?? ''
);

/**
 * Resolve representation templates by name from the store.
 * Returns a map of repr template name -> template object.
 */
const resolvedReprTemplates = computed(() => {
  const result: Record<string, any> = {};
  const templates = representation_templates.value || [];
  for (const t of templates) {
    result[t.template_name] = t;
  }
  return result;
});

// Watch for preselected template
watch(() => props.preselectedTemplate, (val) => {
  if (val) {
    selectedTemplateName.value = val;
    onTemplateSelected(val);
  }
}, { immediate: true });

function onTemplateSelected(_name: string) {
  // Reset bindings and overrides when template changes
  nodeBindings.value = {};
  representationOverrides.value = {};
  showOverrides.value = false;
  validationErrors.value = [];
}

function validate(): boolean {
  const errors: string[] = [];
  if (!selectedTemplateName.value) {
    errors.push('Please select a location template');
  }
  if (!locationName.value.trim()) {
    errors.push('Location name is required');
  }
  // Check that all roles have node bindings
  if (selectedTemplate.value) {
    for (const role of Object.keys(selectedTemplate.value.representation_templates || {})) {
      if (!nodeBindings.value[role]) {
        errors.push(`Node binding required for role "${role}"`);
      }
    }
  }
  validationErrors.value = errors;
  return errors.length === 0;
}

async function submitLocation() {
  if (!validate()) return;

  submitting.value = true;
  try {
    const baseUrl = locationBaseUrl();

    // Build representation overrides from form values (always collected, regardless of UI toggle)
    const overrides: Record<string, Record<string, unknown>> = {};
    if (selectedTemplate.value) {
      for (const [role, reprTemplateName] of Object.entries(
        selectedTemplate.value.representation_templates || {}
      )) {
        const reprTemplate = resolvedReprTemplates.value[reprTemplateName as string];
        if (reprTemplate && representationOverrides.value[role]) {
          const fields = templateToFormFields(reprTemplate);
          const fieldErrors = validateFormValues(fields, representationOverrides.value[role]);
          if (fieldErrors.length > 0) {
            validationErrors.value = fieldErrors.map(e => `${role}: ${e}`);
            return;
          }
          overrides[role] = collectFormValues(fields, representationOverrides.value[role]);
        }
      }
    }

    const body: Record<string, unknown> = {
      location_name: locationName.value.trim(),
      template_name: selectedTemplateName.value,
      node_bindings: nodeBindings.value,
    };
    if (locationDescription.value.trim()) {
      body.description = locationDescription.value.trim();
    }
    if (Object.keys(overrides).length > 0) {
      body.representation_overrides = overrides;
    }

    const response = await fetch(baseUrl + 'location/from_template', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.detail || response.statusText);
    }

    await refreshLocations();
    dialogModel.value = false;
    resetForm();
  } catch (error) {
    console.error('Failed to create location from template:', error);
    validationErrors.value = [`Failed to create location: ${error}`];
  } finally {
    submitting.value = false;
  }
}

function resetForm() {
  selectedTemplateName.value = '';
  locationName.value = '';
  locationDescription.value = '';
  nodeBindings.value = {};
  representationOverrides.value = {};
  showOverrides.value = false;
  validationErrors.value = [];
}
</script>
