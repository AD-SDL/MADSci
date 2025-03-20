<template>
    <div>
        <v-tooltip location="bottom">
            <template v-slot:activator="{ props }">
                <div v-bind="props">
                    <v-btn
                        @click="sendShutdownCommand"
                        color="light-blue darken-3"
                        dark
                        elevation="5"
                        :disabled="isShutdown">
                        <v-icon>mdi-power</v-icon>
                    </v-btn>
                </div>
            </template>
            <span>
                {{ isShutdown ? hoverText + " (unavailable)" : hoverText}}
            </span>
        </v-tooltip>
    </div>

</template>

<script lang="ts" setup>
    import { main_url } from "@/store";
import { ref, watchEffect } from 'vue';

    const props = defineProps<{
        module?: string;
        module_status?: string;
    }>();

    const shutdown_url = ref('')
    const isShutdown = ref(true);
    const hoverText = ref('')

    // Format shutdown url
    watchEffect(() => {
        if (props.module) {
            shutdown_url.value = main_url.value.concat('/admin/shutdown/'.concat(props.module))
            hoverText.value = "Shutdown Module"
        }
        else {
            shutdown_url.value = main_url.value.concat('/admin/shutdown')
            hoverText.value = "Shutdown WEI Server and Dashboard"
        }
    })

    watchEffect(() => {
        // Determine if the module is already shutdown
        if (props.module_status == 'UNKNOWN') {
            isShutdown.value = true
        } else {
            isShutdown.value = false
        }
    })

    // Function to send shutdown command
    const sendShutdownCommand = async () => {
        try {
            const response = await fetch(shutdown_url.value, {
                method: 'POST',
            });
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            console.log('Shutdown successful');

        } catch (error) {
            console.error('Error in shutdown:', error);
        }
    };

</script>
