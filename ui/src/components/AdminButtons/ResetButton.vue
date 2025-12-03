<template>
    <div>
        <v-tooltip location="bottom">
            <template v-slot:activator="{ props }">
                <div v-bind="props">
                    <v-btn
                        @click="sendResetCommand"
                        color="light-green-darken-2"
                        dark
                        elevation="5"
                        :disabled="!canReset">
                        <v-icon>mdi-restart</v-icon>
                    </v-btn>
                </div>
            </template>
            <span>
                {{ canReset ? hoverText : hoverText + " (unavailable)" }}
            </span>
        </v-tooltip>
    </div>

</template>

<script lang="ts" setup>
    import { urls } from "@/store";
import { ref, watchEffect } from 'vue';

    const props = defineProps<{
        node?: string;
        node_status?: any;
        wf_id?: string;
        wf_status?: any;
    }>();

    const reset_url = ref('')
    const canReset = ref(false);
    const hoverText = ref('')

    // Format reset url
    watchEffect(() => {
        if (props.node) {
            reset_url.value = urls.value.workcell_server_url.concat('admin/reset/'.concat(props.node))
            hoverText.value = "Reset Node"
        }
        else if (props.wf_id) {
            reset_url.value = urls.value.workcell_server_url.concat('workflow/'.concat(props.wf_id).concat('/retry'))
            hoverText.value = "Retry Workflow"
        }
        else {
            reset_url.value = urls.value.workcell_server_url.concat('admin/reset')
            hoverText.value = "Reset Workcell"
        }
    })

    watchEffect(() => {
        if (props.node) {
            // Determine if the node is able to be reset (if actively running something)
            if (props.node_status == 'BUSY') {
                canReset.value = false
                //user should pause or stop running action before resetting
            }
            else {
                canReset.value = true
            }
        }
        else if (props.wf_id) {
            if (props.wf_status["terminal"]) {
                canReset.value = true
            }
            else {
                canReset.value = false
            }
        }
        else {
            // TODO: Allow reset only if no workflows/experiments are actively running
            canReset.value = true
        }
    })

    // Function to send reset command
    const sendResetCommand = async () => {
        try {
            const response = await fetch(reset_url.value, {
                method: 'POST',
            });
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            console.log('Reset successful');

        } catch (error) {
            console.error('Error in reset:', error);
        }
    };

</script>
