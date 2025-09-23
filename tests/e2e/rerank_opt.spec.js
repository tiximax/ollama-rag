import { test, expect } from '@playwright/test';

const resultSel = '#result';

async function ensureDb(page, name) {
  await page.fill('#db-new-name', name);
  await page.getByRole('button', { name: 'Tạo DB' }).click();
  await page.selectOption('#db-select', name).catch(() => {});
}

async function ingestSamples(page) {
  await page.getByRole('button', { name: 'Index tài liệu mẫu' }).click();
  await expect(page.locator(resultSel)).toContainText(/index|chunks/i, { timeout: 60000 });
}

test.describe('RAG e2e - Reranker optimize (B9b)', () => {
  test('Reranker embed provider với rr_max_k=4, batch=4, threads=1', async ({ page }) => {
    await page.goto('/');

    const db = 'rrdb';
    await ensureDb(page, db);
    await page.selectOption('#db-select', db);

    await ingestSamples(page);

    // hỏi BM25 non-stream + bật rerank (embed)
    await page.selectOption('#method', 'bm25');
    const streamCk = page.locator('#ck-stream');
    if (await streamCk.isChecked()) await streamCk.uncheck();

    const ckRerank = page.locator('#ck-rerank');
    if (!(await ckRerank.isChecked())) await ckRerank.check();

    await page.fill('#rerank-topn', '2');
    await page.selectOption('#rr-provider', 'embed');
    await page.fill('#rr-maxk', '4');
    await page.fill('#rr-batch', '4');
    await page.fill('#rr-threads', '1');

    await page.fill('#txt-query', 'Bitsness là gì?');
    await page.fill('#top-k', '2');
    await page.getByRole('button', { name: 'Hỏi' }).click();

    await expect(page.locator(resultSel)).not.toHaveText('', { timeout: 60000 });
  });
});
