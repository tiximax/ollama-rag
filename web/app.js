const ingestBtn = document.getElementById('btn-ingest');
const askBtn = document.getElementById('btn-ask');
const queryInput = document.getElementById('txt-query');
const topkInput = document.getElementById('top-k');
const streamCk = document.getElementById('ck-stream');
const resultDiv = document.getElementById('result');
const contextsDiv = document.getElementById('contexts');
const citationsDiv = document.getElementById('citations');
const methodSel = document.getElementById('method');
const bm25Wrap = document.getElementById('bm25-weight-wrap');
const bm25Range = document.getElementById('bm25-weight');
const bm25Val = document.getElementById('bm25-weight-val');
const rerankCk = document.getElementById('ck-rerank');
const rerankTopWrap = document.getElementById('rerank-topn-wrap');
const rerankTopN = document.getElementById('rerank-topn');
const rerankAdv = document.getElementById('rerank-adv');
const rrProvider = document.getElementById('rr-provider');
const rrMaxK = document.getElementById('rr-maxk');
const rrBatch = document.getElementById('rr-batch');
const rrThreads = document.getElementById('rr-threads');
const rewriteCk = document.getElementById('ck-rewrite');
const rewriteNWrap = document.getElementById('rewrite-n-wrap');
const rewriteN = document.getElementById('rewrite-n');
const dbSelect = document.getElementById('db-select');
const dbNewName = document.getElementById('db-new-name');
const dbCreateBtn = document.getElementById('btn-db-create');
const dbDeleteBtn = document.getElementById('btn-db-delete');
const chatSelect = document.getElementById('chat-select');
const chatNewBtn = document.getElementById('btn-chat-new');
const chatRenameBtn = document.getElementById('btn-chat-rename');
const chatDeleteBtn = document.getElementById('btn-chat-delete');
const chatExportJsonBtn = document.getElementById('btn-chat-export-json');
const chatExportMdBtn = document.getElementById('btn-chat-export-md');
const chatDeleteAllBtn = document.getElementById('btn-chat-delete-all');
const chatExportDbJsonBtn = document.getElementById('btn-chat-export-db-json');
const chatExportDbMdBtn = document.getElementById('btn-chat-export-db-md');
const citationsChatBtn = document.getElementById('btn-citations-chat');
const citationsDbBtn = document.getElementById('btn-citations-db');
const citSrc = document.getElementById('cit-src');
const citVer = document.getElementById('cit-ver');
const citLang = document.getElementById('cit-lang');
const chatSearchInput = document.getElementById('chat-search');
const chatSearchBtn = document.getElementById('btn-chat-search');
const saveChatCk = document.getElementById('ck-save-chat');
const providerSel = document.getElementById('provider-select');
const providerName = document.getElementById('provider-name');
const multihopCk = document.getElementById('ck-multihop');
const multihopDepthWrap = document.getElementById('multihop-depth-wrap');
const multihopFanoutWrap = document.getElementById('multihop-fanout-wrap');
const multihopFanout1Wrap = document.getElementById('multihop-fanout1-wrap');
const multihopBudgetWrap = document.getElementById('multihop-budget-wrap');
const hopDepth = document.getElementById('hop-depth');
const hopFanout = document.getElementById('hop-fanout');
const hopFanout1 = document.getElementById('hop-fanout1');
const hopBudget = document.getElementById('hop-budget');
const ingestVersion = document.getElementById('ingest-version');
const ingestPaths = document.getElementById('ingest-paths');
const ingestPathsBtn = document.getElementById('btn-ingest-paths');
const filterLangsSel = document.getElementById('filter-langs');
const filterVersSel = document.getElementById('filter-versions');
const evalJson = document.getElementById('eval-json');
const evalRunBtn = document.getElementById('btn-eval-run');
const evalResultDiv = document.getElementById('eval-result');
const fbUpBtn = document.getElementById('btn-fb-up');
const fbDownBtn = document.getElementById('btn-fb-down');
const fbSendBtn = document.getElementById('btn-fb-send');
const fbComment = document.getElementById('fb-comment');
const logsEnableCk = document.getElementById('ck-logs-enable');
const logsExportBtn = document.getElementById('btn-logs-export');
const analyticsRefreshBtn = document.getElementById('btn-analytics-refresh');
const anChats = document.getElementById('an-chats');
const anQa = document.getElementById('an-qa');
const anAnswered = document.getElementById('an-answered');
const anWithCtx = document.getElementById('an-withctx');
const anAnsAvg = document.getElementById('an-ans-avg');
const anAnsMed = document.getElementById('an-ans-med');
const anTopSources = document.getElementById('an-top-sources');
const anTopVersions = document.getElementById('an-top-versions');
const anTopLangs = document.getElementById('an-top-langs');
// Logs summary elements
const logsSince = document.getElementById('logs-since');
const logsUntil = document.getElementById('logs-until');
const logsSummaryBtn = document.getElementById('btn-logs-summary-refresh');
const lgTotal = document.getElementById('lg-total');
const lgMed = document.getElementById('lg-med');
const lgRate = document.getElementById('lg-rate');
const lgByRoute = document.getElementById('lg-by-route');
const lgByProvider = document.getElementById('lg-by-provider');
const lgByMethod = document.getElementById('lg-by-method');

