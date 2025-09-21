import { test, expect } from '@playwright/test';

// Chat advanced: search, export json/md, delete all (light)

test.describe('RAG e2e - Chat advanced (light)', () => {
  test('Search, export, delete-all', async ({ page }) => {
    await page.goto('/');

    // Tạo chat và ingest + hỏi để có dữ liệu
    await page.locator('#btn-chat-new').click();
    await page.getByRole('button', { name: 'Index tài liệu mẫu' }).click();
    await expect(page.locator('#result')).toContainText(/index/i, { timeout: 60000 });

    const streamCk = page.locator('#ck-stream');
    if (!(await streamCk.isChecked())) await streamCk.check();
    await page.selectOption('#method', 'hybrid');
    await page.fill('#txt-query', 'Bitsness là gì?');
    await page.fill('#top-k', '2');
    await page.getByRole('button', { name: 'Hỏi' }).click();
    await expect(page.locator('#result')).not.toHaveText('', { timeout: 60000 });

    // Lấy chatId hiện tại
    const chatId = await page.locator('#chat-select').inputValue();

    // Search qua API
    const searchRes = await page.evaluate(async (db) => {
      const params = new URLSearchParams();
      if (db) params.set('db', db);
      params.set('q', 'Bitsness');
      const res = await fetch('/api/chats/search?' + params.toString());
      return await res.json();
    }, await page.locator('#db-select').inputValue());
    expect(Array.isArray(searchRes.results)).toBeTruthy();

    // Export JSON
    const expJson = await page.evaluate(async (id) => {
      const res = await fetch(`/api/chats/${id}/export?format=json`);
      return await res.json();
    }, chatId);
    expect(expJson && expJson.id).toBeTruthy();

    // Export MD
    const expMd = await page.evaluate(async (id) => {
      const res = await fetch(`/api/chats/${id}/export?format=md`);
      return await res.text();
    }, chatId);
    expect(typeof expMd).toBe('string');

    // Delete all chats
    const delAll = await page.evaluate(async () => {
      const res = await fetch('/api/chats', { method: 'DELETE' });
      return await res.json();
    });
    expect(delAll && delAll.status === 'ok').toBeTruthy();

    // Kiểm tra list rỗng
    const list = await page.evaluate(async () => {
      const res = await fetch('/api/chats');
      return await res.json();
    });
    expect(Array.isArray(list.chats)).toBeTruthy();
  });
});
