import { test, expect } from '@playwright/test';

const resultSel = '#result';
const contextsSel = '#contexts .ctx';

test.describe('RAG e2e - Reranker @heavy', () => {
  test('Hybrid + Reranker (non-stream)', async ({ page }) => {
    await page.goto('/');

    // Ingest để đảm bảo có dữ liệu
    await page.getByRole('button', { name: 'Index tài liệu mẫu' }).click();
    await expect(page.locator(resultSel)).toContainText(/index/i, { timeout: 60000 });

    await page.selectOption('#method', 'hybrid');
    const streamCk = page.locator('#ck-stream');
    if (!(await streamCk.isChecked())) {
      await streamCk.check();
    }

    // Bật Reranker và đặt Top-N
    const rerankCk = page.locator('#ck-rerank');
    if (!(await rerankCk.isChecked())) {
      await rerankCk.check();
    }
    const topn = page.locator('#rerank-topn');
    await topn.fill('4');

    await page.fill('#txt-query', 'Bitsness là gì?');
    await page.fill('#top-k', '3');
    await page.getByRole('button', { name: 'Hỏi' }).click();

    await expect(page.locator(contextsSel).first()).toBeVisible({ timeout: 60000 });
    await expect(page.locator(resultSel)).not.toHaveText('', { timeout: 60000 });
  });

  test('Hybrid + Reranker (stream)', async ({ page }) => {
    await page.goto('/');

    await page.selectOption('#method', 'hybrid');
    const rerankCk = page.locator('#ck-rerank');
    if (!(await rerankCk.isChecked())) {
      await rerankCk.check();
    }
    const topn = page.locator('#rerank-topn');
    await topn.fill('8');

    // Bật streaming
    const streamCk = page.locator('#ck-stream');
    if (!(await streamCk.isChecked())) {
      await streamCk.check();
    }

    await page.fill('#txt-query', 'Luật giao thông yêu cầu gì?');
    await page.fill('#top-k', '3');
    await page.getByRole('button', { name: 'Hỏi' }).click();

    await expect(page.locator(contextsSel).first()).toBeVisible({ timeout: 60000 });
    await expect(page.locator(resultSel)).not.toHaveText('', { timeout: 60000 });
  });
});