async function loadProvider() {
  try {
    const resp = await fetch('/api/provider');
    const data = await resp.json();
    if (resp.ok && data.provider) {
      if (providerSel) providerSel.value = data.provider;
      if (providerName) providerName.textContent = data.provider;
    }
  } catch {}
}

async function loadFilters() {
  try {
    const params = new URLSearchParams();
    if (dbSelect && dbSelect.value) params.set('db', dbSelect.value);
    const resp = await fetch('/api/filters?' + params.toString());
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || 'Không tải được filters');
    const langs = data.languages || [];
    const vers = data.versions || [];
    if (filterLangsSel) {
      filterLangsSel.innerHTML = '';
      langs.forEach(l => {
        const opt = document.createElement('option');
        opt.value = l;
        opt.textContent = l;
        filterLangsSel.appendChild(opt);
      });
    }
    if (filterVersSel) {
      filterVersSel.innerHTML = '';
      vers.forEach(v => {
        const opt = document.createElement('option');
        opt.value = v;
        opt.textContent = v;
        filterVersSel.appendChild(opt);
      });
    }
  } catch (e) {
    console.error('loadFilters error', e);
  }
}

function getSelectedValues(selectEl) {
  if (!selectEl) return [];
  return Array.from(selectEl.selectedOptions || []).map(o => o.value).filter(Boolean);
}

async function loadLogsInfo() {
  try {
    const params = new URLSearchParams();
    if (dbSelect.value) params.set('db', dbSelect.value);
    const resp = await fetch('/api/logs/info?' + params.toString());
    const data = await resp.json();
    if (resp.ok && logsEnableCk) logsEnableCk.checked = !!data.enabled;
  } catch {}
}

async function setLogsEnabled(enabled) {
  try {
    const body = { db: dbSelect.value || null, enabled: !!enabled };
    const resp = await fetch('/api/logs/enable', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    if (!resp.ok) {
      const data = await resp.json().catch(() => ({}));
      throw new Error(data.detail || resp.status);
    }
  } catch (e) {
    alert('Không thể bật/tắt logs: ' + e);
  }
}

async function exportLogs() {
  try {
    const params = new URLSearchParams();
    if (dbSelect.value) params.set('db', dbSelect.value);
    const resp = await fetch('/api/logs/export?' + params.toString());
    if (!resp.ok) throw new Error('Export logs thất bại');
    const text = await resp.text();
    const name = `logs-${dbSelect.value || 'default'}.jsonl`;
    downloadFile(name, text, 'application/jsonl');
  } catch (e) {
    alert('Lỗi export logs: ' + e);
  }
}

async function setProvider(name) {
  try {
    const resp = await fetch('/api/provider', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name })
    });
    const data = await resp.json();
    if (resp.ok) {
      if (providerName) providerName.textContent = data.provider || name;
    }
  } catch (e) {
    alert('Lỗi đổi provider: ' + e);
  }
}

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

