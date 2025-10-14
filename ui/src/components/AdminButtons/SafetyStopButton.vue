<template>
    <div>
        <v-tooltip location="bottom">
            <template v-slot:activator="{ props }">
                <div v-bind="props">
                    <v-btn
                        @click="sendSafetyStopCommand"
                        color="red-accent-4"
                        dark
                        elevation="5">
                        SAFETY STOP
                    </v-btn>
                </div>
            </template>
            <span>
                {{ hoverText }}
            </span>
        </v-tooltip>
    </div>

</template>

<script lang="ts" setup>
    import { urls } from "@/store";
import { ref, watchEffect } from 'vue';

    const props = defineProps<{
        node?: string;
    }>();

    const safetyStop_url = ref('')
    const hoverText = ref('')

    // Format safety stop url
    watchEffect(() => {
        if (props.node) {
            safetyStop_url.value = urls.value.workcell_server_url.concat('admin/safety_stop/'.concat(props.node))
            hoverText.value = "Stop Node"
        }
        else {
            safetyStop_url.value = urls.value.workcell_server_url.concat('admin/safety_stop')
            hoverText.value = "Stop Workcell"
        }
    })

    // Function to send safety stop command
    const sendSafetyStopCommand = async () => {
        try {
            const response = await fetch(safetyStop_url.value, {
                method: 'POST',
            });
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            console.log('Node Stopped');

        } catch (error) {
            console.error('Error stopping node:', error);
        }
    };

</script>
