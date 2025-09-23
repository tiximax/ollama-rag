import { test, expect } from '@playwright/test';

const resultSel = '#result';
const contextsSel = '#contexts .ctx';

async function ensureDb(page, name) {
  await page.fill('#db-new-name', name);
  await page.getByRole('button', { name: 'Tạo DB' }).click();
  await page.selectOption('#db-select', name).catch(() => {});
}

async function ingestOne(page, paths, version) {
  if (version) {
    await page.fill('#ingest-version', version);
  }
  await page.fill('#ingest-paths', paths);
  await page.getByRole('button', { name: 'Ingest Paths' }).click();
  await expect(page.locator(resultSel)).toContainText(/Đã index|đã index|chunks/i, { timeout: 60000 });
}

async function selectMulti(page, selector, values) {
  await page.selectOption(selector, values);
}

test.describe('RAG e2e - Filters (language/version)', () => {
  test('Filter by language and version (bm25, streaming)', async ({ page }) => {
    await page.goto('/');

    // Isolate DB for test
    await ensureDb(page, 'filtersdb');
    await page.selectOption('#db-select', 'filtersdb');

    // Ingest Vietnamese traffic law as vi1
    await ingestOne(page, 'data/docs/traffic_law_sample.txt', 'vi1');
    // Ingest English highway code as en1
    await ingestOne(page, 'data/docs/en_traffic_sample.txt', 'en1');

    // Wait filters present
    await expect(page.locator('#filter-langs')).toBeVisible();

    // --- English query with version filter 'en1' ---
    await expect(page.locator('#filter-versions')).toBeVisible({ timeout: 60000 });
    await expect(page.locator('#filter-versions option[value="en1"]').first()).toBeVisible({ timeout: 60000 });
    await selectMulti(page, '#filter-versions', ['en1']);
    await page.selectOption('#method', 'bm25');
    const streamCk = page.locator('#ck-stream');
    if (!(await streamCk.isChecked())) await streamCk.check();

    await page.fill('#txt-query', 'What does the Highway Code require?');
    await page.fill('#top-k', '2');
    await page.getByRole('button', { name: 'Hỏi' }).click();

    await expect(page.locator(resultSel)).not.toHaveText('', { timeout: 60000 });
    await expect(page.locator(contextsSel).first()).toBeVisible({ timeout: 60000 });
    await expect(page.locator(contextsSel).first()).toContainText(/Highway Code/i);

    // --- Vietnamese query with version filter 'vi1' ---
    await selectMulti(page, '#filter-versions', ['vi1']);
    await page.fill('#txt-query', 'Luật giao thông yêu cầu gì?');
    await page.getByRole('button', { name: 'Hỏi' }).click();
    await expect(page.locator(contextsSel).first()).toBeVisible({ timeout: 60000 });
    await expect(page.locator(contextsSel).first()).toContainText(/Giao thông|Điều/i);
  });
});
