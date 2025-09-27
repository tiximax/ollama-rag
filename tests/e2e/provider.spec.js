import { test, expect } from '@playwright/test';

// Provider API and UI tests (light): verify GET/POST and UI label updates

test.describe('RAG e2e - Provider switch (light)', () => {
  test('API: GET and POST /api/provider toggles value', async ({ page }) => {
    await page.goto('/?e2e=1');

    // Read current provider
    const cur = await page.evaluate(async () => {
      const r = await fetch('/api/provider');
      const j = await r.json();
      return j.provider;
    });
    expect(cur === 'ollama' || cur === 'openai').toBeTruthy();

    // Toggle provider to the other value
    const target = cur === 'ollama' ? 'openai' : 'ollama';
    const res = await page.evaluate(async (name) => {
      const r = await fetch('/api/provider', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name }) });
      return await r.json();
    }, target);

    expect(res.provider).toBe(target);

    // Verify GET
    const after = await page.evaluate(async () => {
      const r = await fetch('/api/provider');
      const j = await r.json();
      return j.provider;
    });
    expect(after).toBe(target);

    // Revert to original provider
    await page.evaluate(async (name) => {
      await fetch('/api/provider', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name }) });
    }, cur);
  });

  test('UI: changing dropdown updates footer label', async ({ page }) => {
    await page.goto('/?e2e=1');
    await page.waitForFunction(() => window.__E2E_READY__ === true);

    // Ensure current shows in footer
    const footerLabel = page.locator('#provider-name');
    const initial = await footerLabel.textContent();
    expect(initial === 'ollama' || initial === 'openai').toBeTruthy();

    // Switch via dropdown
    const target = initial === 'ollama' ? 'openai' : 'ollama';
    await page.selectOption('#provider-select', target);

    // Footer label should reflect the change
    await expect(footerLabel).toHaveText(target);

    // Switch back
    await page.selectOption('#provider-select', initial);
    await expect(footerLabel).toHaveText(initial);
  });
});
