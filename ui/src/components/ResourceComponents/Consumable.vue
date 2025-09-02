<template>
    <v-card class="pa-2">
    <div v-if="updatedQuantity && updatedCapacity" class="mb-4">
        <ProgressBar 
            :value="progressPercent" 
            :showValue="true" 
            :style="{ height: '40px', width: '100%'}" 
            :pt="{ value: { style: { backgroundColor: barColor }}}"
        />
        <div class="text-right text-body-2 mt-1 grey--text">
            {{ updatedResource.quantity }}/{{ updatedResource.capacity}}
        </div>
    </div>
    <v-card-title class="d-flex justify-space-between align-center">
        <h3 class="text-h6 font-weight-medium">Resource Details</h3>
        <v-btn
            size="small"
            color="primary"
            variant="outlined"
            @click="toggleEdit"
        >
            {{ isEditing ? "Cancel" : "Edit" }}
      </v-btn>
    </v-card-title>
    <v-card-text>
        <div class="mb-4">
            <h5 class="text-subtitle-2 mb-1"> Base Type</h5>
            <div class="text-body-1">{{ resource.base_type}}</div>
        </div>
        <div class="mb-2">
            <h5 class="text-subtitle-2 mb-1">Quantity</h5>
                <div v-if="isEditing">
                    <v-text-field type="number" v-model="editQuantity" class="mr-2" label="Enter Quantity" dense hide-details>
                        <template #append>
                            <!-- <v-btn v-if="editQuantity !== null" color="error" size="small" @click="editConsumable(null, undefined); editQuantity=null">
                                Clear
                            </v-btn> -->

                            <!-- Currently no type check requiring quantity field on consumables, but can only be a positive number and is not optional. 
                            Default is 0. For now removing ability to clear. -->
                        </template>
                    </v-text-field>
                </div>
            <div v-else>
                <span v-if="updatedQuantity" class="text-body-1">{{ updatedResource.quantity }}</span>
                <v-btn v-else size="small" variant="tonal" color="primary" @click="enableField('quantity')">+ Add</v-btn>
            </div>
        </div>
        <div class="mb-2">
            <h5 class="text-subtitle-2 mb-1">Capacity</h5>
                <div v-if="isEditing">
                    <v-text-field v-model="editCapacity" type="number" label="Enter Capacity" dense class="mr-2" hide-details>
                        <template #append>
                            <v-btn v-if="editCapacity !== null" color="error" size="small" @click="editConsumable(undefined, null); editCapacity=null">
                                Clear
                            </v-btn>
                        </template>
                    </v-text-field>
                </div>
                <div v-else>
                    <span v-if="updatedCapacity" class="text-body-1">{{ updatedResource.capacity }}</span>
                    <v-btn v-else size="small" variant="tonal" color="primary" @click="enableField('capacity')">+ Add</v-btn>
                </div>
        </div>
        </v-card-text>
        <v-card-actions v-if="isEditing" class="justify-end">
            <v-btn color="success" @click="editConsumable(editQuantity, editCapacity); isEditing=false">
                Save Changes
            </v-btn>
        </v-card-actions>
        <div class="mb-6"></div>
    </v-card>
    <vue-json-pretty :data="updatedResource" />
</template>

<script setup lang="ts">
import VueJsonPretty from 'vue-json-pretty';
import 'vue-json-pretty/lib/styles.css';
import { VDataTable } from 'vuetify/components';
import { computed, ref } from "vue";
//import ProgressBar from 'primevue/progressbar';
import { resources, urls } from "@/store";

const props = defineProps(['resource'])
const isEditing = ref(false);
const editQuantity = ref<number>(0);
const editCapacity = ref<number | null>(null);

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

function editConsumable(quantity?: number | null, capacity?: number | null) {
    const payload: any = { ...updatedResource.value};
    payload.quantity = typeof quantity !== "undefined" ? quantity : updatedResource.value.quantity;
    payload.capacity = typeof capacity !== "undefined" ? capacity : updatedResource.value.capacity;
    fetch(urls.value.resource_server_url.concat("resource/update"), {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
    }).then(async response => {
        if (response.ok) {
            const updated = await response.json()
            const index = resources.value.findIndex((r: any) => r.resource_id === updated.resource_id);
            if (index !== -1) resources.value[index] = updated;
        }
    });
}
function toggleEdit() {
    if (!isEditing.value) {
        editQuantity.value = updatedQuantity.value ? updatedResource.value.quantity : null;
        editCapacity.value = updatedCapacity.value ? updatedResource.value.capacity : null;
    }
    isEditing.value = !isEditing.value;
}
function enableField(field: "quantity" | "capacity") {
    if (!isEditing.value) toggleEdit();
    if (field === "quantity" && editQuantity.value === null) {
        editQuantity.value = 0;
    }
    if (field === "capacity" && editCapacity.value === null) {
        editCapacity.value = 0;
    }
}
</script>
