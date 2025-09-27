import { test, expect } from '@playwright/test';

// Light UI test: logs summary panel renders from mocked /api/logs/summary

test.describe('RAG e2e - Logs summary (UI light)', () => {
  test('Refresh summary shows totals and lists', async ({ page }) => {
    await page.goto('/?e2e=1');
    await page.waitForFunction(() => window.__E2E_READY__ === true);

    // Mock summary API
    await page.route('**/api/logs/summary*', async (route) => {
      const payload = {
        db: 'default',
        total: 123,
        median_latency_ms: 250.5,
        contexts_rate: 0.75,
        by_route: [ { key: '/api/stream_query', count: 5 } ],
        by_provider: [ { key: 'ollama', count: 5 } ],
        by_method: [ { key: 'bm25', count: 5 } ],
      };
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(payload) });
    });

    // Click refresh
    await page.locator('#btn-logs-summary-refresh').click();

    await expect(page.locator('#lg-total')).toHaveText('123');
    await expect(page.locator('#lg-by-route')).toContainText('/api/stream_query');
    await expect(page.locator('#lg-by-provider')).toContainText('ollama');
    await expect(page.locator('#lg-by-method')).toContainText('bm25');
  });
});
