import { test, expect } from '@playwright/test';

const resultSel = '#result';
const contextsSel = '#contexts .ctx';

test.describe('RAG e2e - Hybrid', () => {
  test('Hybrid (non-stream) với trọng số BM25', async ({ page }) => {
    await page.goto('/');

    // đảm bảo đã có dữ liệu
    await page.getByRole('button', { name: 'Index tài liệu mẫu' }).click();
    await expect(page.locator(resultSel)).toContainText(/index/i, { timeout: 60000 });

    // chọn hybrid và đặt weight
    await page.selectOption('#method', 'hybrid');
    await page.fill('#txt-query', 'Bitsness là gì?');
    await page.fill('#top-k', '3');

    // tắt streaming để dùng /api/query
    const streamCk = page.locator('#ck-stream');
    if (await streamCk.isChecked()) {
      await streamCk.uncheck();
    }

    // chỉnh weight (nếu hiện)
    const weightSlider = page.locator('#bm25-weight');
    if (await weightSlider.isVisible()) {
      await weightSlider.fill('0.6');
    }

    await page.getByRole('button', { name: 'Hỏi' }).click();

    await expect(page.locator(resultSel)).not.toHaveText('', { timeout: 60000 });
    await expect(page.locator(contextsSel).first()).toBeVisible({ timeout: 60000 });
  });
});