async function deleteAllChats() {
  if (!confirm('Xóa toàn bộ chat của DB hiện tại?')) return;
  try {
    const params = new URLSearchParams();
    if (dbSelect.value) params.set('db', dbSelect.value);
    const resp = await fetch(`/api/chats?${params.toString()}`, { method: 'DELETE' });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || 'Không xóa được');
    await loadChats();
    alert(`Đã xóa ${data.deleted} chats.`);
  } catch (e) {
    alert('Lỗi xóa tất cả: ' + e);
  }
}

let gLastAnswer = '';
let gLastMetas = [];
let gLastQuery = '';
let gFbScore = 0;

async function runEval() {
  try {
    const raw = (evalJson && evalJson.value || '').trim();
    if (!raw) {
      evalResultDiv.textContent = 'Nhập JSON dataset trước.';
      return;
    }
    let data;
    try {
      data = JSON.parse(raw);
    } catch (e) {
      evalResultDiv.textContent = 'JSON không hợp lệ: ' + e;
      return;
    }
    if (!data) { evalResultDiv.textContent = 'Dataset trống'; return; }
    if (!data.db && dbSelect && dbSelect.value) data.db = dbSelect.value;
    const resp = await fetch('/api/eval/offline', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    const out = await resp.json();
    if (!resp.ok) {
      evalResultDiv.textContent = 'Eval lỗi: ' + (out.detail || resp.status);
      return;
    }
    const n = out.n || 0;
    const hits = out.hits || 0;
    const recall = typeof out.recall_at_k === 'number' ? out.recall_at_k.toFixed(2) : out.recall_at_k;
    evalResultDiv.textContent = `Recall@k: ${recall} (${hits}/${n})`;
  } catch (e) {
    evalResultDiv.textContent = 'Eval lỗi: ' + e;
  }
}

async function loadAnalytics() {
  try {
    const params = new URLSearchParams();
    if (dbSelect.value) params.set('db', dbSelect.value);
    const resp = await fetch('/api/analytics/db?' + params.toString());
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || 'Analytics lỗi');
    if (anChats) anChats.textContent = String(data.chats ?? '-');
    if (anQa) anQa.textContent = String(data.qa_pairs ?? '-');
    if (anAnswered) anAnswered.textContent = String(data.answered ?? '-');
    if (anWithCtx) anWithCtx.textContent = String(data.with_contexts ?? '-');
    if (anAnsAvg) anAnsAvg.textContent = String((data.answer_len_avg ?? 0).toFixed ? data.answer_len_avg.toFixed(2) : data.answer_len_avg);
    if (anAnsMed) anAnsMed.textContent = data.answer_len_median == null ? '-' : String(data.answer_len_median);
    const renderList = (el, arr) => {
      if (!el) return;
      el.innerHTML = '';
      (arr || []).forEach(it => {
        const li = document.createElement('li');
        li.textContent = `${it.value} (${it.count})`;
        el.appendChild(li);
      });
    };
    renderList(anTopSources, data.top_sources || []);
    renderList(anTopVersions, data.top_versions || []);
    renderList(anTopLangs, data.top_languages || []);
  } catch (e) {
    if (anChats) anChats.textContent = '-';
  }
}

function renderListKV(el, arr) {
  if (!el) return;
  el.innerHTML = '';
  (arr || []).forEach(it => {
    const li = document.createElement('li');
    li.textContent = `${it.key}: ${it.count}`;
    el.appendChild(li);
  });
}

async function loadLogsSummary() {
  try {
    const params = new URLSearchParams();
    if (dbSelect.value) params.set('db', dbSelect.value);
    if (logsSince && logsSince.value.trim()) params.set('since', logsSince.value.trim());
    if (logsUntil && logsUntil.value.trim()) params.set('until', logsUntil.value.trim());
    const resp = await fetch('/api/logs/summary?' + params.toString());
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || 'Summary lỗi');
    if (lgTotal) lgTotal.textContent = String(data.total ?? '-');
    if (lgMed) lgMed.textContent = String((data.median_latency_ms ?? 0).toFixed ? data.median_latency_ms.toFixed(2) : data.median_latency_ms);
    if (lgRate) lgRate.textContent = String((data.contexts_rate ?? 0).toFixed ? data.contexts_rate.toFixed(2) : data.contexts_rate);
    renderListKV(lgByRoute, data.by_route || []);
    renderListKV(lgByProvider, data.by_provider || []);
    renderListKV(lgByMethod, data.by_method || []);
  } catch (e) {
    if (lgTotal) lgTotal.textContent = '-';
  }
}

