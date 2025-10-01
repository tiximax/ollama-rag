import { test, expect } from '@playwright/test';

// Light UI test: chat CRUD flows using mocked endpoints and dialogs

test.describe('RAG e2e - Chat CRUD (UI light)', () => {
  test('Create, rename, delete chat via UI with mocked APIs', async ({ page }) => {
    const state = { chats: [] };

    await page.route('**/api/chats*', async (route) => {
      const req = route.request();
      const url = new URL(req.url());
      if (req.method() === 'GET' && url.pathname === '/api/chats') {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ db: 'default', chats: state.chats }) });
      }
      if (req.method() === 'POST' && url.pathname === '/api/chats') {
        const id = 'chat1';
        state.chats = [{ id, name: 'My Chat' }];
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ db: 'default', chat: { id, name: 'My Chat' } }) });
      }
      if (req.method() === 'PATCH' && url.pathname.startsWith('/api/chats/')) {
        const id = url.pathname.split('/').pop();
        const body = req.postDataJSON();
        state.chats = state.chats.map(c => c.id === id ? { ...c, name: body?.name || c.name } : c);
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ id, name: body?.name || 'Renamed' }) });
      }
      if (req.method() === 'DELETE' && url.pathname.startsWith('/api/chats/')) {
        const id = url.pathname.split('/').pop();
        state.chats = state.chats.filter(c => c.id !== id);
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ status: 'ok' }) });
      }
      return route.continue();
    });

    await page.goto('/');

    // Create: handle prompt
    page.once('dialog', async (d) => { await d.accept('My Chat'); });
    await page.locator('#btn-chat-new').click();
    await expect(page.locator('#chat-select')).toHaveValue('chat1');
    // Option text should reflect created name
    await expect(page.locator('#chat-select')).toContainText('My Chat');

    // Rename: handle prompt
    page.once('dialog', async (d) => { await d.accept('Renamed Chat'); });
    const patchDone = page.waitForRequest((r) => r.method() === 'PATCH' && r.url().includes('/api/chats/'));
    await page.locator('#btn-chat-rename').click();
    const patchReq = await patchDone;
    const patchBody = patchReq.postDataJSON();
    expect(patchBody && patchBody.name).toBe('Renamed Chat');
    // Optionally refresh list (not strictly required for body validation)
    await page.evaluate(async () => { if (typeof window.loadChats === 'function') { await window.loadChats(); } });

    // Delete: handle confirm and validate DELETE request
    page.once('dialog', async (d) => { await d.accept(); });
    const delReqP = page.waitForRequest((r) => r.method() === 'DELETE' && r.url().includes('/api/chats/'));
    await page.locator('#btn-chat-delete').click();
    const delReq = await delReqP;
    expect(delReq.url()).toMatch(/\/api\/chats\/chat1/);
  });
});
