<template>
    <ResourceModal :modal_title="modal_title" :modal_text="modal_text" v-model="modal" />
    <!-- eslint-disable vue/no-parsing-error-->
    <v-data-table :headers="arg_headers" hover
      :items="prune_tree(resources)"
      item-value="resource_id"
      no-data-text="No Resources" density="compact" :sort-by="sortBy" :hide-default-footer="resources.length <= 10"  :hide-default-header="hide_header" show-expand>
      <template v-slot:item="{ item, internalItem, isExpanded, toggleExpand}: { item: any, internalItem: any, isExpanded: any, toggleExpand: any}">
        <tr @click="set_modal(item.resource_name, item)">
          <td>{{ item.resource_name }}</td>
          <td>{{ item.base_type }}</td>
          <td>{{ item.created_at }}</td>
          <td>{{ item.resource_id }}</td>
          <td v-if="item.children && item.children.length > 0"><v-btn
        :icon="isExpanded(internalItem) ? 'mdi-chevron-up' : 'mdi-chevron-down'"
        variant="plain"
        @click.stop="toggleExpand(internalItem)"
      /></td>
        </tr>
      </template>
      <template v-slot:expanded-row="{ columns, item}: {columns: any, item: any}">
          <tr>
            <td :colspan="columns.length"><ResourceTable :resources=item.children :parent_id=item.resource_id :hide_header="true" /></td>
          </tr>
        </template>
    </v-data-table>



</template>

<script setup lang="ts">
import { urls } from "@/store";
import VDrilldownTable from  '@wdns/vuetify-drilldown-table';
import { ref } from 'vue';
import { VDataTable } from 'vuetify/components';
const props = defineProps(['resources', 'parent_id',  'hide_header'])
const modal = ref(false)
const modal_text = ref()
const modal_title = ref()
const sortBy: VDataTable['sortBy'] = [{ key: 'created_at', order: 'desc' }];
const arg_headers = [
  { title: 'Name', key: 'resource_name' },
  { title: 'Base Type', key: 'base_type' },
  { title: 'Created At', key: 'created_at' },
  { title: 'ID', key: 'resource_id' },
]
const set_modal = (title: string, value: Object) => {
  modal_title.value = title
  modal_text.value = value
  modal.value = true
}

function prune_tree(input_resources: any): any[] {
  var return_resources: any = []
  input_resources.forEach((element: any) => { if((element.parent_id == null) || element.parent_id == props.parent_id) { return_resources.push(element)}

  });
  return return_resources

}




</script>
