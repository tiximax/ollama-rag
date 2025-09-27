import { test, expect } from '@playwright/test';

const resultSel = '#result';
const contextsSel = '#contexts .ctx';

async function ensureDb(page, name) {
  await page.fill('#db-new-name', name);
  await page.getByRole('button', { name: 'Tạo DB' }).click();
  await page.selectOption('#db-select', name).catch(() => {});
}

async function ingestSamples(page) {
  await page.getByRole('button', { name: 'Index tài liệu mẫu' }).click();
  await expect(page.locator(resultSel)).toContainText(/index|chunks/i, { timeout: 60000 });
}

test.describe('RAG e2e - Feedback (B8)', () => {
  test('Gửi feedback 👍 với comment và xác nhận lưu', async ({ page }) => {
    await page.goto('/?e2e=1');
    await page.waitForFunction(() => window.__E2E_READY__ === true);

    const db = 'fbdb';
    await ensureDb(page, db);
    await page.selectOption('#db-select', db);

    await ingestSamples(page);

    // hỏi để có answer/contexts
    await page.selectOption('#method', 'bm25');
    const streamCk = page.locator('#ck-stream');
    if (!(await streamCk.isChecked())) await streamCk.check();

    await page.fill('#txt-query', 'Bitsness là gì?');
    await page.fill('#top-k', '2');
    await page.getByRole('button', { name: 'Hỏi' }).click();
    await expect(page.locator(resultSel)).not.toHaveText('', { timeout: 60000 });

    // gửi feedback
    await page.getByRole('button', { name: '👍' }).click();
    await page.fill('#fb-comment', 'good');
    await page.getByRole('button', { name: 'Gửi feedback' }).click();

    // đọc lại feedback qua API
    const data = await page.evaluate(async () => {
      const resp = await fetch('/api/feedback?limit=5');
      return resp.json();
    });
    expect(Array.isArray(data.items)).toBeTruthy();
    expect(data.items.length).toBeGreaterThan(0);
    const last = data.items[data.items.length - 1];
    expect(last.score).toBe(1);
    expect(String(last.comment || '')).toContain('good');
  });
});
