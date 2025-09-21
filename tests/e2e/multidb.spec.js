import { test, expect } from '@playwright/test';

const resultSel = '#result';
const contextsSel = '#contexts .ctx';

async function ensureDb(page, name) {
  // tạo DB nếu chưa có và switch sang DB đó
  await page.fill('#db-new-name', name);
  await page.getByRole('button', { name: 'Tạo DB' }).click();
  // có thể trùng, nên nếu 409 server trả về alert; bỏ qua
  await page.selectOption('#db-select', name).catch(() => {});
}

async function switchDb(page, name) {
  await page.selectOption('#db-select', name);
}

test.describe('RAG e2e - MultiDB', () => {
  test('DB1 có dữ liệu, DB2 trống, chuyển qua lại hoạt động', async ({ page }) => {
    await page.goto('/');

    // Tạo và chuyển sang db1
    await ensureDb(page, 'db1');
    await switchDb(page, 'db1');

    // ingest trong db1
    await page.getByRole('button', { name: 'Index tài liệu mẫu' }).click();
    await expect(page.locator(resultSel)).toContainText(/index/i, { timeout: 60000 });

    // hỏi trong db1 -> có contexts
    await page.fill('#txt-query', 'Bitsness là gì?');
    await page.fill('#top-k', '3');
    await page.selectOption('#method', 'bm25');
    const streamCk = page.locator('#ck-stream');
    if (!(await streamCk.isChecked())) await streamCk.check();
    await page.getByRole('button', { name: 'Hỏi' }).click();
    await expect(page.locator(contextsSel).first()).toBeVisible({ timeout: 60000 });

    // Tạo và chuyển sang db2 (không ingest)
    await ensureDb(page, 'db2');
    await switchDb(page, 'db2');

    // hỏi trong db2 -> không có contexts
    await page.fill('#txt-query', 'Bitsness là gì?');
    await page.fill('#top-k', '3');
    await page.selectOption('#method', 'bm25');
    await page.getByRole('button', { name: 'Hỏi' }).click();
    await expect(page.locator(contextsSel)).toHaveCount(0, { timeout: 10000 });

    // quay lại db1 -> có contexts
    await switchDb(page, 'db1');
    await page.fill('#txt-query', 'Luật giao thông yêu cầu gì?');
    await page.selectOption('#method', 'bm25');
    await page.getByRole('button', { name: 'Hỏi' }).click();
    await expect(page.locator(contextsSel).first()).toBeVisible({ timeout: 60000 });
  });
});
