<template>
    <div>
      <v-tooltip location="bottom">
        <template v-slot:activator="{ props }">
            <div v-bind="props">
            <v-btn
                @click="togglePauseResume"
                :color="isPaused ? 'green-darken-3' : 'orange-darken-1'"
                dark
                elevation="5"
                :disabled="!allowButton" >
                <v-icon>
                    {{ isPaused ? 'mdi-play' : 'mdi-pause' }}
                </v-icon>
            </v-btn>
            </div>
        </template>
         <span>
            {{ allowButton ? (isPaused ? 'Resume ' + hoverText : 'Pause ' + hoverText)
                       : (isPaused ? 'Resume ' + hoverText + ' (unavailable)' : 'Pause ' + hoverText + ' (unavailable)') }}
        </span>
      </v-tooltip>
    </div>
  </template>

<script lang="ts" setup>
import {
  ref,
  watchEffect,
} from 'vue';

import {
  urls,
  workcell_state,
} from '@/store';

const props = defineProps<{
    node?: string;
    node_status?: any;
}>();

const pause_url = ref('')
const resume_url = ref('')
const isPaused = ref(false);
const allowButton = ref(false)
const hoverText = ref('')

// Format pause and resume urls
watchEffect(() => {
    if (props.node) {
        pause_url.value = urls.value.workcell_server_url.concat('admin/pause/'.concat(props.node))
        resume_url.value = urls.value.workcell_server_url.concat('admin/resume/'.concat(props.node))
        hoverText.value = "Node"
    }
    else {
        pause_url.value = urls.value.workcell_server_url.concat('admin/pause')
        resume_url.value = urls.value.workcell_server_url.concat('admin/resume')
        hoverText.value = "Workcell"
    }
})

watchEffect(() => {
    if (props.node) {
        // Determine if pressing pause/resume button should be allowed
        if (props.node_status["BUSY"] == true || props.node_status["PAUSED"] == true) {
            allowButton.value = true
        } else {
            allowButton.value = false
        }

        // Determine if the node is already paused
        if (props.node_status["PAUSED"] == true) {
            isPaused.value = true
        } else {
            isPaused.value = false
        }
    }
    else {
        if (workcell_state.value) {
            isPaused.value = !!workcell_state.value.status?.paused
        } else {
            isPaused.value = false
        }
        allowButton.value = true
    }
})

// Function to toggle pause/resume
const togglePauseResume = async () => {
    if (isPaused.value) {
        await sendResumeCommand();
    } else {
        await sendPauseCommand();
    }
    isPaused.value = !isPaused.value;
};

// Function to send pause command
const sendPauseCommand = async () => {
    console.log(urls.value)
    try {
        const response = await fetch(pause_url.value, {
            method: 'POST',
        });
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        console.log('Paused');

    } catch (error) {
        console.error('Error pausing:', error);
    }
};

// Function to send resume command
const sendResumeCommand = async () => {
    try {
        const response = await fetch(resume_url.value, {
            method: 'POST',
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        console.log('Resumed');

    } catch (error) {
        console.error('Error resuming:', error);
    }
};
</script>
