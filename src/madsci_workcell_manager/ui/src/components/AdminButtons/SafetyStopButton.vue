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
    import { main_url } from "@/store";
import { ref, watchEffect } from 'vue';

    const props = defineProps<{
        module?: string;
    }>();

    const safetyStop_url = ref('')
    const hoverText = ref('')

    // Format safety stop url
    watchEffect(() => {
        if (props.module) {
            safetyStop_url.value = main_url.value.concat('/admin/safety_stop/'.concat(props.module))
            hoverText.value = "Stop Module"
        }
        else {
            safetyStop_url.value = main_url.value.concat('/admin/safety_stop')
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
            console.log('Module Stopped');

        } catch (error) {
            console.error('Error stopping module:', error);
        }
    };

</script>
