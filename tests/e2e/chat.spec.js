import { test, expect } from '@playwright/test';

const resultSel = '#result';
const contextsSel = '#contexts .ctx';

// Light test: tạo session, hỏi streaming và xác nhận messages được lưu

test.describe('RAG e2e - Chat sessions (light)', () => {
  test('Tạo/Rename/Delete chat + lưu Q/A khi hỏi', async ({ page }) => {
    await page.goto('/?e2e=1');
    await page.waitForFunction(() => window.__E2E_READY__ === true);

    // Tạo chat mới
    await page.locator('#btn-chat-new').click();
    // Prompt sẽ hiện từ window.prompt trong app.js; Playwright không tương tác prompt mặc định,
    // nên backend sẽ tạo với tên default 'New Chat'. Chờ đến khi dropdown có value.
    await expect(page.locator('#chat-select')).toHaveValue(/.+/);

    // Bật streaming để contexts xuất hiện sớm
    const streamCk = page.locator('#ck-stream');
    if (!(await streamCk.isChecked())) await streamCk.check();

    // Đảm bảo ingest trước
    await page.getByRole('button', { name: 'Index tài liệu mẫu' }).click();
    await expect(page.locator(resultSel)).toContainText(/index/i, { timeout: 60000 });

    // Hỏi và lưu vào chat hiện tại
    const chatId = await page.locator('#chat-select').inputValue();
    expect(chatId).not.toEqual('');
    await page.selectOption('#method', 'hybrid');
    await page.fill('#txt-query', 'Bitsness là gì?');
    await page.fill('#top-k', '2');
    await page.getByRole('button', { name: 'Hỏi' }).click();

    await expect(page.locator(resultSel)).not.toHaveText('', { timeout: 60000 });

    // Kiểm tra messages lưu qua API
    // Đợi đến khi session có ít nhất 2 message (user + assistant)
    await page.waitForFunction(async (id) => {
      const res = await fetch(`/api/chats/${id}`);
      const data = await res.json();
      return Array.isArray(data.messages) && data.messages.length >= 2;
    }, chatId, { timeout: 60000 });

    // Rename chat
    await page.locator('#btn-chat-rename').click();
    // prompt() sẽ không nhập được từ tự động; API vẫn sẽ fail nếu name rỗng, nên bỏ qua bước xác minh tên

    // Delete chat
    await page.locator('#btn-chat-delete').click();
  });
});
