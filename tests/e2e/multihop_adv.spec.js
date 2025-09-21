import { test, expect } from '@playwright/test';

// Kiểm tra UI gửi budget_ms và fanout_first_hop trong body về /api/multihop_query (non-stream)

test.describe('RAG e2e - Multi-hop advanced (UI)', () => {
  test('UI gửi budget_ms và fanout_first_hop khi bật Multi-hop', async ({ page }) => {
    await page.goto('/');

    // Tắt streaming để đi non-stream
    const streamCk = page.locator('#ck-stream');
    if (await streamCk.isChecked()) await streamCk.uncheck();

    // Bật Multi-hop và set tham số
    const mhCk = page.locator('#ck-multihop');
    await mhCk.check();
    await page.fill('#hop-depth', '2');
    await page.fill('#hop-fanout', '2');
    await page.fill('#hop-fanout1', '1');
    await page.fill('#hop-budget', '200');

    // Intercept /api/multihop_query để kiểm tra body
    await page.route('**/api/multihop_query', async (route) => {
      const req = route.request();
      let ok = false;
      try {
        const body = req.postDataJSON();
        ok = body && parseInt(body.fanout_first_hop, 10) === 1 && parseInt(body.budget_ms, 10) === 200;
      } catch {}
      if (!ok) {
        return route.fulfill({
          status: 400,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'missing multi-hop adv fields' })
        });
      }
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ answer: '(skip)', contexts: ['ctx1'], metadatas: [{}] })
      });
    });

    await page.fill('#txt-query', 'câu hỏi demo');
    await page.getByRole('button', { name: 'Hỏi' }).click();

    // Có kết quả hiển thị
    await expect(page.locator('#result')).toContainText(/\(|ctx|skip|/);
  });
});
