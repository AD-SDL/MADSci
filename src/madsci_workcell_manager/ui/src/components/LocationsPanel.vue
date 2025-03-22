<template>
  <v-card class="pa-1 ma-1" col="3" title="Locations">
    <v-card-text>
      <v-container v-if="locations" fluid class="pa-1">
        <v-row no-gutter wrap justify-content class="pa-1">
          <v-col v-for="value in locations" class="pa-1" cols=12 sm=6 md=4 lg=3 xl=2>
            <v-card-text>
              <h3 wrap>{{ value.location_name }}</h3>
              <p wrap class="text-caption">
                {{ value.reservation }}
              </p>
            </v-card-text>
          </v-col>
        </v-row>
      </v-container>
      <p v-else>No Locations Yet</p>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
const props = defineProps(['locations'])
</script>
