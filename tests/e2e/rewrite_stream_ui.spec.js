import { test, expect } from '@playwright/test';

// Light UI test: verify rewrite flags sent over streaming /api/stream_query

test.describe('RAG e2e - Rewrite (UI stream light)', () => {
  test('UI sends rewrite_enable=true and rewrite_n on stream', async ({ page }) => {
    await page.goto('/');

    // streaming ON, rewrite ON
    const streamCk = page.locator('#ck-stream');
    if (!(await streamCk.isChecked())) await streamCk.check();
    const rewriteCk = page.locator('#ck-rewrite');
    if (!(await rewriteCk.isChecked())) await rewriteCk.check();
    await page.fill('#rewrite-n', '3');

    // Intercept stream_query
    await page.route('**/api/stream_query', async (route) => {
      const req = route.request();
      let ok = false;
      try {
        const body = req.postDataJSON();
        ok = !!body && body.rewrite_enable === true && parseInt(body.rewrite_n, 10) === 3;
      } catch {}
      const header = '[[CTXJSON]]' + JSON.stringify({ contexts: [], metadatas: [] }) + '\n';
      if (!ok) return route.fulfill({ status: 200, contentType: 'text/plain', body: header + 'bad' });
      return route.fulfill({ status: 200, contentType: 'text/plain', body: header + 'ok' });
    });

    await page.fill('#txt-query', 'demo rewrite');
    await page.fill('#top-k', '2');
    await page.getByRole('button', { name: 'Hỏi' }).click();

    await expect(page.locator('#result')).toContainText('ok');
  });
});
