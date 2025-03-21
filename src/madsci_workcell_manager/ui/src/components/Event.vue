<template>
    <vue-json-pretty :data="events[props.event_id]" />
</template>

<script setup lang="ts">

import VueJsonPretty from 'vue-json-pretty';
import 'vue-json-pretty/lib/styles.css';
/// <reference path="../store.d.ts" />
import { events } from "@/store";
const props = defineProps(['event_id'])

</script>
