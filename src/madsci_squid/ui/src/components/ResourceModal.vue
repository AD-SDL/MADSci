<template>
  <v-dialog class="pa-3" v-slot:default="{ isActive }">
    <v-card>
      <v-card-title>
        <h2 class="title">Resource: {{ modal_title }}</h2>
        {{modal_text.resource_id}}
      </v-card-title>
      <v-card-text>
        <div v-if="modal_text.base_type=='stack'">
          <Stack :resource="modal_text"/>
        </div>
        <div v-else-if="modal_text.base_type=='slot'">
          <Slot :resource="modal_text" />
        </div>
        <div v-else>
        {{ modal_text }}
      </div>
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn flat @click="isActive.value = false" class="primary--text">close</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import Stack from "./ResourceComponents/Stack.vue";
import Slot from "./ResourceComponents/Slot.vue";
const props = defineProps(['modal_title', 'modal_text'])
const flowdef = ref(false)
</script>