function downloadFile(name, content, mime) {
  const blob = new Blob([content], { type: mime || 'application/octet-stream' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}

function downloadBlob(name, blob) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}

async function exportChat(format) {
  const id = chatSelect.value;
  if (!id) { alert('Chưa chọn chat'); return; }
  try {
    const params = new URLSearchParams();
    if (dbSelect.value) params.set('db', dbSelect.value);
    params.set('format', format);
    const resp = await fetch(`/api/chats/${encodeURIComponent(id)}/export?${params.toString()}`);
    if (!resp.ok) {
      const data = await resp.json().catch(() => ({}));
      throw new Error(data.detail || 'Export thất bại');
    }
    if (format === 'json') {
      const data = await resp.json();
      downloadFile(`chat-${id}.json`, JSON.stringify(data, null, 2), 'application/json');
    } else {
      const text = await resp.text();
downloadFile(`chat-${id}.md`, text, 'text/markdown');
    }
  } catch (e) {
    alert('Lỗi export: ' + e);
  }
}

async function sendFeedback() {
  try {
    const score = gFbScore;
    if (!score) { alert('Chọn 👍 hoặc 👎 trước khi gửi'); return; }
    const provider = providerSel ? providerSel.value : undefined;
    const method = methodSel ? methodSel.value : undefined;
    const k = parseInt(topkInput.value || '5', 10);
    const languages = getSelectedValues(filterLangsSel);
    const versions = getSelectedValues(filterVersSel);
    const sources = Array.isArray(gLastMetas) ? gLastMetas.map(m => (m && m.source) ? String(m.source) : '') : [];
    const payload = {
      db: dbSelect.value || null,
      chat_id: chatSelect.value || null,
      query: gLastQuery || null,
      answer: gLastAnswer || null,
      score,
      comment: fbComment && fbComment.value || '',
      provider,
      method,
      k,
      languages: languages.length ? languages : null,
      versions: versions.length ? versions : null,
      sources,
    };
    const resp = await fetch('/api/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!resp.ok) {
      const data = await resp.json().catch(() => ({}));
      throw new Error(data.detail || resp.status);
    }
    if (fbComment) fbComment.value = '';
    gFbScore = 0;
    alert('Đã gửi feedback!');
  } catch (e) {
    alert('Lỗi gửi feedback: ' + e);
  }
}

async function exportDb(format) {
  try {
    const params = new URLSearchParams();
    if (dbSelect.value) params.set('db', dbSelect.value);
    params.set('format', format);
    const resp = await fetch('/api/chats/export_db?' + params.toString());
    if (!resp.ok) throw new Error('Export DB thất bại');
    const buf = await resp.arrayBuffer();
    const blob = new Blob([buf], { type: 'application/zip' });
    const name = `db-${dbSelect.value || 'default'}-${format}.zip`;
    downloadBlob(name, blob);
  } catch (e) {
    alert('Lỗi export DB: ' + e);
  }
}

async function searchChats() {
  const q = (chatSearchInput.value || '').trim();
  if (!q) { alert('Nhập từ khóa'); return; }
  try {
    const params = new URLSearchParams();
    if (dbSelect.value) params.set('db', dbSelect.value);
    params.set('q', q);
    const resp = await fetch(`/api/chats/search?${params.toString()}`);
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || 'Search lỗi');
    const results = data.results || [];
    resultDiv.textContent = `Search '${q}': ${results.length} chats có kết quả.`;
  } catch (e) {
    alert('Lỗi search: ' + e);
  }
}

function renderCitations(answerText, metas) {
  try {
    if (citationsDiv) citationsDiv.innerHTML = '';
    if (!answerText || !Array.isArray(metas) || metas.length === 0 || !citationsDiv) return;
    const re = /\[(\d+)\]/g;
    const seen = new Set();
    let m;
    const items = [];
    while ((m = re.exec(answerText)) !== null) {
      const n = parseInt(m[1], 10);
      if (!Number.isFinite(n)) continue;
      if (n < 1 || n > metas.length) continue;
      if (seen.has(n)) continue;
      seen.add(n);
      const meta = metas[n - 1] || {};
      const src = meta.source || '(unknown)';
      const chunk = typeof meta.chunk === 'number' ? `#${meta.chunk}` : '';
      items.push(`<div class=\"citation\">[${n}] ${escapeHtml(src)} ${chunk}</div>`);
    }
    if (items.length) {
      citationsDiv.innerHTML = `<div class=\"citations-title\">Citations</div>` + items.join('');
    }
  } catch {}
}

