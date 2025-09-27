import { test, expect } from '@playwright/test';

// Light UI test: chat exports (json/md) and DB exports (zip), mocked

test.describe('RAG e2e - Chat exports (UI light)', () => {
  test('Export chat json/md and DB json/md', async ({ page }) => {
    // Mock chats list (GET) and chat create (POST) — đăng ký trước khi load trang
    await page.route('**/api/chats*', async (route) => {
      const req = route.request();
      if (req.method() === 'GET') {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ db: 'default', chats: [{ id: 'e2e-chat', name: 'E2E Chat' }] }) });
      }
      if (req.method() === 'POST') {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ db: 'default', chat: { id: 'e2e-chat', name: 'E2E Chat' } }) });
      }
      return route.continue();
    });

    await page.goto('/?e2e=1');
    await page.waitForFunction(() => window.__E2E_READY__ === true);

    // Create chat via UI
    await page.locator('#btn-chat-new').click();
    await expect(page.locator('#chat-select')).toHaveValue('e2e-chat');

    // Mock chat export (json)
    await page.route('**/api/chats/*/export?*', async (route) => {
      const url = route.request().url();
      const u = new URL(url);
      const fmt = u.searchParams.get('format');
      if (fmt === 'json') {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ id: 'e2e-chat', messages: [] }) });
      } else {
        return route.fulfill({ status: 200, contentType: 'text/markdown', body: '# Chat\n' });
      }
    });

    // Export JSON
    const respJsonPromise = page.waitForResponse((r) => r.url().includes('/api/chats/') && r.url().includes('/export?') && r.request().method() === 'GET');
    await page.locator('#btn-chat-export-json').click();
    const respJson = await respJsonPromise;
    expect(respJson.ok()).toBeTruthy();
    const json = await respJson.json();
    expect(json.id).toBe('e2e-chat');

    // Export Markdown
    const respMdPromise = page.waitForResponse((r) => r.url().includes('/api/chats/') && r.url().includes('/export?') && r.request().method() === 'GET');
    await page.locator('#btn-chat-export-md').click();
    const respMd = await respMdPromise;
    expect(respMd.ok()).toBeTruthy();
    const md = await respMd.text();
    expect(md).toContain('# Chat');

    // Mock DB export (zip)
    await page.route('**/api/chats/export_db?*', async (route) => {
      const u = new URL(route.request().url());
      const fmt = u.searchParams.get('format');
      // Return fake zip bytes
      const body = Buffer.from('PK');
      return route.fulfill({ status: 200, headers: { 'Content-Type': 'application/zip' }, body });
    });

    // Export DB JSON
    const respDbJsonP = page.waitForResponse((r) => r.url().includes('/api/chats/export_db?') && r.request().method() === 'GET');
    await page.locator('#btn-chat-export-db-json').click();
    const respDbJson = await respDbJsonP;
    expect(respDbJson.ok()).toBeTruthy();
    expect((respDbJson.headers()['content-type'] || '').toLowerCase()).toContain('application/zip');

    // Export DB MD
    const respDbMdP = page.waitForResponse((r) => r.url().includes('/api/chats/export_db?') && r.request().method() === 'GET');
    await page.locator('#btn-chat-export-db-md').click();
    const respDbMd = await respDbMdP;
    expect(respDbMd.ok()).toBeTruthy();
    expect((respDbMd.headers()['content-type'] || '').toLowerCase()).toContain('application/zip');
  });
});
