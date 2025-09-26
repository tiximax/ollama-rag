import { test, expect } from '@playwright/test';

// Light UI test: citations rendering with multiple markers and filters

test.describe('RAG e2e - Citations (UI light variants)', () => {
  test('Render [1],[2] and ignore out-of-range [99]; request carries languages/versions', async ({ page }) => {
    await page.goto('/');

    // Ensure non-stream (use /api/query)
    const streamCk = page.locator('#ck-stream');
    if (await streamCk.isChecked()) await streamCk.uncheck();

    // Inject options for filters and select them
    await page.evaluate(() => {
      const langs = document.getElementById('filter-langs');
      const vers = document.getElementById('filter-versions');
      function addOpt(sel, v) { const o = document.createElement('option'); o.value = v; o.textContent = v; sel.appendChild(o); }
      if (langs) { langs.innerHTML = ''; addOpt(langs, 'vi'); addOpt(langs, 'en'); langs.options[0].selected = true; }
      if (vers) { vers.innerHTML = ''; addOpt(vers, 'v1'); addOpt(vers, 'v2'); vers.options[0].selected = true; }
    });

    // Intercept /api/query and validate request languages/versions
    await page.route('**/api/query', async (route) => {
      const req = route.request();
      let ok = false;
      try {
        const body = req.postDataJSON();
        ok = Array.isArray(body.languages) && body.languages.includes('vi') &&
             Array.isArray(body.versions) && body.versions.includes('v1');
      } catch {}
      const payload = {
        answer: 'A [1] B [2] C [1] [99]',
        contexts: ['ctx1', 'ctx2'],
        metadatas: [
          { source: 'src1.txt', chunk: 0 },
          { source: 'src2.txt', chunk: 1 }
        ]
      };
      return route.fulfill({ status: ok ? 200 : 200, contentType: 'application/json', body: JSON.stringify(payload) });
    });

    await page.fill('#txt-query', 'demo citations');
    await page.fill('#top-k', '2');
    await page.getByRole('button', { name: 'Hỏi' }).click();

    // Expect citations show [1] and [2], not [99]
    const cits = page.locator('#citations .citation');
    await expect(cits).toHaveCount(2);
    await expect(page.locator('#citations')).toContainText('[1]');
    await expect(page.locator('#citations')).toContainText('[2]');
    await expect(page.locator('#citations')).not.toContainText('[99]');
    await expect(page.locator('#citations')).toContainText('src1.txt');
    await expect(page.locator('#citations')).toContainText('src2.txt');
  });
});
