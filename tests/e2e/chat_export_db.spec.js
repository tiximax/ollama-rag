import { test, expect } from '@playwright/test';

// Export toàn bộ chats của DB (ZIP) — light

test.describe('RAG e2e - Chat export DB (light)', () => {
  test('Export DB JSON/MD returns a ZIP', async ({ page }) => {
    await page.goto('/?e2e=1');
    await page.waitForFunction(() => window.__E2E_READY__ === true);

    // Tạo chat và ingest + hỏi nhanh để có dữ liệu ít nhất 1 file
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

    // Export JSON
    const resJson = await page.evaluate(async () => {
      const res = await fetch('/api/chats/export_db?format=json');
      return { ok: res.ok, ct: res.headers.get('content-type'), len: (await res.arrayBuffer()).byteLength };
    });
    expect(resJson.ok).toBeTruthy();
    expect((resJson.ct || '').includes('application/zip')).toBeTruthy();
    expect(resJson.len).toBeGreaterThan(0);

    // Export MD
    const resMd = await page.evaluate(async () => {
      const res = await fetch('/api/chats/export_db?format=md');
      return { ok: res.ok, ct: res.headers.get('content-type'), len: (await res.arrayBuffer()).byteLength };
    });
    expect(resMd.ok).toBeTruthy();
    expect((resMd.ct || '').includes('application/zip')).toBeTruthy();
    expect(resMd.len).toBeGreaterThan(0);
  });
});
