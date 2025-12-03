<template>
    <div>
        <v-tooltip location="bottom">
            <template v-slot:activator="{ props }">
                <div v-bind="props">
                    <v-btn
                        @click="sendCancelCommand"
                        color="deep-orange darken-1"
                        dark
                        elevation="5"
                        :disabled="!canCancel">
                        <v-icon>mdi-cancel</v-icon>
                    </v-btn>
                </div>
            </template>
            <span>
                {{ canCancel ? hoverText : hoverText + " (unavailable)" }}
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
    wf_id?: string;
    wf_status?: any;
}>();

const cancel_url = ref('')
const canCancel = ref(false);
const hoverText = ref('')

// Format cancel url
watchEffect(() => {
    if (props.node) {
        cancel_url.value = urls.value.workcell_server_url.concat('admin/cancel/'.concat(props.node))
        hoverText.value = "Cancel Node Action"
    }
    else if (props.wf_id) {
        cancel_url.value = urls.value.workcell_server_url.concat('workflow/'.concat(props.wf_id).concat('/cancel/'))
        hoverText.value = "Cancel Workflow"
    }
    else {
        cancel_url.value = urls.value.workcell_server_url.concat('admin/cancel')
        hoverText.value = "Cancel All Workflows"
    }
})

watchEffect(() => {
    // Determine if the node is cancelable (if actively running something)
    if (props.node) {
        console.log("Node Status (from props=get_status):", props.node_status)
        if (props.node_status == 'busy' || props.node_status == 'running' || props.node_status == 'paused') {
            canCancel.value = true
        }
        else {
            canCancel.value = false
        }
    }
    else if (props.wf_id) {
        if (props.wf_status["active"]) {
            canCancel.value = true
        }
        else {
            canCancel.value = false
        }
    }
    else {
        // TODO: Allow cancel if there's an actively running workflow
        canCancel.value = true
    }
})

// Function to send cancel command
const sendCancelCommand = async () => {
    try {
        const response = await fetch(cancel_url.value, {
            method: 'POST',
        });
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        console.log('Cancel successful');

    } catch (error) {
        console.error('Error in cancel:', error);
    }
};
</script>
