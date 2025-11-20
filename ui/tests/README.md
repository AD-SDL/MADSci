# Dashboard Tests

This directory contains all automated tests for the MADSci Dashboard.

## Directory Structure

```
tests/
├── unit/              # Unit tests for utilities and pure functions
├── components/        # Component tests for Vue components
├── e2e/              # End-to-end tests with Playwright
├── setup.ts          # Global test setup and mocks
└── README.md         # This file
```

## Test Organization

### Unit Tests (`unit/`)

Tests for isolated functions, utilities, and business logic that don't require DOM or Vue.

**Examples:**
- Store initialization logic
- Utility functions
- Data transformations
- API response parsing

**File naming:** `<module-name>.test.ts`

### Component Tests (`components/`)

Tests for Vue components using Vue Test Utils and Vuetify.

**What to test:**
- Component rendering with different props
- User interactions (clicks, input, etc.)
- Component state changes
- Event emissions
- Conditional rendering
- Accessibility

**File naming:** `<ComponentName>.test.ts`

**Template:**
```typescript
import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import YourComponent from '@/components/YourComponent.vue'

describe('YourComponent', () => {
  let vuetify: ReturnType<typeof createVuetify>

  beforeEach(() => {
    vuetify = createVuetify({ components, directives })
  })

  it('renders correctly', () => {
    const wrapper = mount(YourComponent, {
      global: { plugins: [vuetify] },
    })
    expect(wrapper.exists()).toBe(true)
  })
})
```

### E2E Tests (`e2e/`)

End-to-end tests using Playwright that test complete user workflows.

**What to test:**
- Critical user journeys
- Multi-step workflows
- Integration with backend APIs
- Cross-browser compatibility
- Navigation flows

**File naming:** `<feature-name>.spec.ts`

**Template:**
```typescript
import { test, expect } from '@playwright/test'

test('user can complete workflow', async ({ page }) => {
  await page.goto('/')
  // Test steps...
  await expect(page.locator('.result')).toBeVisible()
})
```

## Running Tests

See [../TESTING.md](../TESTING.md) for detailed information on running tests.

**Quick reference:**
```bash
# Unit and component tests
yarn test              # Watch mode
yarn test:unit         # Run once
yarn test:ui           # Visual UI

# E2E tests
yarn test:e2e          # Run E2E tests
yarn test:e2e:ui       # With UI

# Coverage
yarn test:coverage     # Generate coverage report
```

## Writing Good Tests

### Best Practices

1. **Descriptive test names**: Use clear, descriptive names that explain what is being tested
   ```typescript
   // Good
   it('displays error message when API call fails', () => {})

   // Bad
   it('works', () => {})
   ```

2. **Arrange-Act-Assert pattern**:
   ```typescript
   it('updates count when button is clicked', async () => {
     // Arrange: Set up test conditions
     const wrapper = mount(Counter)

     // Act: Perform the action
     await wrapper.find('button').trigger('click')

     // Assert: Verify the result
     expect(wrapper.text()).toContain('Count: 1')
   })
   ```

3. **Test behavior, not implementation**: Focus on what users see and do
   ```typescript
   // Good: Tests user-visible behavior
   expect(wrapper.text()).toContain('Paused')

   // Bad: Tests internal implementation
   expect(wrapper.vm.internalState).toBe(true)
   ```

4. **One assertion per test**: Each test should verify one specific behavior
   ```typescript
   // Good
   it('displays pause icon when not paused', () => {
     expect(wrapper.find('.icon').text()).toBe('mdi-pause')
   })

   it('displays resume icon when paused', () => {
     expect(wrapper.find('.icon').text()).toBe('mdi-play')
   })
   ```

5. **Mock external dependencies**: Isolate the code under test
   ```typescript
   vi.mock('@/store', () => ({
     workcell_state: { value: mockState },
   }))
   ```

### Common Patterns

#### Mocking Fetch Calls

```typescript
import { vi } from 'vitest'

beforeEach(() => {
  global.fetch = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ data: 'test' }),
  })
})
```

#### Testing Vuetify Components

```typescript
const vuetify = createVuetify({
  components,
  directives,
})

const wrapper = mount(Component, {
  global: {
    plugins: [vuetify],
  },
})
```

#### Testing User Interactions

```typescript
// Click
await wrapper.find('button').trigger('click')

// Input
await wrapper.find('input').setValue('test value')

// Check emitted events
expect(wrapper.emitted()).toHaveProperty('update')
```

#### Testing Async Behavior

```typescript
it('loads data on mount', async () => {
  const wrapper = mount(Component)

  // Wait for async operations
  await wrapper.vm.$nextTick()

  expect(wrapper.text()).toContain('Loaded')
})
```

## Debugging Tests

### Vitest

```bash
# Run specific test file
yarn test PauseResumeButton

# Run specific test
yarn test -t "renders pause button"

# Debug with UI
yarn test:ui
```

### Playwright

```bash
# Debug mode (opens browser)
yarn test:e2e:debug

# Headed mode (see browser while running)
yarn test:e2e --headed

# Specific test file
yarn test:e2e dashboard.spec.ts
```

### Tips

1. **Use console.log in tests**: Available in Vitest output
2. **Inspect wrapper HTML**: `console.log(wrapper.html())`
3. **Check component props**: `console.log(wrapper.props())`
4. **View emitted events**: `console.log(wrapper.emitted())`

## Contributing

When adding new features:

1. Write tests first (TDD recommended)
2. Ensure all tests pass before committing
3. Maintain or improve code coverage
4. Add E2E tests for user-facing features
5. Update this README if introducing new patterns

## Resources

- [Vitest Documentation](https://vitest.dev/)
- [Vue Test Utils](https://test-utils.vuejs.org/)
- [Playwright Documentation](https://playwright.dev/)
- [Testing Library](https://testing-library.com/)
- [Main Testing Guide](../TESTING.md)
