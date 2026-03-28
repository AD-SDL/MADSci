<template>
  <v-data-table
    :headers="headers"
    :items="location_templates"
    hover
    density="compact"
    no-data-text="No Location Templates"
    :hide-default-footer="location_templates.length <= 10"
  >
    <template v-slot:item="{ item }: { item: any }">
      <tr @click="openDetail(item)" style="cursor: pointer;">
        <td>{{ item.template_name }}</td>
        <td>{{ item.version }}</td>
        <td>
          <v-chip
            v-for="(tmpl, role) in (item.representation_templates || {})"
            :key="role"
            size="small"
            class="mr-1 mb-1"
          >
            {{ role }}: {{ tmpl }}
          </v-chip>
        </td>
        <td>{{ item.resource_template_name || '-' }}</td>
        <td>
          <v-icon :color="item.default_allow_transfers ? 'green' : 'red'">
            {{ item.default_allow_transfers ? 'mdi-check-circle' : 'mdi-close-circle' }}
          </v-icon>
        </td>
        <td>
          <v-chip v-for="tag in (item.tags || [])" :key="tag" size="small" class="mr-1">
            {{ tag }}
          </v-chip>
        </td>
        <td>
          <v-btn
            size="small"
            color="primary"
            variant="outlined"
            @click.stop="createFromTemplate(item.template_name)"
          >
            <v-icon start>mdi-plus</v-icon>
            Create Location
          </v-btn>
        </td>
      </tr>
    </template>
  </v-data-table>

  <CreateLocationFromTemplateModal
    v-model="createDialog"
    :preselected-template="preselectedTemplateName"
  />

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
import { location_templates } from '@/store';
import CreateLocationFromTemplateModal from './CreateLocationFromTemplateModal.vue';

const createDialog = ref(false);
const preselectedTemplateName = ref('');

function createFromTemplate(templateName: string) {
  preselectedTemplateName.value = templateName;
  createDialog.value = true;
}

const headers = [
  { title: 'Name', key: 'template_name' },
  { title: 'Version', key: 'version' },
  { title: 'Roles / Repr Templates', key: 'representation_templates', sortable: false },
  { title: 'Resource Template', key: 'resource_template_name' },
  { title: 'Allow Transfers', key: 'default_allow_transfers' },
  { title: 'Tags', key: 'tags', sortable: false },
  { title: 'Actions', key: 'actions', sortable: false },
];

const detailDialog = ref(false);
const selectedTemplate = ref<any>(null);

function openDetail(item: any) {
  selectedTemplate.value = item;
  detailDialog.value = true;
}
</script>
