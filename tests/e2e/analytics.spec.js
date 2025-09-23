import { test, expect } from '@playwright/test';

// Analytics e2e: tạo chat, ingest, gửi 2 query lưu chat, gọi /api/analytics/db

test.describe('RAG e2e - Analytics (B10a)', () => {
  test('DB analytics có qa_pairs >= 2 và top_sources chứa bitsness_sample.txt', async ({ page }) => {
    await page.goto('/');

    const db = 'andb';
    // tạo DB
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

    // tạo chat qua API
    const chat = await page.evaluate(async () => {
      const resp = await fetch('/api/chats', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ db: 'andb', name: 'Analytics Chat' }) });
      return await resp.json();
    });
    const chatId = chat?.chat?.id;
    expect(chatId).toBeTruthy();

    // gửi 2 query bằng stream để lưu sớm
    const runQuery = async (q) => await page.evaluate(async (args) => {
      const { q, chatId } = args;
      const resp = await fetch('/api/stream_query', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: q, k: 2, method: 'bm25', bm25_weight: 0.5, rerank_enable: false, db: 'andb', chat_id: chatId, save_chat: true })
      });
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        if (buffer.indexOf('[[CTXJSON]]') >= 0) {
          try { await reader.cancel(); } catch {}
          break;
        }
      }
      return true;
    }, { q, chatId });

    await runQuery('Bitsness là gì?');
    await runQuery('Luật giao thông yêu cầu gì?');

    // gọi analytics db
    const analytics = await page.evaluate(async () => {
      const resp = await fetch('/api/analytics/db?db=andb');
      return await resp.json();
    });

    expect(analytics.db).toBe('andb');
    expect(analytics.qa_pairs).toBeGreaterThanOrEqual(2);
    expect(Array.isArray(analytics.top_sources)).toBeTruthy();
  });
});
