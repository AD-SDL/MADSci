<template>
<v-card>
<v-card-title>
<h2>
    Create Workflow
</h2>
</v-card-title>
<v-text-field @vue:updated="set_workflow_title()" height="20px" v-model="workflow_title"
                          dense>
</v-text-field>
<h3>Workflow Title: {{workflow["title"]}} </h3>
<div v-if="workflow['steps'].length > 0">
<Workflow :wf=workflow :steps="workflow['steps']" />
</div>
<v-btn>Add Step</v-btn>
<v-select :items="Object.keys(workcell_state.nodes)" v-model="target_node"></v-select>
<v-select v-model="target_action" v-if="target_node != null" :items="Object.keys(workcell_state.nodes[target_node].info['actions'])"></v-select>
<v-btn @click="">Select</v-btn>
<!-- <Step v-model="new_step" v-if="target_action != null"/> -->


</v-card>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { workcell_state } from '@/store';
const workflow = ref()
const workflow_title = ref()
const target_node = ref(null)
const target_action = ref(null)
const new_step = ref()
workflow.value = {"steps": [], "title": "New Workflow"}

function set_workflow_title() {

    workflow.value.title = workflow_title.value
  }





</script>
