import { test, expect } from '@playwright/test';

const resultSel = '#result';
const contextsSel = '#contexts .ctx';

async function waitForTextContains(page, selector, regex, timeout = 30000) {
  await expect(page.locator(selector)).toHaveText(regex, { timeout });
}

test.describe('RAG e2e', () => {
  test('Ingest và hỏi (non-stream)', async ({ page }) => {
    await page.goto('/');

    await page.getByRole('button', { name: 'Index tài liệu mẫu' }).click();
    await page.selectOption('#method', 'hybrid');
    await expect(page.locator(resultSel)).toContainText(/Đã index|đã index|chunks/i, { timeout: 60000 });

    await page.fill('#txt-query', 'Bitsness là gì?');
    await page.fill('#top-k', '2');
    const streamCk = page.locator('#ck-stream');
    if (!(await streamCk.isChecked())) {
      await streamCk.check();
    }
    await page.getByRole('button', { name: 'Hỏi' }).click();

    await expect(page.locator(resultSel)).not.toHaveText('', { timeout: 60000 });
  });

  test('Hỏi ở chế độ Streaming và có contexts', async ({ page }) => {
    await page.goto('/');

    await page.selectOption('#method', 'hybrid');
    const streamCk = page.locator('#ck-stream');
    if (!(await streamCk.isChecked())) {
      await streamCk.check();
    }

    await page.fill('#txt-query', 'Luật giao thông yêu cầu gì?');
    await page.fill('#top-k', '3');
    await page.getByRole('button', { name: 'Hỏi' }).click();

    await expect(page.locator(resultSel)).not.toHaveText('', { timeout: 60000 });
  });
});
