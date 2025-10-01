import { test, expect } from '@playwright/test';

// Light UI test: verify multi-hop UI sends correct fields to /api/multihop_query (non-stream)

test.describe('RAG e2e - Multi-hop (UI light)', () => {
  test('UI sends depth/fanout fields on multihop (non-stream, mocked)', async ({ page }) => {
    await page.goto('/');

    // Ensure non-stream mode
    const streamCk = page.locator('#ck-stream');
    if (await streamCk.isChecked()) await streamCk.uncheck();

    // Toggle multihop and set params
    const mhCk = page.locator('#ck-multihop');
    if (!(await mhCk.isChecked())) await mhCk.check();
    await page.fill('#hop-depth', '2');
    await page.fill('#hop-fanout', '1');
    await page.fill('#hop-fanout1', '1');
    await page.fill('#hop-budget', '0');

    // Intercept /api/multihop_query and validate request payload
    await page.route('**/api/multihop_query', async (route) => {
      const req = route.request();
      let ok = false;
      try {
        const body = req.postDataJSON();
        ok = !!body && body.depth === 2 && body.fanout === 1 && body.fanout_first_hop === 1 && body.budget_ms === 0;
      } catch {}
      if (!ok) {
        return route.fulfill({
          status: 400,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'invalid multihop body' })
        });
      }
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ answer: 'ok', contexts: [], metadatas: [] })
      });
    });

    // Ask
    await page.fill('#txt-query', 'demo multihop');
    await page.fill('#top-k', '2');
    await page.getByRole('button', { name: 'Hỏi' }).click();

    await expect(page.locator('#result')).toContainText('ok');
  });
});
