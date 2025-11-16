import { describe, it, expect, beforeEach, vi } from 'vitest'
import { ref } from 'vue'

describe('Store', () => {
  beforeEach(() => {
    vi.resetModules()
  })

  it('initializes main_url with window location', async () => {
    // Mock window.location.host
    Object.defineProperty(window, 'location', {
      value: {
        host: 'localhost:3000',
      },
      writable: true,
    })

    const { main_url } = await import('@/store')
    expect(main_url.value).toBe('http://localhost:3000')
  })

  it('exports reactive refs for state management', async () => {
    const store = await import('@/store')

    // Check that key state variables are exported
    expect(store.workcell_state).toBeDefined()
    expect(store.active_workflows).toBeDefined()
    expect(store.resources).toBeDefined()
    expect(store.locations).toBeDefined()
  })

  it('uses Vue ref for reactive state', async () => {
    const { workcell_state } = await import('@/store')

    // Should be a Vue ref
    expect(workcell_state.value).toBeDefined()
  })
})
