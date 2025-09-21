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
const dbSelect = document.getElementById('db-select');
const dbNewName = document.getElementById('db-new-name');
const dbCreateBtn = document.getElementById('btn-db-create');
const dbDeleteBtn = document.getElementById('btn-db-delete');
const chatSelect = document.getElementById('chat-select');
const chatNewBtn = document.getElementById('btn-chat-new');
const chatRenameBtn = document.getElementById('btn-chat-rename');
const chatDeleteBtn = document.getElementById('btn-chat-delete');
const saveChatCk = document.getElementById('ck-save-chat');
const multihopCk = document.getElementById('ck-multihop');
const multihopDepthWrap = document.getElementById('multihop-depth-wrap');
const multihopFanoutWrap = document.getElementById('multihop-fanout-wrap');
const hopDepth = document.getElementById('hop-depth');
const hopFanout = document.getElementById('hop-fanout');

async function loadDbs() {
  try {
    const resp = await fetch('/api/dbs');
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || 'Không tải được DBs');
    const { current, dbs } = data;
    dbSelect.innerHTML = '';
    (dbs || []).forEach(name => {
      const opt = document.createElement('option');
      opt.value = name;
      opt.textContent = name;
      if (name === current) opt.selected = true;
      dbSelect.appendChild(opt);
    });
  } catch (e) {
    console.error('loadDbs error', e);
  }
}

async function useDb(name) {
  try {
    const resp = await fetch('/api/dbs/use', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name })
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || 'Không thể đổi DB');
    await loadDbs();
  } catch (e) {
    alert('Lỗi đổi DB: ' + e);
  }
}

async function createDb() {
  const name = (dbNewName.value || '').trim();
  if (!name) {
    alert('Nhập tên DB mới');
    return;
  }
  try {
    const resp = await fetch('/api/dbs/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name })
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || 'Không thể tạo DB');
    dbNewName.value = '';
    await loadDbs();
    dbSelect.value = name;
    await useDb(name);
  } catch (e) {
    alert('Lỗi tạo DB: ' + e);
  }
}

async function deleteDb() {
  const name = dbSelect.value;
  if (!name) return;
  try {
    const resp = await fetch('/api/dbs/' + encodeURIComponent(name), { method: 'DELETE' });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || 'Không thể xóa DB');
    await loadDbs();
  } catch (e) {
    alert('Lỗi xóa DB: ' + e);
  }
}

async function loadChats() {
  try {
    const params = new URLSearchParams();
    if (dbSelect.value) params.set('db', dbSelect.value);
    const resp = await fetch('/api/chats?' + params.toString());
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || 'Không tải được chats');
    const { chats } = data;
    const prev = chatSelect.value;
    chatSelect.innerHTML = '';
    (chats || []).forEach(c => {
      const opt = document.createElement('option');
      opt.value = c.id;
      opt.textContent = c.name || c.id;
      chatSelect.appendChild(opt);
    });
    // giữ nguyên lựa chọn cũ nếu còn
    if (prev && [...chatSelect.options].some(o => o.value === prev)) {
      chatSelect.value = prev;
    }
  } catch (e) {
    console.error('loadChats error', e);
  }
}

async function createChat() {
  try {
    const name = prompt('Tên chat mới:', 'New Chat') || undefined;
    const resp = await fetch('/api/chats', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ db: dbSelect.value || null, name })
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || 'Không tạo được chat');
    await loadChats();
    if (data.chat && data.chat.id) {
      chatSelect.value = data.chat.id;
    }
  } catch (e) {
    alert('Lỗi tạo chat: ' + e);
  }
}

