<template>
  <WorkflowStepsTab :steps="steps" :wf="wf" />
  <h3>Details</h3>
  <vue-json-pretty :data="wf" :deep="1"></vue-json-pretty>
</template>

<script setup lang="ts">
import VueJsonPretty from 'vue-json-pretty'
import 'vue-json-pretty/lib/styles.css'

defineProps(['steps', 'wf'])
</script>
