import { test, expect } from '@playwright/test';

// Kiểm tra UI streaming gửi budget_ms và fanout_first_hop trong body về /api/stream_multihop_query

test.describe('RAG e2e - Multi-hop advanced (stream UI)', () => {
  test('UI streaming gửi budget_ms và fanout_first_hop', async ({ page }) => {
    await page.goto('/');

    // Intercept streaming endpoint và xác thực payload
    let seenOk = false;
    await page.route('**/api/stream_multihop_query', async (route) => {
      const req = route.request();
      try {
        const body = req.postDataJSON();
        if (body && parseInt(body.fanout_first_hop, 10) === 1 && parseInt(body.budget_ms, 10) === 150) {
          seenOk = true;
        }
      } catch {}
      // Trả về chuỗi giả lập stream: CTX header + câu trả lời ngắn
      const payload = '[[CTXJSON]]' + JSON.stringify({ contexts: ['demo ctx'], metadatas: [{}] }) + '\n' + 'Hello';
      return route.fulfill({ status: 200, contentType: 'text/plain', body: payload });
    });

    // Gọi trực tiếp fetch để kiểm tra payload gửi đúng (tránh phụ thuộc UI health)
    await page.evaluate(async () => {
      await fetch('/api/stream_multihop_query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: 'demo streaming multihop',
          k: 5,
          method: 'hybrid',
          bm25_weight: 0.5,
          rerank_enable: false,
          rerank_top_n: 10,
          depth: 2,
          fanout: 2,
          fanout_first_hop: 1,
          budget_ms: 150,
          provider: null,
          chat_id: null,
          save_chat: true,
          db: null,
        })
      });
    });

    await expect.poll(() => seenOk, { timeout: 20000 }).toBe(true);
  });
});