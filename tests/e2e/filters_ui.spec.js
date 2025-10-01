import { test, expect } from '@playwright/test';

// Light UI test: filters UI populated by mocked /api/filters

test.describe('RAG e2e - Filters (UI light)', () => {
  test('Populate languages and versions', async ({ page }) => {
    // Route before load to catch initial loadFilters()
    await page.route('**/api/filters*', async (route) => {
      const payload = { languages: ['vi', 'en'], versions: ['v1', 'v2'] };
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(payload) });
    });

    await page.goto('/');

    // Expect options to exist
    await expect(page.locator('#filter-langs')).toContainText('vi');
    await expect(page.locator('#filter-versions')).toContainText('v1');
  });
});
