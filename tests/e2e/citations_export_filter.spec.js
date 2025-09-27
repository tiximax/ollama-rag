import { test, expect } from '@playwright/test';

test.describe('RAG e2e - Citations export filters (B10b)', () => {
  test('Export citations chat với filter sources substring (không bắt buộc non-empty)', async ({ page }) => {
    await page.goto('/?e2e=1');
    await page.waitForFunction(() => window.__E2E_READY__ === true);

    const db = 'citedb2';
    await page.fill('#db-new-name', db);
    await page.getByRole('button', { name: 'Tạo DB' }).click();
    await page.selectOption('#db-select', db).catch(() => {});

    await page.evaluate(async (db) => {
      await fetch('/api/dbs/use', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: db }) });
    }, db);

    await page.getByRole('button', { name: 'Index tài liệu mẫu' }).click();
    await expect(page.locator('#result')).toContainText(/index|chunks/i, { timeout: 60000 });

    const chat = await page.evaluate(async (db) => {
      const resp = await fetch('/api/chats', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ db, name: 'Citations Filter' }) });
      return await resp.json();
    }, db);
    const chatId = chat?.chat?.id;

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

    const data = await page.evaluate(async ({ db, chatId }) => {
      const params = new URLSearchParams();
      params.set('db', db);
      params.set('format', 'json');
      params.set('sources', 'bitsness');
      const resp = await fetch(`/api/citations/chat/${encodeURIComponent(chatId)}?` + params.toString());
      const text = await resp.text();
      try { return JSON.parse(text); } catch { return []; }
    }, { db, chatId });

    expect(Array.isArray(data)).toBeTruthy();
    // Nếu có phần tử, tất cả phải có source chứa 'bitsness'
    for (const c of data) {
      expect(String(c.source || '')).toContain('bitsness');
    }
  });
});
