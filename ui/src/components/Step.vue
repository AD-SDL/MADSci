<!--
<template>
<v-card >
              <v-card-title >
                <h4>{{ action.name }}</h4>
              </v-card-title>
              <v-card-text>
                <h5>Description</h5>
                <p class="py-1 my-1">{{ action.description }}</p>
                <h5 v-if="Object.keys(action.args).length > 0">Arguments</h5>
                <v-data-table v-if="Object.keys(action.args).length > 0" :headers="arg_headers" :items="Object.keys(action.args).map(function(key){
    return action.args[key];})" hover items-per-page="-1"
                  no-data-text="No Arguments" density="compact"> -->
                  <!-- eslint-disable vue/no-parsing-error-->
                  <!-- <template v-slot:item="{ item }: { item: any }">
                    <tr>
                      <td>{{ item.name }}</td>
                      <td>{{ item.argument_type }}</td>
                      <td>{{ item.required }}</td>
                      <td>{{ item.default }}</td>
                      <td>{{ item.description }}</td>
                      <td><v-text-field @update:focused="set_text(action)" height="20px" v-model="item.value"
                          dense>
                        </v-text-field></td>
                    </tr>
                  </template>
                  <template #bottom></template>
                </v-data-table>
                <h5 v-if="Object.keys(action.files).length > 0">Files</h5>
                <v-data-table v-if="Object.keys(action.files).length > 0" :headers="file_headers" :items="Object.keys(action.files).map(function(key){
    return action.files[key];})" hover
                  items-per-page="-1" no-data-text="No Files" density="compact">
                  <template v-slot:item="{ item }: { item: any }">
                    <tr>
                      <td>{{ item.name }}</td>
                      <td>{{ item.required }}</td>
                      <td>{{ item.description }}</td>
                      <td><v-file-input v-model="item.value" label="File input"></v-file-input></td>
                    </tr>
                  </template>
                </v-data-table>
                <h5 v-if="Object.keys(action.locations).length > 0">Locations</h5>
                <v-data-table v-if="Object.keys(action.locations).length > 0" :headers="locations_headers" :items="Object.keys(action.locations).map(function(key){
    return action.locations[key];})" hover
                  items-per-page="-1" no-data-text="No Locations" density="compact">
                  <template v-slot:item="{ item }: { item: any }">
                    <tr>
                      <td>{{ item.name }}</td>
                      <td>{{ item.required }}</td>
                      <td>{{ item.description }}</td>
                      <td>
                        <v-text-field v-model=item.value list="locations" id="locations_id" name="locations_name" />
                        <datalist id="locations">
                        <option v-for="option in locations.map(function(location: any){return location.location_name;})" :value="option">{{option}}</option>
                        </datalist>
                        </td>
                    </tr>
                  </template>
                </v-data-table>
                <h5 v-if="action.results.length > 0">Results</h5>
                <v-data-table v-if="action.results.length > 0" :headers="result_headers" :items="action.results" hover
                  items-per-page="-1" no-data-text="No Results" density="compact">
                  <template v-slot:item="{ item }: { item: any }">
                    <tr>
                      <td>{{ item.label }}</td>
                      <td>{{ item.type }}</td>
                      <td>{{ item.description }}</td>
                    </tr>
                  </template>
                </v-data-table>

              </v-card-text>
            </v-card>
    </template>

     -->
