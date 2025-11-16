import { afterEach } from 'vitest'
import { cleanup } from '@vue/test-utils'

// Cleanup after each test
afterEach(() => {
  cleanup()
})

// Mock fetch globally for tests
global.fetch = vi.fn()

// Mock window.location for tests
Object.defineProperty(window, 'location', {
  value: {
    host: 'localhost:3000',
  },
  writable: true,
})
