/**
 * plugins/index.ts
 *
 * Automatically included in `./src/main.ts`
 */

// Plugins
import VueJsonPretty from 'vue-json-pretty';
import 'vue-json-pretty/lib/styles.css';
import vuetify from './vuetify';

// Types
import type { App } from 'vue';

export function registerPlugins (app: App) {
  app.use(vuetify)
  app.use(VueJsonPretty)
}
