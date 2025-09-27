/**
 * plugins/index.ts
 *
 * Automatically included in `./src/main.ts`
 */

// Plugins
import VueJsonPretty from 'vue-json-pretty';
import 'vue-json-pretty/lib/styles.css';
import vuetify from './vuetify';
import PrimeVue from 'primevue/config'
import 'primevue/resources/themes/saga-blue/theme.css' // or another theme
import 'primevue/resources/primevue.min.css'
import 'primeicons/primeicons.css'

// Types
import type { App } from 'vue';

export function registerPlugins (app: App) {
  app.use(vuetify)
  app.use(VueJsonPretty)
  app.use(PrimeVue)
}
