<template>
    <v-card class="pa-1 ma-1" title="Recent Workflows">
        <v-card-text v-if="wfs">
            <WorkflowTable :wc_state=wc_state :wfs="wfs.slice(0, 10)" />
        </v-card-text>
        <v-card-text v-else>
            <p>No Workflows Yet</p>
        </v-card-text>
        <v-card-actions>
            <v-spacer></v-spacer>
            <v-btn class="ma-1" @click="$emit('viewWorkflows')" color="blue">View All Workflows</v-btn>
        </v-card-actions>

    </v-card>
</template>

<script setup lang="ts">
const props = defineProps(['wc_state', 'wfs'])
const emits = defineEmits(['viewWorkflows'])
</script>
