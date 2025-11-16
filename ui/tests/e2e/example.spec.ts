import { test, expect } from '@playwright/test'

/**
 * Example E2E test file
 * This demonstrates basic Playwright testing patterns for the MADSci Dashboard
 */

test('basic navigation test', async ({ page }) => {
  await page.goto('/')

  // Check that the page loaded
  await expect(page).toHaveURL('http://localhost:3000/')

  // Verify the app container is present
  const app = page.locator('#app')
  await expect(app).toBeVisible()
})

test('can interact with UI elements', async ({ page }) => {
  await page.goto('/')

  // Example: Click on first available button (if any)
  const buttons = page.locator('button')
  const count = await buttons.count()

  if (count > 0) {
    // Just verify buttons exist and are visible
    await expect(buttons.first()).toBeVisible()
  }
})
