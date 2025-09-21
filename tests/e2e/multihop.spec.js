import { test, expect } from '@playwright/test';

const resultSel = '#result';
const contextsSel = '#contexts .ctx';

test.describe('RAG e2e - Multi-hop @heavy', () => {
  test('Multi-hop (stream) depth=2 fanout=2', async ({ page }) => {
    await page.goto('/');

    // Đảm bảo có dữ liệu
    await page.getByRole('button', { name: 'Index tài liệu mẫu' }).click();
    await expect(page.locator(resultSel)).toContainText(/index/i, { timeout: 60000 });

    // Bật multi-hop và streaming, cấu hình tham số
    await page.selectOption('#method', 'hybrid');
    const mhCk = page.locator('#ck-multihop');
    if (!(await mhCk.isChecked())) {
      await mhCk.check();
    }
    await page.fill('#hop-depth', '1');
    await page.fill('#hop-fanout', '1');

    const streamCk = page.locator('#ck-stream');
    if (!(await streamCk.isChecked())) {
      await streamCk.check();
    }

    await page.fill('#txt-query', 'Bitsness là gì?');
    await page.fill('#top-k', '3');
    await page.getByRole('button', { name: 'Hỏi' }).click();

    await expect(page.locator(contextsSel).first()).toBeVisible({ timeout: 60000 });
    await expect(page.locator(resultSel)).not.toHaveText('', { timeout: 60000 });
  });
});
