import { test, expect } from '@playwright/test';

// Upload + ingest e2e: tạo DB, upload 1 file .txt trong bộ nhớ, xác nhận index xong, stream hỏi và hiển thị contexts

test.describe('RAG e2e - Upload & Ingest (B15)', () => {
  test('Upload file .txt và hỏi (stream) hiển thị contexts', async ({ page }) => {
    await page.goto('/');

    const db = 'upldb';
    await page.fill('#db-new-name', db);
    await page.getByRole('button', { name: 'Tạo DB' }).click();
    await page.selectOption('#db-select', db).catch(() => {});

    // tạo 1 file trong bộ nhớ
    const content = 'E2E_UPLOAD_MARKER_12345 This is an uploaded doc for e2e test.';
    const filePayload = {
      name: 'e2e_upload.txt',
      mimeType: 'text/plain',
      buffer: Buffer.from(content, 'utf-8'),
    };

    // set files và upload
    const up = page.locator('#file-upload');
    await up.setInputFiles([filePayload]);
    const filesCount = await page.evaluate(() => {
      const el = document.getElementById('file-upload');
      return (el && el.files && el.files.length) ? el.files.length : 0;
    });
    expect(filesCount).toBeGreaterThan(0);
    await page.locator('#btn-upload').click();
    // Chờ response upload để xác nhận thực tế
    const resp = await page.waitForResponse(r => r.url().includes('/api/upload') && r.request().method() === 'POST', { timeout: 60000 });
    expect(resp.ok()).toBeTruthy();
    const data = await resp.json();
    expect(Array.isArray(data.saved) && data.saved.length > 0).toBeTruthy();

    // hỏi bằng stream để hiển thị contexts
    await page.selectOption('#method', 'bm25');
    const streamCk = page.locator('#ck-stream');
    if (!(await streamCk.isChecked())) await streamCk.check();

    await page.fill('#txt-query', 'E2E_UPLOAD_MARKER_12345');
    await page.fill('#top-k', '1');
    await page.getByRole('button', { name: 'Hỏi' }).click();

    await expect(page.locator('#contexts .ctx').first()).toBeVisible({ timeout: 60000 });
  });
});
