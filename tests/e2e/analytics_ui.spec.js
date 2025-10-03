import { test, expect } from '@playwright/test';

// UI analytics: tạo DB, ingest, chạy 1-2 stream query để lưu sớm, bấm Refresh và kiểm tra UI có số liệu

test.describe('RAG e2e - Analytics UI (B10a)', () => {
  test('Analytics panel hiển thị số liệu cơ bản', async ({ page }) => {
    await page.goto('/?e2e=1');

    const db = 'andbui';
    await page.fill('#db-new-name', db);
    await page.getByRole('button', { name: 'Tạo DB' }).click();
    await page.selectOption('#db-select', db).catch(() => {});

    // đảm bảo backend đã switch DB
    await page.evaluate(async (db) => {
      await fetch('/api/dbs/use', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: db }) });
    }, db);

    // ingest
    await page.getByRole('button', { name: 'Index tài liệu mẫu' }).click();
    await expect(page.locator('#result')).toContainText(/index|chunks/i, { timeout: 60000 });

    // tạo chat
    const chat = await page.evaluate(async (db) => {
      const resp = await fetch('/api/chats', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ db, name: 'Analytics UI' }) });
      return await resp.json();
    }, db);
    const chatId = chat?.chat?.id;

    // chạy 1 stream query để lưu sớm
    await page.evaluate(async ({ db, chatId }) => {
      const resp = await fetch('/api/stream_query', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ query: 'Bitsness là gì?', k: 2, method: 'bm25', db, chat_id: chatId, save_chat: true }) });
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        if (buffer.indexOf('[[CTXJSON]]') >= 0) { try { await reader.cancel(); } catch {}; break; }
      }
    }, { db, chatId });

    // bấm Refresh (target analytics button explicitly)
    await page.locator('#btn-analytics-refresh').click();

    // kiểm tra UI có số liệu
    await expect(page.locator('#an-chats')).not.toHaveText('-', { timeout: 10000 });
    await expect(page.locator('#an-qa')).not.toHaveText('-', { timeout: 10000 });
    await expect(page.locator('#an-top-sources')).toBeVisible({ timeout: 10000 });
  });
});
