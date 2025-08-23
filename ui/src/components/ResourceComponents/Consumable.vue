<template>
    <div v-if="updatedQuantity && updatedCapacity" class="progress-wrapper">
        <ProgressBar 
            :value="progressPercent" 
            :showValue="true" 
            :style="{ height: '50px', width: '100%'}" 
            :pt="{ value: { style: { backgroundColor: barColor }}}"
        />
        <div class="progress-label">
            {{ updatedResource.quantity }}/{{ updatedResource.capacity}}
        </div>
    </div>
    <h5>Base Type</h5>
        {{ resource.base_type }}
    <div v-if="updatedQuantity">
        <h5>Quantity</h5>
        {{ updatedResource.quantity }}
    </div>
    <div v-if="updatedCapacity">
        <h5>Capacity</h5>
        {{ updatedResource.capacity }}
    </div>
</template>

<script setup lang="ts">
import VueJsonPretty from 'vue-json-pretty';
import 'vue-json-pretty/lib/styles.css';
import { VDataTable } from 'vuetify/components';
import { computed } from "vue";
//import ProgressBar from 'primevue/progressbar';
import { resources, urls } from "@/store";

const props = defineProps(['resource'])

const updatedResource = computed(() =>
    resources.value.find((r: any) => r.resource_id === props.resource.resource_id) || props.resource
);
const updatedQuantity = computed(() => 
    updatedResource.value?.quantity !== undefined 
    && updatedResource.value?.quantity !== null
);
const updatedCapacity = computed(() => 
    updatedResource.value?.capacity !== undefined 
    && updatedResource.value?.capacity !== null
);
const progress = computed(() =>
    updatedQuantity.value && updatedCapacity.value && updatedResource.value.capacity !== 0
    ? updatedResource.value.quantity / updatedResource.value.capacity : null
);
const progressPercent = computed(() =>
    progress.value != null ? Math.round(progress.value * 100) : 0
);
function interpolateColor(color1: string, color2: string, factor: number) {
  const c1 = color1.match(/\w\w/g)!.map((x) => parseInt(x, 16));
  const c2 = color2.match(/\w\w/g)!.map((x) => parseInt(x, 16));
  const result = c1.map((v, i) => Math.round(v + factor * (c2[i] - v)));
  return `#${result.map((x) => x.toString(16).padStart(2, "0")).join("")}`;
}
const barColor = computed(() => {
  const p = progress.value ?? 0;
  if (p <= 0.5) { return interpolateColor("dc3545", "ffc107", p / 0.5);
    } else { return interpolateColor("ffc107", "28a745", (p - 0.5) / 0.5);
  }});
</script>

<style>
.progress-wrapper {
    margin-bottom: 1rem;
}
.progress-label {
    margin-top: 0.25rem;
    font-size: 0.9rem;
    text-align: right;
    color: #555;
}
</style>