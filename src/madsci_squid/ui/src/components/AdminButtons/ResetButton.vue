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
    import { main_url } from "@/store";
import { ref, watchEffect } from 'vue';

    const props = defineProps<{
        module?: string;
        module_status?: string;
    }>();

    const reset_url = ref('')
    const canReset = ref(false);
    const hoverText = ref('')

    // Format reset url
    watchEffect(() => {
        if (props.module) {
            reset_url.value = main_url.value.concat('/admin/reset/'.concat(props.module))
            hoverText.value = "Reset Module"
        }
        else {
            reset_url.value = main_url.value.concat('/admin/reset')
            hoverText.value = "Reset Workcell"
        }
    })

    watchEffect(() => {
        if (props.module) {
            // Determine if the module is able to be reset (if actively running something)
            if (props.module_status == 'BUSY') {
                canReset.value = false
                //user should pause or stop running action before resetting
            }
            else {
                canReset.value = true
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
