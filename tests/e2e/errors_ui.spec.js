import { test, expect } from '@playwright/test';

// Light UI test: negative-path errors for non-stream /api/query and streaming /api/stream_query

test.describe('RAG e2e - Errors (UI light)', () => {
  test('Non-stream /api/query 500 shows error text', async ({ page }) => {
    await page.goto('/');

    // Non-stream mode
    const streamCk = page.locator('#ck-stream');
    if (await streamCk.isChecked()) await streamCk.uncheck();

    await page.route('**/api/query', async (route) => {
      return route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'server error' }) });
    });

    await page.fill('#txt-query', 'demo');
    await page.getByRole('button', { name: 'Hỏi' }).click();

    await expect(page.locator('#result')).toContainText('Lỗi truy vấn');
  });

  test('Streaming /api/stream_query non-OK shows error status text', async ({ page }) => {
    await page.goto('/');

    // Stream mode
    const streamCk = page.locator('#ck-stream');
    if (!(await streamCk.isChecked())) await streamCk.check();

    await page.route('**/api/stream_query', async (route) => {
      return route.fulfill({ status: 503, contentType: 'text/plain', body: 'fail' });
    });

    await page.fill('#txt-query', 'demo');
    await page.getByRole('button', { name: 'Hỏi' }).click();

    await expect(page.locator('#result')).toContainText('Streaming thất bại');
  });
});
