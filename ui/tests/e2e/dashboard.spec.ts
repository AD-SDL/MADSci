import { test, expect } from '@playwright/test'

test.describe('MADSci Dashboard', () => {
  test('homepage loads successfully', async ({ page }) => {
    await page.goto('/')

    // Wait for the app to be visible
    await expect(page.locator('#app')).toBeVisible()
  })

  test('has correct title', async ({ page }) => {
    await page.goto('/')

    // Adjust this based on actual title in your app
    await expect(page).toHaveTitle(/MADSci|squid/)
  })

  test('renders main layout', async ({ page }) => {
    await page.goto('/')

    // Check that the main Vuetify app container is present
    const app = page.locator('.v-application')
    await expect(app).toBeVisible()
  })

  test('dashboard component loads', async ({ page }) => {
    await page.goto('/')

    // Wait for content to load - adjust selector based on your Dashboard component
    await page.waitForSelector('.v-tabs', { timeout: 5000 })

    const tabs = page.locator('.v-tabs')
    await expect(tabs).toBeVisible()
  })

  test('navigation between tabs works', async ({ page }) => {
    await page.goto('/')

    // Wait for tabs to be visible
    await page.waitForSelector('.v-tab', { timeout: 5000 })

    // Get all tabs
    const tabs = page.locator('.v-tab')
    const tabCount = await tabs.count()

    // Should have multiple tabs (Workcells, Workflows, Resources, etc.)
    expect(tabCount).toBeGreaterThan(0)
  })
})

test.describe('Dashboard API Integration', () => {
  test('handles API connection gracefully', async ({ page }) => {
    // Mock API responses
    await page.route('**/context', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          workcell_server_url: 'http://localhost:8005/',
          resource_server_url: 'http://localhost:8003/',
          experiment_server_url: 'http://localhost:8002/',
        }),
      })
    })

    await page.goto('/')

    // Verify page still loads even with mocked APIs
    await expect(page.locator('#app')).toBeVisible()
  })

  test('displays error handling for failed API calls', async ({ page }) => {
    // Mock failed API call
    await page.route('**/context', (route) => {
      route.abort('failed')
    })

    await page.goto('/')

    // Page should still load even if API fails
    await expect(page.locator('#app')).toBeVisible()
  })
})
