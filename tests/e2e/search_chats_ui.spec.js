import { test, expect } from '@playwright/test';

// Light UI test: search chats with mocked /api/chats/search

test.describe('RAG e2e - Search chats (UI light)', () => {
  test('Search renders count in result panel', async ({ page }) => {
    await page.route('**/api/chats/search*', async (route) => {
      const payload = { db: 'default', results: [{ id: 'a' }, { id: 'b' }] };
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(payload) });
    });

    await page.goto('/');

    await page.fill('#chat-search', 'hello');
    const respP = page.waitForResponse((r) => r.url().includes('/api/chats/search?') && r.request().method() === 'GET');
    await page.locator('#btn-chat-search').click();
    await respP;

    await expect(page.locator('#result')).toContainText("Search 'hello': 2 chats có kết quả.");
  });
});