async function ingest() {
  resultDiv.textContent = 'Đang index tài liệu...';
  try {
    const payload = { paths: ['data/docs'], db: dbSelect.value || null };
    if (ingestVersion && ingestVersion.value.trim()) payload.version = ingestVersion.value.trim();
    const resp = await fetch('/api/ingest', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await resp.json();
    if (resp.ok) {
      resultDiv.textContent = `Đã index ${data.chunks_indexed} chunks.`;
      await loadFilters();
    } else {
      resultDiv.textContent = `Lỗi ingest: ${data.detail}`;
    }
  } catch (e) {
    resultDiv.textContent = `Lỗi kết nối server: ${e}`;
  }
}

async function ingestByPaths() {
  const raw = (ingestPaths && ingestPaths.value || '').trim();
  if (!raw) {
    alert('Nhập Paths (có thể là glob, phân tách bằng dấu ,)');
    return;
  }
  resultDiv.textContent = 'Đang index tài liệu (custom paths)...';
  try {
    const list = raw.split(',').map(s => s.trim()).filter(Boolean);
    const payload = { paths: list, db: dbSelect.value || null };
    if (ingestVersion && ingestVersion.value.trim()) payload.version = ingestVersion.value.trim();
    const resp = await fetch('/api/ingest', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await resp.json();
    if (resp.ok) {
      resultDiv.textContent = `Đã index ${data.chunks_indexed} chunks.`;
      await loadFilters();
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
  const rewrite_enable = !!rewriteCk.checked;
  const rewrite_n = parseInt(rewriteN.value || '2', 10);
  if (!q) {
    resultDiv.textContent = 'Vui lòng nhập câu hỏi';
    return;
  }
  resultDiv.textContent = 'Đang truy vấn...';
  contextsDiv.innerHTML = '';

  try {
    const chat_id = chatSelect.value || null;
    const save_chat = !!saveChatCk.checked;
    const provider = providerSel ? providerSel.value : undefined;
    const languages = getSelectedValues(filterLangsSel);
    const versions = getSelectedValues(filterVersSel);
    gLastQuery = q;
    if (streaming) {
      if (multihopCk.checked) {
        await askStreamingMH(q, k, method, bm25_weight, chat_id, save_chat, { languages, versions });
      } else {
        await askStreaming(q, k, method, bm25_weight, chat_id, save_chat, { rewrite_enable, rewrite_n, languages, versions });
      }
    } else {
      if (multihopCk.checked) {
        const resp = await fetch('/api/multihop_query', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query: q, k, method, bm25_weight, rerank_enable, rerank_top_n, depth: parseInt(hopDepth.value||'2',10), fanout: parseInt(hopFanout.value||'2',10), fanout_first_hop: parseInt(hopFanout1.value||'1',10), budget_ms: parseInt(hopBudget.value||'0',10), provider, chat_id, save_chat, db: dbSelect.value || null, rewrite_enable, rewrite_n, languages, versions })
        });
        const data = await resp.json();
        if (resp.ok) {
          resultDiv.textContent = data.answer || '(Không có trả lời)';
          gLastAnswer = data.answer || '';
          const ctxs = data.contexts || [];
          const metas = data.metadatas || [];
          if (ctxs.length) {
            const blocks = ctxs.map((c, i) => `<div class=\"ctx\"><strong>CTX ${i+1}</strong><pre>${escapeHtml(c)}</pre></div>`);
            contextsDiv.innerHTML = blocks.join('');
          }
          renderCitations(data.answer || '', metas);
        } else {
          resultDiv.textContent = `Lỗi truy vấn: ${data.detail}`;
        }
      } else {
        const resp = await fetch('/api/query', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query: q, k, method, bm25_weight, rerank_enable, rerank_top_n, provider, chat_id, save_chat, db: dbSelect.value || null, rewrite_enable, rewrite_n, languages, versions })
        });
        const data = await resp.json();
        if (resp.ok) {
          resultDiv.textContent = data.answer || '(Không có trả lời)';
          const ctxs = data.contexts || [];
          if (ctxs.length) {
            const blocks = ctxs.map((c, i) => `<div class=\"ctx\"><strong>CTX ${i+1}</strong><pre>${escapeHtml(c)}</pre></div>`);
            contextsDiv.innerHTML = blocks.join('');
          }
          const metas = data.metadatas || [];
          gLastMetas = metas;
          renderCitations(data.answer || '', metas);
        } else {
          resultDiv.textContent = `Lỗi truy vấn: ${data.detail}`;
        }
      }
    }
  } catch (e) {
    resultDiv.textContent = `Lỗi kết nối server: ${e}`;
  }
}

