import { test, expect } from '@playwright/test';

// Kiểm tra UI gửi rewrite_enable/rewrite_n trong body về /api/query (non-stream)

test.describe('RAG e2e - Rewrite (UI)', () => {
  test('UI gửi rewrite_enable=true, rewrite_n=2 khi bật Rewrite', async ({ page }) => {
    await page.goto('/?e2e=1');
    await page.waitForFunction(() => window.__E2E_READY__ === true);

    // Tắt streaming để đi qua /api/query
    const streamCk = page.locator('#ck-stream');
    if (await streamCk.isChecked()) await streamCk.uncheck();

    // Bật rewrite và đặt n=2
    const rewriteCk = page.locator('#ck-rewrite');
    await rewriteCk.check();
    await page.fill('#rewrite-n', '2');

    // Intercept /api/query để kiểm tra body
    await page.route('**/api/query', async (route) => {
      const req = route.request();
      let ok = false;
      try {
        const body = req.postDataJSON();
        ok = body && body.rewrite_enable === true && parseInt(body.rewrite_n, 10) === 2;
      } catch {}
      if (!ok) {
        return route.fulfill({
          status: 400,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'missing rewrite fields' })
        });
      }
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ answer: 'ok', contexts: [], metadatas: [] })
      });
    });

    await page.fill('#txt-query', 'câu hỏi demo');
    await page.getByRole('button', { name: 'Hỏi' }).click();

    await expect(page.locator('#result')).toContainText('ok');
  });
});
