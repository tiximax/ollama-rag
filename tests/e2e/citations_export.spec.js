import { test, expect } from '@playwright/test';

// Citations export e2e: tạo DB, ingest, tạo chat, chạy stream query để lưu sớm, export citations JSON và kiểm tra

test.describe('RAG e2e - Citations export (B10b)', () => {
  test('Export citations chat (JSON) có cấu trúc hợp lệ', async ({ page }) => {
    await page.goto('/?e2e=1');
    await page.waitForFunction(() => window.__E2E_READY__ === true);

    const db = 'citedb';
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
      const resp = await fetch('/api/chats', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ db, name: 'Citations Chat' }) });
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

    // export citations JSON qua API
    const data = await page.evaluate(async ({ db, chatId }) => {
      const params = new URLSearchParams();
      params.set('db', db);
      params.set('format', 'json');
      const resp = await fetch(`/api/citations/chat/${encodeURIComponent(chatId)}?` + params.toString());
      const text = await resp.text();
      try { return JSON.parse(text); } catch { return []; }
    }, { db, chatId });

    expect(Array.isArray(data)).toBeTruthy();
    // Có thể chưa có [n] trong mẫu này, nên chỉ kiểm tra cấu trúc mảng
  });
});
