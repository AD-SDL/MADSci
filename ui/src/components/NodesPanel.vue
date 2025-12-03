<template>
  <div>
    <NodeModal :modal_title="modal_title" :modal_text="modal_text" :main_url="main_url" :wc_state="wc_state" :locations='locations'
      v-model="modal" />
    <v-card class="pa-1 ma-1" title="Nodes">
      <v-card-text>
        <v-container v-if="sortedNodes" fluid class="pa-1">
          <v-row no-gutter wrap justify-content class="pa-1">
            <v-col class="pa-1" cols=12 sm=6 md=4 lg=3 xl=2 v-for="(value, node_name) in sortedNodes" :key="node_name">
              <v-card class="pa-1 node_indicator" @click="set_modal(String(node_name), value.info)"
                :class="'node_status_' + get_status(value.status)">
                <v-card-text>
                  <h3 wrap>{{ node_name }}</h3>

                  <p wrap class="text-caption">
                    <!-- status: {{ Object.entries(value.status).filter(([_, value]) => value === true).map(([key, _]) => key).join(' ') }} -->
                    status: {{ get_status(value.status) }}
                  </p>
                </v-card-text>
              </v-card>
            </v-col>
          </v-row>
        </v-container>
        <p v-else> No Nodes In Workcell</p>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { get_status } from '../store';
const props = defineProps(['nodes', 'wc_state', 'main_url', 'locations'])
const modal_title = ref()
const modal = ref(false)
const modal_text = ref()
const set_modal = (title: string, value: Object) => {
  modal_title.value = title
  modal_text.value = value
  modal.value = true
}

const sortedNodes = computed(() => {
  if (!props.nodes) return null;
  return Object.entries(props.nodes)
    .sort(([a], [b]) => a.localeCompare(b))
    .reduce((acc, [key, value]) => {
      acc[key] = value;
      return acc;
    }, {} as typeof props.nodes);
})


</script>
