import { afterEach, vi } from 'vitest'

// Mock fetch globally for tests
global.fetch = vi.fn()

// Mock window.location for tests
Object.defineProperty(window, 'location', {
  value: {
    host: 'localhost:3000',
  },
  writable: true,
})

afterEach(() => {
  vi.clearAllMocks()
})
