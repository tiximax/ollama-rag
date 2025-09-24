import { test, expect } from '@playwright/test';

// Light UI test: feedback sending flow with mocked stream_query and feedback endpoints

test.describe('RAG e2e - Feedback (UI light)', () => {
  test('Thumbs up + send posts feedback with sources', async ({ page }) => {
    await page.goto('/');

    // Ensure streaming mode
    const streamCk = page.locator('#ck-stream');
    if (!(await streamCk.isChecked())) await streamCk.check();

    // Mock stream_query to set contexts header and allow gLastMetas to be populated
    await page.route('**/api/stream_query', async (route) => {
      const header = '[[CTXJSON]]' + JSON.stringify({ contexts: ['ctx'], metadatas: [{ source: 'mock.txt', chunk: 0 }] }) + '\n';
      return route.fulfill({ status: 200, contentType: 'text/plain', body: header + 'ok answer' });
    });

    // Ask once to set last answer/metas
    await page.fill('#txt-query', 'feedback demo');
    await page.fill('#top-k', '1');
    await page.getByRole('button', { name: 'Hỏi' }).click();
    await expect(page.locator('#result')).toContainText('ok answer');

    // Click thumbs up and type a comment
    await page.locator('#btn-fb-up').click();
    await page.fill('#fb-comment', 'Great');

    // Intercept feedback POST and validate payload
    const feedbackP = page.waitForRequest((r) => r.url().includes('/api/feedback') && r.method() === 'POST');
    await page.locator('#btn-fb-send').click();
    const fbReq = await feedbackP;
    const body = fbReq.postDataJSON();
    expect(body.score).toBe(1);
    expect(Array.isArray(body.sources)).toBeTruthy();
    expect(body.sources.some((s) => String(s || '').includes('mock.txt'))).toBeTruthy();
  });
});
