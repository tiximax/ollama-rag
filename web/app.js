const ingestBtn = document.getElementById('btn-ingest');
const askBtn = document.getElementById('btn-ask');
const queryInput = document.getElementById('txt-query');
const topkInput = document.getElementById('top-k');
const streamCk = document.getElementById('ck-stream');
const resultDiv = document.getElementById('result');
const contextsDiv = document.getElementById('contexts');
const methodSel = document.getElementById('method');
const bm25Wrap = document.getElementById('bm25-weight-wrap');
const bm25Range = document.getElementById('bm25-weight');
const bm25Val = document.getElementById('bm25-weight-val');
const rerankCk = document.getElementById('ck-rerank');
const rerankTopWrap = document.getElementById('rerank-topn-wrap');
const rerankTopN = document.getElementById('rerank-topn');

async function ingest() {
  resultDiv.textContent = 'Đang index tài liệu...';
  try {
    const resp = await fetch('/api/ingest', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ paths: ['data/docs'] })
    });
    const data = await resp.json();
    if (resp.ok) {
      resultDiv.textContent = `Đã index ${data.chunks_indexed} chunks.`;
    } else {
      resultDiv.textContent = `Lỗi ingest: ${data.detail}`;
    }
  } catch (e) {
    resultDiv.textContent = `Lỗi kết nối server: ${e}`;
  }
}

async function ask() {
  const q = queryInput.value.trim();
  const k = parseInt(topkInput.value || '5', 10);
  const streaming = streamCk.checked;
  const method = methodSel.value || 'vector';
  const bm25_weight = parseFloat(bm25Range.value || '0.5');
  const rerank_enable = !!rerankCk.checked;
  const rerank_top_n = parseInt(rerankTopN.value || '10', 10);
  if (!q) {
    resultDiv.textContent = 'Vui lòng nhập câu hỏi';
    return;
  }
  resultDiv.textContent = 'Đang truy vấn...';
  contextsDiv.innerHTML = '';

  try {
    if (streaming) {
      await askStreaming(q, k, method, bm25_weight);
    } else {
      const resp = await fetch('/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: q, k, method, bm25_weight, rerank_enable, rerank_top_n })
      });
      const data = await resp.json();
      if (resp.ok) {
        resultDiv.textContent = data.answer || '(Không có trả lời)';
        const ctxs = data.contexts || [];
        if (ctxs.length) {
          const blocks = ctxs.map((c, i) => `<div class=\"ctx\"><strong>CTX ${i+1}</strong><pre>${escapeHtml(c)}</pre></div>`);
          contextsDiv.innerHTML = blocks.join('');
        }
      } else {
        resultDiv.textContent = `Lỗi truy vấn: ${data.detail}`;
      }
    }
  } catch (e) {
    resultDiv.textContent = `Lỗi kết nối server: ${e}`;
  }
}

async function askStreaming(q, k, method, bm25_weight) {
  const rerank_enable = !!rerankCk.checked;
  const rerank_top_n = parseInt(rerankTopN.value || '10', 10);
  const resp = await fetch('/api/stream_query', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query: q, k, method, bm25_weight, rerank_enable, rerank_top_n })
  });
  if (!resp.ok || !resp.body) {
    resultDiv.textContent = `Streaming thất bại: ${resp.status}`;
    return;
  }
  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let answer = '';
  let ctxHandled = false;
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    const chunk = decoder.decode(value, { stream: true });

    if (!ctxHandled) {
      // xử lý gói contexts đầu tiên theo định dạng [[CTXJSON]]{json}\n
      if (chunk.startsWith('[[CTXJSON]]')) {
        const idx = chunk.indexOf('\n');
        const header = chunk.substring(0, idx);
        const jsonStr = header.replace('[[CTXJSON]]', '');
        try {
          const obj = JSON.parse(jsonStr);
          const ctxs = obj.contexts || [];
          const blocks = ctxs.map((c, i) => `<div class="ctx"><strong>CTX ${i+1}</strong><pre>${escapeHtml(c)}</pre></div>`);
          contextsDiv.innerHTML = blocks.join('');
        } catch {}
        ctxHandled = true;
        const rest = chunk.substring(idx + 1);
        if (rest) {
          answer += rest;
          resultDiv.textContent = answer;
        }
        continue;
      }
    }

    answer += chunk;
    resultDiv.textContent = answer;
  }
}

function escapeHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

ingestBtn.addEventListener('click', ingest);
askBtn.addEventListener('click', ask);

methodSel.addEventListener('change', () => {
  const m = methodSel.value;
  const show = m === 'hybrid';
  bm25Wrap.style.display = show ? '' : 'none';
});

rerankCk.addEventListener('change', () => {
  rerankTopWrap.style.display = rerankCk.checked ? '' : 'none';
});

bm25Range.addEventListener('input', () => {
  bm25Val.textContent = bm25Range.value;
});
