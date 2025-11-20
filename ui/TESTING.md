# MADSci Dashboard Testing Guide

This guide provides comprehensive information about testing the MADSci Dashboard.

## Table of Contents

- [Overview](#overview)
- [Testing Stack](#testing-stack)
- [Quick Start](#quick-start)
- [Test Structure](#test-structure)
- [Writing Tests](#writing-tests)
- [Running Tests](#running-tests)
- [Best Practices](#best-practices)
- [CI/CD Integration](#cicd-integration)

## Overview

The MADSci Dashboard uses a comprehensive testing approach with three layers:

1. **Unit Tests**: Test individual functions and utilities in isolation
2. **Component Tests**: Test Vue components with Vitest and Vue Test Utils
3. **End-to-End Tests**: Test complete user workflows with Playwright

## Testing Stack

### Core Testing Tools

- **[Vitest](https://vitest.dev/)**: Fast unit testing framework with native Vite integration
- **[@vue/test-utils](https://test-utils.vuejs.org/)**: Official Vue.js component testing utilities
- **[@testing-library/vue](https://testing-library.com/docs/vue-testing-library/intro/)**: User-centric testing approach
- **[Playwright](https://playwright.dev/)**: End-to-end testing framework
- **[happy-dom](https://github.com/capricorn86/happy-dom)**: Lightweight DOM implementation for tests

### Additional Tools

- **[@vitest/ui](https://vitest.dev/guide/ui.html)**: Visual test UI for development
- **[@vitest/coverage-v8](https://vitest.dev/guide/coverage.html)**: Code coverage reporting
- **[Vuetify](https://vuetifyjs.com/)**: Properly configured for component tests

## Quick Start

### Installation

```bash
# Install all dependencies (including test dependencies)
yarn install

# Install Playwright browsers (first time only)
npx playwright install
```

### Running Tests

```bash
# Run all unit and component tests
yarn test

# Run tests in watch mode (for development)
yarn test

# Run tests once and exit
yarn test:unit

# Open Vitest UI for interactive testing
yarn test:ui

# Run tests with coverage
yarn test:coverage

# Run E2E tests
yarn test:e2e

# Run E2E tests with UI
yarn test:e2e:ui

# Debug E2E tests
yarn test:e2e:debug
```

## Test Structure

```
ui/
├── tests/
│   ├── unit/              # Unit tests for utilities and functions
│   │   └── store.test.ts
│   ├── components/        # Component tests
│   │   ├── App.test.ts
│   │   └── PauseResumeButton.test.ts
│   ├── e2e/              # End-to-end tests
│   │   ├── dashboard.spec.ts
│   │   └── example.spec.ts
│   └── setup.ts          # Global test setup
├── vitest.config.ts      # Vitest configuration
└── playwright.config.ts  # Playwright configuration
```

## Writing Tests

### Unit Tests

Unit tests focus on testing individual functions and utilities in isolation.

```typescript
// tests/unit/example.test.ts
import { describe, it, expect } from 'vitest'

describe('utility function', () => {
  it('performs calculation correctly', () => {
    const result = someUtilityFunction(2, 3)
    expect(result).toBe(5)
  })
})
```

### Component Tests

Component tests verify Vue components work correctly with different props and user interactions.

```typescript
// tests/components/MyComponent.test.ts
import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import MyComponent from '@/components/MyComponent.vue'

describe('MyComponent', () => {
  let vuetify: ReturnType<typeof createVuetify>

  beforeEach(() => {
    vuetify = createVuetify({
      components,
      directives,
    })
  })

  it('renders correctly', () => {
    const wrapper = mount(MyComponent, {
      props: {
        title: 'Test Title',
      },
      global: {
        plugins: [vuetify],
      },
    })

    expect(wrapper.text()).toContain('Test Title')
  })

  it('handles user interaction', async () => {
    const wrapper = mount(MyComponent, {
      global: {
        plugins: [vuetify],
      },
    })

    await wrapper.find('button').trigger('click')
    expect(wrapper.emitted()).toHaveProperty('click')
  })
})
```

### Mocking the Store

When testing components that use the global store, mock it:

```typescript
import { vi } from 'vitest'

vi.mock('@/store', () => ({
  urls: {
    value: {
      workcell_server_url: 'http://localhost:8005/',
    },
  },
  workcell_state: {
    value: {
      status: { paused: false },
    },
  },
}))
```

### Mocking API Calls

Mock fetch for component tests:

```typescript
import { vi } from 'vitest'

beforeEach(() => {
  global.fetch = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ data: 'test' }),
  })
})
```

### End-to-End Tests

E2E tests verify complete user workflows in a real browser environment.

```typescript
// tests/e2e/workflow.spec.ts
import { test, expect } from '@playwright/test'

test('user can view dashboard', async ({ page }) => {
  await page.goto('/')

  // Check page loaded
  await expect(page.locator('#app')).toBeVisible()

  // Verify tabs are present
  const tabs = page.locator('.v-tab')
  await expect(tabs.first()).toBeVisible()
})

test('user can interact with workcells', async ({ page }) => {
  await page.goto('/')

  // Mock API response
  await page.route('**/context', (route) => {
    route.fulfill({
      status: 200,
      body: JSON.stringify({
        workcell_server_url: 'http://localhost:8005/',
      }),
    })
  })

  // Test interaction
  await page.click('.v-tab:has-text("Workcells")')
  await expect(page.locator('.workcell-panel')).toBeVisible()
})
```

## Running Tests

### Development Workflow

1. **Watch Mode**: Run `yarn test` to start watch mode
2. **Write Test**: Create or modify test files
3. **Auto-run**: Tests automatically re-run on file changes
4. **Visual UI**: Use `yarn test:ui` for visual feedback

### CI/CD Workflow

```bash
# Run all tests with coverage
yarn test:coverage

# Run E2E tests in CI mode
yarn test:e2e
```

### Coverage Reports

```bash
# Generate coverage report
yarn test:coverage

# View HTML report
open coverage/index.html
```

Coverage reports are generated in the `coverage/` directory with multiple formats:
- **HTML**: Visual coverage report
- **LCOV**: For CI tools integration
- **JSON**: Programmatic access
- **Text**: Console summary

## Best Practices

### General Testing Principles

1. **Test Behavior, Not Implementation**: Focus on what users see and do
2. **Keep Tests Simple**: Each test should verify one thing
3. **Use Descriptive Names**: Test names should explain what they verify
4. **Arrange-Act-Assert**: Structure tests clearly
5. **Avoid Test Interdependence**: Tests should be independent

### Component Testing

1. **Mount with Vuetify**: Always include Vuetify plugin for components
2. **Mock External Dependencies**: Mock store, API calls, etc.
3. **Test User Interactions**: Click, type, hover, etc.
4. **Check Accessibility**: Verify ARIA labels and roles
5. **Test Edge Cases**: Empty states, errors, loading states

### E2E Testing

1. **Use Data Test IDs**: Add `data-testid` attributes for stable selectors
2. **Wait for Elements**: Use Playwright's auto-waiting features
3. **Mock External APIs**: Control test data with route mocking
4. **Test Critical Paths**: Focus on most important user workflows
5. **Keep Tests Fast**: Mock backend when possible

### Performance

1. **Parallel Execution**: Vitest runs tests in parallel by default
2. **Selective Testing**: Use `.only` or `.skip` during development
3. **Minimize Setup**: Share setup code with `beforeEach`
4. **Fast DOM**: happy-dom is faster than jsdom

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install dependencies
        run: yarn install
        working-directory: ui

      - name: Run unit tests
        run: yarn test:unit
        working-directory: ui

      - name: Run E2E tests
        run: yarn test:e2e
        working-directory: ui

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./ui/coverage/lcov.info
```

### Pre-commit Hooks

Add to `.git/hooks/pre-commit`:

```bash
#!/bin/bash
cd ui
yarn test:unit
if [ $? -ne 0 ]; then
  echo "Tests failed. Commit aborted."
  exit 1
fi
```

## Troubleshooting

### Common Issues

#### Tests Hang or Timeout

```bash
# Increase timeout in vitest.config.ts
export default defineConfig({
  test: {
    testTimeout: 10000,
  },
})
```

#### Vuetify Components Not Rendering

Ensure Vuetify is properly installed in tests:

```typescript
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

const vuetify = createVuetify({ components, directives })

mount(Component, {
  global: { plugins: [vuetify] },
})
```

#### Mock Not Working

Reset mocks between tests:

```typescript
import { vi, beforeEach } from 'vitest'

beforeEach(() => {
  vi.resetAllMocks()
})
```

#### Playwright Browser Not Found

```bash
npx playwright install
```

## Resources

- [Vitest Documentation](https://vitest.dev/)
- [Vue Test Utils](https://test-utils.vuejs.org/)
- [Testing Library](https://testing-library.com/)
- [Playwright Documentation](https://playwright.dev/)
- [Vuetify Testing Guide](https://vuetifyjs.com/en/getting-started/unit-testing/)

## Contributing

When adding new features to the dashboard:

1. Write tests first (TDD approach recommended)
2. Ensure all tests pass before committing
3. Maintain or improve code coverage
4. Add E2E tests for new user-facing features
5. Update this guide if adding new testing patterns
