<template>
  <div class="schema-form">
    <div v-for="field in formFields" :key="field.key" class="mb-2">
      <!-- Boolean fields -->
      <v-checkbox
        v-if="field.type === 'boolean'"
        v-model="localValues[field.key]"
        :label="field.label + (field.required ? ' *' : '')"
        :hint="field.description"
        :persistent-hint="!!field.description"
        density="compact"
        @update:model-value="emitUpdate"
      />

      <!-- Enum/select fields -->
      <v-select
        v-else-if="field.enumOptions && field.enumOptions.length > 0"
        v-model="localValues[field.key]"
        :items="field.enumOptions"
        item-title="title"
        item-value="value"
        :label="field.label + (field.required ? ' *' : '')"
        :hint="field.description"
        :persistent-hint="!!field.description"
        :rules="field.required ? [requiredRule] : []"
        variant="outlined"
        density="compact"
        @update:model-value="emitUpdate"
      />

      <!-- Number fields -->
      <v-text-field
        v-else-if="field.type === 'number'"
        v-model.number="localValues[field.key]"
        type="number"
        :label="field.label + (field.required ? ' *' : '')"
        :hint="field.description"
        :persistent-hint="!!field.description"
        :rules="field.required ? [requiredRule] : []"
        :min="field.minimum"
        :max="field.maximum"
        variant="outlined"
        density="compact"
        @update:model-value="emitUpdate"
      />

      <!-- JSON fields (arrays, objects) -->
      <v-textarea
        v-else-if="field.type === 'json'"
        v-model="localValues[field.key]"
        :label="field.label + (field.required ? ' *' : '')"
        :hint="field.description || 'Enter valid JSON'"
        :persistent-hint="true"
        :rules="jsonRules(field.required)"
        variant="outlined"
        density="compact"
        rows="3"
        auto-grow
        @update:model-value="emitUpdate"
      />

      <!-- String fields (default) -->
      <v-text-field
        v-else
        v-model="localValues[field.key]"
        :label="field.label + (field.required ? ' *' : '')"
        :hint="field.description"
        :persistent-hint="!!field.description"
        :rules="field.required ? [requiredRule] : []"
        variant="outlined"
        density="compact"
        @update:model-value="emitUpdate"
      />
    </div>

    <div v-if="formFields.length === 0" class="text-grey text-body-2">
      No template fields defined
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue';
import {
  templateToFormFields,
  buildDefaultValues,
  type FormField,
} from '../utils/schemaForm';

interface SchemaFormProps {
  /** The representation template object */
  template: {
    default_values?: Record<string, unknown>;
    schema_def?: Record<string, unknown> | null;
    required_overrides?: string[] | null;
  };
  /** Current form values (v-model) */
  modelValue?: Record<string, unknown>;
}

const props = defineProps<SchemaFormProps>();

const emit = defineEmits<{
  'update:modelValue': [value: Record<string, unknown>];
}>();

const formFields = ref<FormField[]>([]);
const localValues = ref<Record<string, unknown>>({});

// Validation rules
const requiredRule = (v: unknown) => {
  if (v === null || v === undefined || v === '') return 'This field is required';
  return true;
};

const jsonRules = (required: boolean) => {
  const rules: ((v: unknown) => string | true)[] = [];
  if (required) {
    rules.push((v: unknown) => {
      if (v === null || v === undefined || v === '') return 'This field is required';
      return true;
    });
  }
  rules.push((v: unknown) => {
    if (typeof v !== 'string' || v.trim() === '') return true;
    try {
      JSON.parse(v);
      return true;
    } catch {
      return 'Must be valid JSON';
    }
  });
  return rules;
};

function initializeForm() {
  formFields.value = templateToFormFields(props.template);
  const defaults = buildDefaultValues(formFields.value);
  // Merge with any existing model values
  localValues.value = { ...defaults, ...(props.modelValue ?? {}) };
  emitUpdate();
}

function emitUpdate() {
  emit('update:modelValue', { ...localValues.value });
}

// Re-initialize when template changes
watch(() => props.template, initializeForm, { deep: true });

// Initialize on mount
onMounted(initializeForm);
</script>
