import { test, expect } from '@playwright/test';

const resultSel = '#result';

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

function datasetJSON(dbName) {
  return JSON.stringify({
    k: 5,
    method: 'bm25',
    db: dbName,
    queries: [
      { query: 'What does the Highway Code require?', expected_sources: ['en_traffic_sample.txt'], expected_substrings: ['Highway Code'], versions: ['en1'] },
      { query: 'Luật giao thông yêu cầu gì?', expected_sources: ['traffic_law_sample.txt'], expected_substrings: ['Giao thông'], versions: ['vi1'] }
    ]
  }, null, 2);
}

test.describe('RAG e2e - Offline Eval (B7)', () => {
  test('Eval offline (bm25) đạt recall@k = 1.0', async ({ page }) => {
    await page.goto('/?e2e=1');
    await page.waitForFunction(() => window.__E2E_READY__ === true);

    const db = 'evaldb';
    await ensureDb(page, db);
    await page.selectOption('#db-select', db);

    // ingest dữ liệu mẫu với version
    await ingestOne(page, 'data/docs/traffic_law_sample.txt', 'vi1');
    await ingestOne(page, 'data/docs/en_traffic_sample.txt', 'en1');

    // nhập dataset và chạy eval
    await page.fill('#eval-json', datasetJSON(db));
    await page.getByRole('button', { name: 'Run Eval' }).click();

    // kết quả
    const evalDiv = page.locator('#eval-result');
    await expect(evalDiv).toContainText(/Recall@k: 1|1.00|1.0/);
    await expect(evalDiv).toContainText('(2/2)');
  });
});
