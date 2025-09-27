import { test, expect } from '@playwright/test';

// Logs Dashboard UI: enable logs, fire a stream query to log early, refresh logs summary, and check basic fields

test.describe('RAG e2e - Logs Dashboard UI', () => {
  test('Summary panel hiển thị số liệu', async ({ page }) => {
    await page.goto('/?e2e=1');
    await page.waitForFunction(() => window.__E2E_READY__ === true);

    const db = 'loguidb';
    await page.fill('#db-new-name', db);
    await page.getByRole('button', { name: 'Tạo DB' }).click();
    await page.selectOption('#db-select', db).catch(() => {});

    // backend switch
    await page.evaluate(async (db) => {
      await fetch('/api/dbs/use', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: db }) });
    }, db);

    // enable logs
    await page.evaluate(async (db) => {
      await fetch('/api/logs/enable', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ db, enabled: true }) });
    }, db);

    // ingest
    await page.getByRole('button', { name: 'Index tài liệu mẫu' }).click();
    await expect(page.locator('#result')).toContainText(/index|chunks/i, { timeout: 60000 });

    // one stream query to produce a log (early header)
    await page.evaluate(async (db) => {
      const resp = await fetch('/api/stream_query', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ query: 'Bitsness là gì?', k: 2, method: 'bm25', db }) });
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        if (buffer.indexOf('[[CTXJSON]]') >= 0) { try { await reader.cancel(); } catch {}; break; }
      }
    }, db);

    // refresh logs summary
    await page.locator('#btn-logs-summary-refresh').click();

    await expect(page.locator('#lg-total')).not.toHaveText('-', { timeout: 10000 });
    await expect(page.locator('#lg-by-route')).toBeVisible({ timeout: 10000 });
  });
});
