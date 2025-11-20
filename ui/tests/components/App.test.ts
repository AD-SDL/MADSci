import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import App from '@/App.vue'

describe('App', () => {
  let vuetify: ReturnType<typeof createVuetify>

  beforeEach(() => {
    vuetify = createVuetify({
      components,
      directives,
    })
  })

  it('renders the App component', () => {
    const wrapper = mount(App, {
      global: {
        plugins: [vuetify],
      },
    })

    expect(wrapper.exists()).toBe(true)
  })

  it('contains a v-app component', () => {
    const wrapper = mount(App, {
      global: {
        plugins: [vuetify],
      },
    })

    const vApp = wrapper.findComponent({ name: 'VApp' })
    expect(vApp.exists()).toBe(true)
  })
})
