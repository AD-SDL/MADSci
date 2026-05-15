<template>
  <v-data-table
    :headers="headers"
    :items="representation_templates"
    hover
    density="compact"
    no-data-text="No Representation Templates"
    :hide-default-footer="representation_templates.length <= 10"
  >
    <template v-slot:item="{ item }: { item: any }">
      <tr @click="openDetail(item)" style="cursor: pointer;">
        <td>{{ item.template_name }}</td>
        <td>{{ item.version }}</td>
        <td>{{ truncate(JSON.stringify(item.default_values)) }}</td>
        <td>{{ (item.required_overrides || []).join(', ') }}</td>
        <td>
          <v-chip v-for="tag in (item.tags || [])" :key="tag" size="small" class="mr-1">
            {{ tag }}
          </v-chip>
        </td>
        <td>{{ item.created_by || '-' }}</td>
      </tr>
    </template>
  </v-data-table>

  <v-dialog v-model="detailDialog" max-width="800">
    <v-card>
      <v-card-title>{{ selectedTemplate?.template_name }}</v-card-title>
      <v-card-text>
        <vue-json-pretty :data="selectedTemplate" :deep="3" />
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn text="Close" @click="detailDialog = false" />
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import VueJsonPretty from 'vue-json-pretty';
import 'vue-json-pretty/lib/styles.css';
import { representation_templates } from '@/store';

const headers = [
  { title: 'Name', key: 'template_name' },
  { title: 'Version', key: 'version' },
  { title: 'Default Values', key: 'default_values', sortable: false },
  { title: 'Required Overrides', key: 'required_overrides', sortable: false },
  { title: 'Tags', key: 'tags', sortable: false },
  { title: 'Created By', key: 'created_by' },
];

const detailDialog = ref(false);
const selectedTemplate = ref<any>(null);

function openDetail(item: any) {
  selectedTemplate.value = item;
  detailDialog.value = true;
}

function truncate(str: string, maxLen = 60) {
  if (str.length <= maxLen) return str;
  return str.substring(0, maxLen) + '...';
}
</script>
