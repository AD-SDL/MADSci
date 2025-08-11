<template>
    <div>
      <v-tooltip location="bottom">
        <template v-slot:activator="{ props }">
            <div v-bind="props">
            <v-btn
                @click="toggleLockUnlock"
                :color="isLocked ? 'grey-darken-3' : 'grey-lighten-1'"
                dark
                elevation="5" >
                <v-icon>
                    {{ isLocked ? 'mdi-lock-open' : 'mdi-lock' }}
                </v-icon>
            </v-btn>
            </div>
        </template>
         <span>
            {{ isLocked ? "Unlock " + hoverText : "Lock " + hoverText}}
        </span>
      </v-tooltip>
    </div>
  </template>

<script lang="ts" setup>
import { urls, workcell_state } from "@/store";
import { ref, watchEffect } from 'vue';

const props = defineProps<{
    module?: string;
    module_status?: any;
}>();
const lock_url = ref('')
const unlock_url = ref('')
const isLocked = ref(false);
const hoverText = ref('')

// Format pause and resume urls
watchEffect(() => {
    if (props.module) {
        lock_url.value = urls.value.workcell_server_url.concat('admin/lock/'.concat(props.module))
        unlock_url.value = urls.value.workcell_server_url.concat('admin/unlock/'.concat(props.module))
        hoverText.value = "Module"
    }
    else {
        lock_url.value = urls.value.workcell_server_url.concat('admin/lock')
        unlock_url.value = urls.value.workcell_server_url.concat('admin/unlock')
        hoverText.value = "Workcell"
    }
})

watchEffect(() => {
    if (props.module) {
        // Determine if the module is already locked
        if (props.module_status["LOCKED"] == true) {
            isLocked.value = true
        } else {
            if (workcell_state.value) {
                isLocked.value = workcell_state.value.locked
            } else {
                isLocked.value = false
            }
        }
    } else {
        if (workcell_state.value) {
            isLocked.value = workcell_state.value.locked
        } else {
            isLocked.value = false
        }
    }
})

// Function to toggle lock/unlock
const toggleLockUnlock = async () => {
    if (isLocked.value) {
        await sendUnlockCommand();
    } else {
        await sendLockCommand();
    }
    isLocked.value = !isLocked.value;
};

// Function to send lock command
const sendLockCommand = async () => {
    try {
        const response = await fetch(lock_url.value, {
            method: 'POST',
        });
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        console.log('Locked');

    } catch (error) {
        console.error('Error locking:', error);
    }
};

// Function to send unlock command
const sendUnlockCommand = async () => {
    try {
        const response = await fetch(unlock_url.value, {
            method: 'POST',
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        console.log('Unlocked');

    } catch (error) {
        console.error('Error unlocking:', error);
    }
};
</script>
