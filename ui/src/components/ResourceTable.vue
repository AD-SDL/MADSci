<template>
    <ResourceModal :modal_title="modal_title" :modal_text="modal_text" v-model="modal" />
    <!-- eslint-disable vue/no-parsing-error-->
    <v-data-table :headers="arg_headers" hover
      :items="prune_tree(resources)"
      item-value="resource_id"
      v-model:expanded="expanded"
      no-data-text="No Resources" density="compact" :sort-by="sortBy" :hide-default-footer="resources.length <= 10"  :hide-default-header="hide_header" show-expand>
      <template v-slot:item="{ item, internalItem, isExpanded, toggleExpand}: { item: any, internalItem: any, isExpanded: any, toggleExpand: any}">
        <tr @click="set_modal(item.resource_name, item)">
          <td ><v-checkbox-btn
          :v-model="delete_list"
          @update:modelValue="function(val: any) {modify_to_delete(val, item) }"
          @click.stop
          class="pe-2"
        ></v-checkbox-btn></td>
          <td>{{ item.resource_name }}</td>
          <td>{{ item.base_type }}</td>
          <td>{{ item.created_at }}</td>
          <td>{{ item.resource_id }}</td>
          <td v-if="item.children && get_all(item.children).length > 0">
            <v-btn :icon="isExpanded(internalItem) ? 'mdi-chevron-up' : 'mdi-chevron-down'"
                    variant="plain"
                    @click.stop="toggleExpand(internalItem)"/>
          </td>
        </tr>
      </template>
      <template v-slot:expanded-row="{ columns, item}: {columns: any, item: any}">
          <tr>
            <td :colspan="columns.length"><ResourceTable :resources=get_all(item.children) :parent_id=item.resource_id :hide_header="true" /></td>
          </tr>
        </template>
    </v-data-table>



</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import { VDataTable } from 'vuetify/components';
import { to_delete_list } from "@/store";
const props = defineProps(['resources', 'parent_id',  'hide_header'])
const modal = ref(false)
const delete_list = ref([])
const modal_text = ref()
const modal_title = ref()
const pruned_resources = ref()
const expanded = ref<string[]>([]);
const sortBy: VDataTable['sortBy'] = [{ key: 'created_at', order: 'desc' }];
const arg_headers = [
  { title: 'Select', key: 'select', sortable: false },
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
watch(() => props.resources, (newResources: any) => {
  expanded.value = expanded.value.filter((resourceId: any) => {
    const resource = newResources.find((r: any) => r.resource_id === resourceId);
    return resource && get_all(resource.children).length > 0;
  });
},
{deep: true}
);
function prune_tree(input_resources: any): any[] {
  var return_resources: any = []
  input_resources.forEach((element: any) => { if((element.parent_id == null) || element.parent_id == props.parent_id) { element.selected = false; return_resources.push(element)}

  });
  return return_resources

}

//"(val: any) => modify_to_delete(val, item.resource_id)"

function modify_to_delete(val: boolean, item: any) {
  console.log("Modifying to_delete_list: ", item.resource_id)
  if (val) {
    to_delete_list.value.push(item.resource_id)
  } else {
    const index = to_delete_list.value.indexOf(item.resource_id);
    if (index > -1) {
      to_delete_list.value.splice(index, 1);
    }
  }
}


function get_all(input_resources: any) {
  if (Array.isArray(input_resources)) {
    return input_resources
  } else {
    return Object.values(input_resources)
  }
}

</script>
