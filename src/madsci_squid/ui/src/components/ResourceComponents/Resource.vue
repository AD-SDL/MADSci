<template>
    <div v-for="(value, key) in resource">
    <div v-if="value != null">
      <h5>{{ key }}:</h5>
     {{ value }}
    </div>
    </div>

    <vue-json-pretty :data="resource" />
</template>

<script setup lang="ts">

import VueJsonPretty from 'vue-json-pretty';
import 'vue-json-pretty/lib/styles.css';
const props = defineProps(['resource'])
import { ref } from 'vue';



</script>
