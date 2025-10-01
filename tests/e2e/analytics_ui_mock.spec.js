import { test, expect } from '@playwright/test';

// Light UI test: analytics dashboard renders from mocked /api/analytics/db

test.describe('RAG e2e - Analytics UI (light)', () => {
  test('Refresh shows key metrics and top lists', async ({ page }) => {
    await page.goto('/');

    await page.route('**/api/analytics/db*', async (route) => {
      const payload = {
        db: 'default',
        chats: 5,
        qa_pairs: 10,
        answered: 8,
        with_contexts: 7,
        answer_len_avg: 123.45,
        answer_len_median: null,
        top_sources: [ { value: 'bitsness_sample.txt', count: 4 } ],
        top_versions: [ { value: 'v1', count: 3 } ],
        top_languages: [ { value: 'vi', count: 6 } ],
      };
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(payload) });
    });

    // Click refresh
    await page.locator('#btn-analytics-refresh').click();

    await expect(page.locator('#an-qa')).toHaveText('10');
    await expect(page.locator('#an-chats')).toHaveText('5');
    await expect(page.locator('#an-withctx')).toHaveText('7');
    await expect(page.locator('#an-top-sources')).toContainText('bitsness_sample.txt');
    await expect(page.locator('#an-top-versions')).toContainText('v1');
    await expect(page.locator('#an-top-langs')).toContainText('vi');
  });
});
