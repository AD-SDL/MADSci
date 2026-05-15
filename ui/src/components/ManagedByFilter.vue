<template>
  <div class="d-flex ga-2 mb-3">
    <v-chip
      :color="modelValue === 'all' ? 'primary' : undefined"
      :variant="modelValue === 'all' ? 'flat' : 'outlined'"
      @click="$emit('update:modelValue', 'all')"
    >
      All
    </v-chip>
    <v-chip
      :color="modelValue === 'node' ? 'info' : undefined"
      :variant="modelValue === 'node' ? 'flat' : 'outlined'"
      @click="$emit('update:modelValue', 'node')"
      prepend-icon="mdi-robot-industrial"
    >
      Node-Managed
    </v-chip>
    <v-chip
      :color="modelValue === 'lab' ? 'success' : undefined"
      :variant="modelValue === 'lab' ? 'flat' : 'outlined'"
      @click="$emit('update:modelValue', 'lab')"
      prepend-icon="mdi-flask"
    >
      Lab-Managed
    </v-chip>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  modelValue: 'all' | 'node' | 'lab';
}>();

defineEmits<{
  (e: 'update:modelValue', value: 'all' | 'node' | 'lab'): void;
}>();
</script>
