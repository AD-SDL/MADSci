<template>
    <div>
        <v-tooltip location="bottom">
            <template v-slot:activator="{ props }">
                <div v-bind="props">
                    <v-btn
                        @click="sendHomeCommand()"
                        color="purple darken-1"
                        dark
                        elevation="5"
                        :disabled="!canHome">
                        <v-icon>mdi-home-outline</v-icon>
                    </v-btn>
                </div>
            </template>
            <span>
                {{ canHome ? hoverText : hoverText + " (unavailable)" }}
            </span>
        </v-tooltip>
    </div>

</template>

<script setup lang="ts">
import { urls } from "@/store";
import { ref, watchEffect } from 'vue';

const props = defineProps<{
    node?: string;
    node_status?: any;
}>();

const home_url = ref('')
const canHome = ref(false);
const hoverText = ref('')
const emit = defineEmits(['Home'])

// Format home url
watchEffect(() => {
    if (props.node) {
        home_url.value = urls.value.workcell_server_url.concat('admin/home/'.concat(props.node).concat('/action'))
        hoverText.value = "Home Node"
    }
    else {
        home_url.value = urls.value.workcell_server_url.concat('admin/home/action')
        hoverText.value = "Home All Nodes"
    }
})

watchEffect(() => {
    // Determine if the node is homeable (if ready, not running anything)
    if (props.node) {
        if (props.node_status == 'busy' || props.node_status == 'running' || props.node_status == 'paused') { 
            canHome.value = false
        }
        else {
            canHome.value = true
        }
    }
    else {
        // ***
        canHome.value = true
    }
})

// Function to send home command
const sendHomeCommand = async () => {
    try {
        const response = await fetch(home_url.value, {
            method: 'POST',
        });
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        console.log('Home successful');

    } catch (error) {
        console.error('Error in home:', error);
    }
};
</script>
