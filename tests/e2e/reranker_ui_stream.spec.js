import { test, expect } from '@playwright/test';

// Light UI test: verify reranker advanced options are sent on streaming requests to /api/stream_query

test.describe('RAG e2e - Reranker (UI stream light)', () => {
  test('UI sends rerank_enable/top_n and rr_* options (stream, mocked)', async ({ page }) => {
    await page.goto('/?e2e=1');
    await page.waitForFunction(() => window.__E2E_READY__ === true);

    // Ensure streaming mode
    const streamCk = page.locator('#ck-stream');
    if (!(await streamCk.isChecked())) await streamCk.check();

    // Select method and enable reranker + advanced options
    await page.selectOption('#method', 'bm25');
    const ckRerank = page.locator('#ck-rerank');
    if (!(await ckRerank.isChecked())) await ckRerank.check();
    await page.fill('#rerank-topn', '4');
    await page.selectOption('#rr-provider', 'embed');
    await page.fill('#rr-maxk', '4');
    await page.fill('#rr-batch', '4');
    await page.fill('#rr-threads', '1');

    // Intercept /api/stream_query and validate payload
    await page.route('**/api/stream_query', async (route) => {
      const req = route.request();
      let ok = false;
      try {
        const body = req.postDataJSON();
        ok = !!body && body.rerank_enable === true && parseInt(body.rerank_top_n, 10) === 4
          && body.rr_provider === 'embed'
          && parseInt(body.rr_max_k, 10) === 4
          && parseInt(body.rr_batch_size, 10) === 4
          && parseInt(body.rr_num_threads, 10) === 1;
      } catch {}
      const header = '[[CTXJSON]]' + JSON.stringify({ contexts: [], metadatas: [] }) + '\n';
      if (!ok) {
        return route.fulfill({ status: 200, contentType: 'text/plain', body: header + 'bad' });
      }
      return route.fulfill({ status: 200, contentType: 'text/plain', body: header + 'ok' });
    });

    await page.fill('#txt-query', 'demo rerank');
    await page.fill('#top-k', '2');
    await page.getByRole('button', { name: 'Hỏi' }).click();

    await expect(page.locator('#result')).toContainText('ok');
  });
});
