<template>
    <v-card class="pa-1 ma-1" title="Workflows">
        <v-card-text v-if="active_workflows">
            <h3>Active Workflows</h3>
            <WorkflowTable :workflows="active_workflows"/>
        </v-card-text>
        <v-card-text v-else>
            <p>No Active Workflows</p>
        </v-card-text>
        <v-card-text v-if="archived_workflows">
            <h3>Archived Workflows</h3>
            <WorkflowTable :workflows="archived_workflows"/>
        </v-card-text>
        <v-card-text v-else>
            <p>No Archived Workflows</p>
        </v-card-text>
        <v-card-actions>
            <v-spacer></v-spacer>
            <v-btn class="ma-1" @click="$emit('viewWorkflows')" color="blue">View All Workflows</v-btn>
        </v-card-actions>

    </v-card>
</template>

<script setup lang="ts">
import { active_workflows, archived_workflows } from "@/store";
const emits = defineEmits(['viewWorkflows'])
</script>
