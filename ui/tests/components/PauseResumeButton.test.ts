import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, VueWrapper } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import PauseResumeButton from '@/components/AdminButtons/PauseResumeButton.vue'

// Mock the store module
vi.mock('@/store', () => ({
  urls: {
    value: {
      workcell_server_url: 'http://localhost:8005/',
    },
  },
  workcell_state: {
    value: {
      status: {
        paused: false,
      },
    },
  },
}))

describe('PauseResumeButton', () => {
  let wrapper: VueWrapper
  let vuetify: ReturnType<typeof createVuetify>

  beforeEach(() => {
    // Create a new Vuetify instance for each test
    vuetify = createVuetify({
      components,
      directives,
    })

    // Mock fetch
    global.fetch = vi.fn()
  })

  it('renders pause button when not paused (workcell mode)', () => {
    wrapper = mount(PauseResumeButton, {
      global: {
        plugins: [vuetify],
      },
    })

    const button = wrapper.find('button')
    expect(button.exists()).toBe(true)
    expect(button.classes()).toContain('bg-orange-darken-1')
  })

  it('renders resume button when paused (workcell mode)', async () => {
    const { workcell_state } = await import('@/store')
    workcell_state.value = {
      status: {
        paused: true,
      },
    }

    wrapper = mount(PauseResumeButton, {
      global: {
        plugins: [vuetify],
      },
    })

    await wrapper.vm.$nextTick()
    const button = wrapper.find('button')
    expect(button.classes()).toContain('bg-green-darken-3')
  })

  it('shows correct tooltip text for workcell pause', () => {
    wrapper = mount(PauseResumeButton, {
      global: {
        plugins: [vuetify],
      },
    })

    const tooltip = wrapper.findComponent({ name: 'VTooltip' })
    expect(tooltip.exists()).toBe(true)
  })

  it('calls pause endpoint when clicked (not paused)', async () => {
    const mockFetch = vi.fn().mockResolvedValue({ ok: true })
    global.fetch = mockFetch

    wrapper = mount(PauseResumeButton, {
      global: {
        plugins: [vuetify],
      },
    })

    await wrapper.find('button').trigger('click')
    await wrapper.vm.$nextTick()

    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8005/admin/pause',
      expect.objectContaining({ method: 'POST' })
    )
  })

  it('renders with node-specific configuration', () => {
    wrapper = mount(PauseResumeButton, {
      props: {
        node: 'test-node',
        node_status: {
          BUSY: true,
          PAUSED: false,
        },
      },
      global: {
        plugins: [vuetify],
      },
    })

    expect(wrapper.exists()).toBe(true)
  })

  it('disables button when node is not busy or paused', () => {
    wrapper = mount(PauseResumeButton, {
      props: {
        node: 'test-node',
        node_status: {
          BUSY: false,
          PAUSED: false,
        },
      },
      global: {
        plugins: [vuetify],
      },
    })

    const button = wrapper.find('button')
    expect(button.attributes('disabled')).toBeDefined()
  })
})
