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

test.describe('RAG e2e - Logs (B9a)', () => {
  test('Bật logs, hỏi, export JSONL có query/method/contexts_sources', async ({ page }) => {
    await page.goto('/');

    const db = 'logsdb';
    await ensureDb(page, db);
    await page.selectOption('#db-select', db);

    await ingestSamples(page);

    // bật logs (đảm bảo server đã nhận)
    await page.evaluate(async () => {
      await fetch('/api/logs/enable', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ db: 'logsdb', enabled: true })
      });
    });
    // xác nhận
    const info = await page.evaluate(async () => {
      const resp = await fetch('/api/logs/info?db=logsdb');
      return resp.json();
    });
    expect(info.enabled).toBeTruthy();

    // Gọi trực tiếp /api/stream_query để đảm bảo kết thúc stream và có log
    await page.evaluate(async () => {
      const payload = { query: 'Bitsness là gì?', k: 2, method: 'bm25', bm25_weight: 0.5, rerank_enable: false, rerank_top_n: 10, db: 'logsdb' };
      const resp = await fetch('/api/stream_query', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
      });
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      // Đọc đến khi nhận header [[CTXJSON]] là đủ (đã log sớm)
      // eslint-disable-next-line no-constant-condition
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        if (buffer.indexOf('[[CTXJSON]]') >= 0) {
          try { await reader.cancel(); } catch {}
          break;
        }
      }
    });

    // export logs bằng API và parse JSONL
    const data = await page.evaluate(async () => {
      const params = new URLSearchParams();
      params.set('db', 'logsdb');
      const resp = await fetch('/api/logs/export?' + params.toString());
      const text = await resp.text();
      return text.split('\n').filter(Boolean).map(line => { try { return JSON.parse(line); } catch { return null; } }).filter(Boolean);
    });

    expect(Array.isArray(data)).toBeTruthy();
    expect(data.length).toBeGreaterThan(0);
    const has = data.some(e => e && e.route === '/api/stream_query' && e.method === 'bm25' && String(e.query || '').includes('Bitsness'));
    expect(has).toBeTruthy();
    const any = data.find(e => e && e.route === '/api/stream_query');
    expect(Array.isArray(any.contexts_sources)).toBeTruthy();
  });
});