async function renameChat() {
  const id = chatSelect.value;
  if (!id) return;
  const name = prompt('Tên mới:', '') || '';
  if (!name.trim()) return;
  try {
    const params = new URLSearchParams();
    if (dbSelect.value) params.set('db', dbSelect.value);
    const resp = await fetch(`/api/chats/${encodeURIComponent(id)}?${params.toString()}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name })
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || 'Không đổi tên được chat');
    await loadChats();
    chatSelect.value = id;
  } catch (e) {
    alert('Lỗi rename chat: ' + e);
  }
}

async function deleteChat() {
  const id = chatSelect.value;
  if (!id) return;
  if (!confirm('Xóa chat này?')) return;
  try {
    const params = new URLSearchParams();
    if (dbSelect.value) params.set('db', dbSelect.value);
    const resp = await fetch(`/api/chats/${encodeURIComponent(id)}?${params.toString()}`, { method: 'DELETE' });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || 'Không xóa được chat');
    await loadChats();
  } catch (e) {
    alert('Lỗi xóa chat: ' + e);
  }
}

async function ingest() {
  resultDiv.textContent = 'Đang index tài liệu...';
  try {
    const resp = await fetch('/api/ingest', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ paths: ['data/docs'], db: dbSelect.value || null })
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
    const chat_id = chatSelect.value || null;
    const save_chat = !!saveChatCk.checked;
    if (streaming) {
      if (multihopCk.checked) {
        await askStreamingMH(q, k, method, bm25_weight, chat_id, save_chat);
      } else {
        await askStreaming(q, k, method, bm25_weight, chat_id, save_chat);
      }
    } else {
      if (multihopCk.checked) {
        const resp = await fetch('/api/multihop_query', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query: q, k, method, bm25_weight, rerank_enable, rerank_top_n, depth: parseInt(hopDepth.value||'2',10), fanout: parseInt(hopFanout.value||'2',10), chat_id, save_chat, db: dbSelect.value || null })
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
      } else {
        const resp = await fetch('/api/query', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query: q, k, method, bm25_weight, rerank_enable, rerank_top_n, chat_id, save_chat, db: dbSelect.value || null })
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
    }
  } catch (e) {
    resultDiv.textContent = `Lỗi kết nối server: ${e}`;
  }
}

async function askStreaming(q, k, method, bm25_weight, chat_id, save_chat) {
  const rerank_enable = !!rerankCk.checked;
  const rerank_top_n = parseInt(rerankTopN.value || '10', 10);
  const resp = await fetch('/api/stream_query', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query: q, k, method, bm25_weight, rerank_enable, rerank_top_n, chat_id, save_chat, db: dbSelect.value || null })
  });
  if (!resp.ok || !resp.body) {
    resultDiv.textContent = `Streaming thất bại: ${resp.status}`;
    return;
  }
  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let answer = '';
  let ctxHandled = false;
  let buffer = '';
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    const chunk = decoder.decode(value, { stream: true });
    buffer += chunk;

    if (!ctxHandled) {
      const tag = '[[CTXJSON]]';
      const tagIdx = buffer.indexOf(tag);
      const nlIdx = buffer.indexOf('\n', tagIdx >= 0 ? tagIdx : 0);
      if (tagIdx >= 0 && nlIdx > tagIdx) {
        const header = buffer.substring(tagIdx, nlIdx);
        const jsonStr = header.replace(tag, '');
        try {
          const obj = JSON.parse(jsonStr);
          const ctxs = obj.contexts || [];
          const blocks = ctxs.map((c, i) => `<div class=\"ctx\"><strong>CTX ${i+1}</strong><pre>${escapeHtml(c)}</pre></div>`);
          contextsDiv.innerHTML = blocks.join('');
        } catch {}
        ctxHandled = true;
        buffer = buffer.substring(nlIdx + 1);
      } else {
        // chưa đủ header hoàn chỉnh
        continue;
      }
    }

    if (buffer) {
      answer += buffer;
      resultDiv.textContent = answer;
      buffer = '';
    }
  }
}

async function askStreamingMH(q, k, method, bm25_weight, chat_id, save_chat) {
  const rerank_enable = !!rerankCk.checked;
  const rerank_top_n = parseInt(rerankTopN.value || '10', 10);
  const depth = parseInt(hopDepth.value || '2', 10);
  const fanout = parseInt(hopFanout.value || '2', 10);
  const resp = await fetch('/api/stream_multihop_query', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query: q, k, method, bm25_weight, rerank_enable, rerank_top_n, depth, fanout, chat_id, save_chat, db: dbSelect.value || null })
  });
  if (!resp.ok || !resp.body) {
    resultDiv.textContent = `Streaming thất bại: ${resp.status}`;
    return;
  }
  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let answer = '';
  let ctxHandled = false;
  let buffer = '';
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    const chunk = decoder.decode(value, { stream: true });
    buffer += chunk;

    if (!ctxHandled) {
      const tag = '[[CTXJSON]]';
      const tagIdx = buffer.indexOf(tag);
      const nlIdx = buffer.indexOf('\n', tagIdx >= 0 ? tagIdx : 0);
      if (tagIdx >= 0 && nlIdx > tagIdx) {
        const header = buffer.substring(tagIdx, nlIdx);
        const jsonStr = header.replace(tag, '');
        try {
          const obj = JSON.parse(jsonStr);
          const ctxs = obj.contexts || [];
          const blocks = ctxs.map((c, i) => `<div class=\"ctx\"><strong>CTX ${i+1}</strong><pre>${escapeHtml(c)}</pre></div>`);
          contextsDiv.innerHTML = blocks.join('');
        } catch {}
        ctxHandled = true;
        buffer = buffer.substring(nlIdx + 1);
      } else {
        continue;
      }
    }

    if (buffer) {
      answer += buffer;
      resultDiv.textContent = answer;
      buffer = '';
    }
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

dbSelect.addEventListener('change', async () => {
  const name = dbSelect.value;
  if (name) await useDb(name);
  await loadChats();
});

dbCreateBtn.addEventListener('click', async () => { await createDb(); await loadChats(); });
dbDeleteBtn.addEventListener('click', async () => { await deleteDb(); await loadChats(); });
chatNewBtn.addEventListener('click', createChat);
chatRenameBtn.addEventListener('click', renameChat);
chatDeleteBtn.addEventListener('click', deleteChat);

// init
loadDbs().then(loadChats);

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

multihopCk.addEventListener('change', () => {
  const on = multihopCk.checked;
  multihopDepthWrap.style.display = on ? '' : 'none';
  multihopFanoutWrap.style.display = on ? '' : 'none';
});
