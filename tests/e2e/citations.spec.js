import { test, expect } from '@playwright/test';

// Kiểm tra UI render citations dựa trên markers [n] trong answer
// Không phụ thuộc mô hình: mock /api/query để trả về dữ liệu cố định

test.describe('RAG e2e - Citations (UI)', () => {
  test('Render citations từ answer [n] (non-stream, mocked)', async ({ page }) => {
    await page.goto('/?e2e=1');

    // Tắt streaming để đi qua đường /api/query
    const streamCk = page.locator('#ck-stream');
    if (await streamCk.isChecked()) await streamCk.uncheck();

    // Intercept /api/query và trả về JSON chứa answer + metas
    await page.route('**/api/query', async (route) => {
      const json = {
        answer: 'Demo trả lời có trích dẫn [1].',
        contexts: ['Đây là đoạn ngữ cảnh mẫu.'],
        metadatas: [{ source: 'mock.txt', chunk: 0 }],
      };
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(json),
      });
    });

    await page.fill('#txt-query', 'câu hỏi demo');
    await page.fill('#top-k', '1');
    await page.getByRole('button', { name: 'Hỏi' }).click();

    // Kết quả có text
    await expect(page.locator('#result')).toContainText(/Demo trả lời/);

    // Citations panel có ít nhất 1 mục, hiển thị [1] và nguồn mock.txt
    await expect(page.locator('#citations .citation')).toHaveCount(1, { timeout: 10000 });
    await expect(page.locator('#citations')).toContainText(/\[1\]/);
    await expect(page.locator('#citations')).toContainText(/mock\.txt/);
  });
});