async function askStreaming(q, k, method, bm25_weight, chat_id, save_chat, opt) {
  const rerank_enable = !!rerankCk.checked;
  const rerank_top_n = parseInt(rerankTopN.value || '10', 10);
  const provider = providerSel ? providerSel.value : undefined;
  const payload = { query: q, k, method, bm25_weight, rerank_enable, rerank_top_n, provider, chat_id, save_chat, db: dbSelect.value || null };
  if (rerank_enable && rrProvider) {
    payload.rr_provider = rrProvider.value;
    payload.rr_max_k = parseInt((rrMaxK && rrMaxK.value) || '10', 10);
    payload.rr_batch_size = parseInt((rrBatch && rrBatch.value) || '16', 10);
    payload.rr_num_threads = parseInt((rrThreads && rrThreads.value) || '1', 10);
  }
  if (opt) {
    if (typeof opt.rewrite_enable !== 'undefined') {
      payload.rewrite_enable = !!opt.rewrite_enable;
      payload.rewrite_n = parseInt(opt.rewrite_n || 2, 10);
    }
    if (Array.isArray(opt.languages)) payload.languages = opt.languages;
    if (Array.isArray(opt.versions)) payload.versions = opt.versions;
  }
  const resp = await fetch('/api/stream_query', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
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
  let lastMetas = [];
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
          lastMetas = obj.metadatas || [];
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
  gLastAnswer = answer;
  gLastMetas = lastMetas || [];
  renderCitations(answer, lastMetas);
}

async function askStreamingMH(q, k, method, bm25_weight, chat_id, save_chat, opt) {
  const rerank_enable = !!rerankCk.checked;
  const rerank_top_n = parseInt(rerankTopN.value || '10', 10);
  const depth = parseInt(hopDepth.value || '2', 10);
  const fanout = parseInt(hopFanout.value || '2', 10);
  const provider = providerSel ? providerSel.value : undefined;
  const payload = { query: q, k, method, bm25_weight, rerank_enable, rerank_top_n, depth, fanout, provider, chat_id, save_chat, db: dbSelect.value || null };
  if (opt) {
    if (Array.isArray(opt.languages)) payload.languages = opt.languages;
    if (Array.isArray(opt.versions)) payload.versions = opt.versions;
  }
  const resp = await fetch('/api/stream_multihop_query', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
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
  let lastMetas = [];
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
          lastMetas = obj.metadatas || [];
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
  gLastAnswer = answer;
  gLastMetas = lastMetas || [];
  renderCitations(answer, lastMetas);
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
  await loadFilters();
  await loadLogsInfo();
  await loadAnalytics();
  await loadLogsSummary();
});

dbCreateBtn.addEventListener('click', async () => { await createDb(); await loadChats(); });
dbDeleteBtn.addEventListener('click', async () => { await deleteDb(); await loadChats(); });
chatNewBtn.addEventListener('click', createChat);
chatRenameBtn.addEventListener('click', renameChat);
chatDeleteBtn.addEventListener('click', deleteChat);
chatDeleteAllBtn.addEventListener('click', deleteAllChats);
chatExportJsonBtn.addEventListener('click', () => exportChat('json'));
chatExportMdBtn.addEventListener('click', () => exportChat('md'));
chatExportDbJsonBtn.addEventListener('click', () => exportDb('json'));
chatExportDbMdBtn.addEventListener('click', () => exportDb('md'));
chatSearchBtn.addEventListener('click', searchChats);
if (ingestPathsBtn) ingestPathsBtn.addEventListener('click', ingestByPaths);
if (evalRunBtn) evalRunBtn.addEventListener('click', runEval);
if (fbUpBtn) fbUpBtn.addEventListener('click', () => { gFbScore = 1; });
if (fbDownBtn) fbDownBtn.addEventListener('click', () => { gFbScore = -1; });
if (fbSendBtn) fbSendBtn.addEventListener('click', sendFeedback);
if (logsEnableCk) logsEnableCk.addEventListener('change', async () => { await setLogsEnabled(logsEnableCk.checked); });
if (logsExportBtn) logsExportBtn.addEventListener('click', exportLogs);
if (analyticsRefreshBtn) analyticsRefreshBtn.addEventListener('click', loadAnalytics);
if (logsSummaryBtn) logsSummaryBtn.addEventListener('click', loadLogsSummary);
if (citationsChatBtn) citationsChatBtn.addEventListener('click', async () => {
  const id = chatSelect.value;
  if (!id) { alert('Chưa chọn chat'); return; }
  try {
    const params = new URLSearchParams();
    if (dbSelect.value) params.set('db', dbSelect.value);
    params.set('format', 'json');
    if (citSrc && citSrc.value.trim()) params.set('sources', citSrc.value.trim());
    if (citVer && citVer.value.trim()) params.set('versions', citVer.value.trim());
    if (citLang && citLang.value.trim()) params.set('languages', citLang.value.trim());
    const resp = await fetch(`/api/citations/chat/${encodeURIComponent(id)}?${params.toString()}`);
    if (!resp.ok) throw new Error('Export citations lỗi');
    const text = await resp.text();
    downloadFile(`citations-${id}.json`, text, 'application/json');
  } catch (e) { alert('Lỗi export citations: ' + e); }
});
if (citationsDbBtn) citationsDbBtn.addEventListener('click', async () => {
  try {
    const params = new URLSearchParams();
    if (dbSelect.value) params.set('db', dbSelect.value);
    params.set('format', 'json');
    if (citSrc && citSrc.value.trim()) params.set('sources', citSrc.value.trim());
    if (citVer && citVer.value.trim()) params.set('versions', citVer.value.trim());
    if (citLang && citLang.value.trim()) params.set('languages', citLang.value.trim());
    const resp = await fetch('/api/citations/db?' + params.toString());
    if (!resp.ok) throw new Error('Export citations DB lỗi');
    const buf = await resp.arrayBuffer();
    const blob = new Blob([buf], { type: 'application/zip' });
    const name = `citations-${dbSelect.value || 'default'}.zip`;
    downloadBlob(name, blob);
  } catch (e) { alert('Lỗi export citations DB: ' + e); }
});

// init
loadProvider().then(() => loadDbs().then(async () => { await loadChats(); await loadFilters(); await loadLogsInfo(); await loadAnalytics(); await loadLogsSummary(); }));

methodSel.addEventListener('change', () => {
  const m = methodSel.value;
  const show = m === 'hybrid';
  bm25Wrap.style.display = show ? '' : 'none';
});

rerankCk.addEventListener('change', () => {
  const on = rerankCk.checked;
  rerankTopWrap.style.display = on ? '' : 'none';
  if (rerankAdv) rerankAdv.style.display = on ? '' : 'none';
});

bm25Range.addEventListener('input', () => {
  bm25Val.textContent = bm25Range.value;
});

multihopCk.addEventListener('change', () => {
  const on = multihopCk.checked;
  multihopDepthWrap.style.display = on ? '' : 'none';
  multihopFanoutWrap.style.display = on ? '' : 'none';
  multihopFanout1Wrap.style.display = on ? '' : 'none';
  multihopBudgetWrap.style.display = on ? '' : 'none';
});

rewriteCk.addEventListener('change', () => {
  rewriteNWrap.style.display = rewriteCk.checked ? '' : 'none';
});

if (providerSel) {
  providerSel.addEventListener('change', async () => {
    await setProvider(providerSel.value);
  });
}
