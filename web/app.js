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
const fileUploadInput = document.getElementById('file-upload');
const uploadBtn = document.getElementById('btn-upload');
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
const advResetBtn = document.getElementById('btn-adv-reset');
const anChats = document.getElementById('an-chats');
// Backend status
const backendStatus = document.getElementById('backend-status');
// Help menu
const menuHelp = document.getElementById('menu-help');
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

// New UI elements (v2)
const docList = document.getElementById('doc-list');
const docDeleteBtn = document.getElementById('btn-docs-delete');
const chatList = document.getElementById('chat-list');
const reloadBtn = document.getElementById('btn-reload');
const dbStatus = document.getElementById('db-status');
const statsToggleBtn = document.getElementById('btn-stats-toggle');
const statsBody = document.getElementById('stats-body');
const docsToggleBtn = document.getElementById('btn-docs-toggle');
const docsBody = document.getElementById('docs-body');
const chatsToggleBtn = document.getElementById('btn-chats-toggle');
const chatsBody = document.getElementById('chats-body');
// Settings UI
const menuSettings = document.getElementById('menu-settings');
const settingsOverlay = document.getElementById('settings-overlay');
const settingsModal = document.getElementById('settings-modal');
const settingsClose = document.getElementById('settings-close');
const settingsProvider = document.getElementById('settings-provider');
const settingsStreamDefault = document.getElementById('settings-stream-default');
const settingsLangs = document.getElementById('settings-langs');
const settingsSave = document.getElementById('settings-save');
const settingsResetUI = document.getElementById('settings-reset-ui');

async function loadProvider() {
  try {
    const resp = await fetch('/api/provider');
    const data = await resp.json();
    // Sync settings modal select if present
    if (settingsProvider && data.provider) settingsProvider.value = data.provider;
    if (resp.ok && data.provider) {
      if (providerSel) providerSel.value = data.provider;
      if (providerName) providerName.textContent = data.provider;
    }
  } catch {}
}

async function loadHealth() {
  // Hiển thị health dưới dạng badge màu + tooltip gợi ý
  const setBadge = (cls, text, title) => {
    if (!backendStatus) return;
    backendStatus.className = `status badge ${cls}`;
    backendStatus.textContent = text;
    if (title) backendStatus.title = Array.isArray(title) ? title.join('\n') : String(title);
  };
  try {
    const resp = await fetch('/api/health');
    const data = await resp.json();
    if (resp.ok) {
      const st = (data.overall_status || '').toLowerCase();
      const msg = data.message || '';
      const tips = data.suggestions || [];
      if (st === 'ok') setBadge('ok', `✅ ${msg}`, tips);
      else if (st === 'warning') setBadge('warning', `⚠️ ${msg}`, tips);
      else setBadge('error', `⛔ ${msg || 'Backend lỗi'}`, tips);

      // Disable/enable action buttons dựa trên health
      const healthy = st === 'ok';
      const buttons = [ingestPathsBtn, uploadBtn, askBtn];
      buttons.forEach(b => { if (b) b.disabled = !healthy; });
    } else {
      setBadge('error', '⛔ Backend: lỗi health API');
    }
  } catch (e) {
    if (backendStatus) backendStatus.textContent = 'Backend: lỗi kết nối health';
  }
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
notifyError('Không thể bật/tắt logs: ' + e);
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
notifyError('Lỗi export logs: ' + e);
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
notifyError('Lỗi đổi provider: ' + e);
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

async function loadDocs() {
  try {
    const params = new URLSearchParams();
    if (dbSelect.value) params.set('db', dbSelect.value);
    const resp = await fetch('/api/docs?' + params.toString());
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || 'Không tải được danh sách tài liệu');
if (docList) {
      docList.innerHTML = '';
      const docs = data.docs || [];
      if (!docs.length) {
        const li = document.createElement('li');
        li.className = 'empty muted';
        li.textContent = 'Chưa có tài liệu. Dùng "Thêm vào DB" hoặc "Ingest file" để nạp nội dung.';
        docList.appendChild(li);
      }
      docs.forEach(item => {
        const li = document.createElement('li');
        const cb = document.createElement('input'); cb.type = 'checkbox'; cb.value = item.source;
        const span = document.createElement('span'); span.className = 'title'; span.textContent = `${item.source} (${item.chunks})`;
        li.appendChild(cb); li.appendChild(span);
        docList.appendChild(li);
      });
      // Update topbar DB status
      const totalDocs = docs.length;
      const totalChunks = docs.reduce((s, it) => s + (parseInt(it.chunks, 10) || 0), 0);
      const name = (dbSelect && dbSelect.value) || 'default';
      if (dbStatus) dbStatus.textContent = `DB '${name}' — ${totalDocs} tài liệu, ${totalChunks} chunks`;
    }
  } catch (e) {
    console.error('loadDocs error', e);
  }
}

function renderChatList(chats) {
  if (!chatList) return;
  chatList.innerHTML = '';
  if (!chats || !chats.length) {
    const li = document.createElement('li');
    li.className = 'empty muted';
    li.textContent = 'Chưa có hội thoại. Bấm "Hội thoại mới" để bắt đầu.';
    chatList.appendChild(li);
    return;
  }
  (chats || []).forEach(c => {
  if (!chatList) return;
  chatList.innerHTML = '';
  (chats || []).forEach(c => {
    const li = document.createElement('li');
    const radio = document.createElement('input'); radio.type = 'radio'; radio.name = 'chatlist'; radio.value = c.id;
    radio.addEventListener('change', () => { chatSelect.value = c.id; });
    const span = document.createElement('span'); span.className = 'title'; span.textContent = c.name || c.id;
    li.appendChild(radio); li.appendChild(span);
    chatList.appendChild(li);
  });
}

async function deleteSelectedDocs() {
  try {
    if (!docList) return;
    const selected = Array.from(docList.querySelectorAll('input[type="checkbox"]:checked')).map(cb => cb.value);
    if (!selected.length) { alert('Chọn ít nhất 1 tài liệu'); return; }
    if (!confirm(`Xóa ${selected.length} tài liệu đã chọn?`)) return;
    const resp = await fetch('/api/docs', {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ db: dbSelect.value || null, sources: selected })
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || 'Không xóa được');
    await loadDocs();
  } catch (e) {
notifyError('Lỗi xóa tài liệu: ' + e);
  }
}
  try {
    if (!docList) return;
    const selected = Array.from(docList.querySelectorAll('input[type="checkbox"]:checked')).map(cb => cb.value);
    if (!selected.length) { alert('Chọn ít nhất 1 tài liệu'); return; }
    const resp = await fetch('/api/docs', {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ db: dbSelect.value || null, sources: selected })
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || 'Không xóa được');
    await loadDocs();
  } catch (e) {
    alert('Lỗi xóa tài liệu: ' + e);
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
notifyError('Lỗi đổi DB: ' + e);
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
  if (!confirm(`Xóa DB '${name}'? Hành động này không thể hoàn tác.`)) return;
  try {
    const resp = await fetch('/api/dbs/' + encodeURIComponent(name), { method: 'DELETE' });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || 'Không thể xóa DB');
await loadDbs(); notifySuccess('Đã xóa DB: ' + name);
  } catch (e) {
notifyError('Lỗi xóa DB: ' + e);
  }
}
  const name = dbSelect.value;
  if (!name) return;
  try {
    const resp = await fetch('/api/dbs/' + encodeURIComponent(name), { method: 'DELETE' });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || 'Không thể xóa DB');
    await loadDbs();
  } catch (e) {
notifyError('Lỗi xóa DB: ' + e);
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
    // Update sidebar list
    renderChatList(chats);
    // keep previous selection if exists
    if (prev && [...chatSelect.options].some(o => o.value === prev)) {
      chatSelect.value = prev;
      const r = chatList && chatList.querySelector(`input[type=radio][value="${CSS.escape(prev)}"]`);
      if (r) r.checked = true;
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
chatSelect.value = data.chat.id; notifySuccess('Đã tạo hội thoại');
    }
  } catch (e) {
notifyError('Lỗi tạo chat: ' + e);
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
notifyError('Lỗi đổi tên hội thoại: ' + e);
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
notifySuccess(`Đã xóa ${data.deleted} chats.`);
  } catch (e) {
notifyError('Lỗi xóa tất cả: ' + e);
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
      const id = el.id || '';
      const prefix = id === 'an-top-sources' ? '📄 ' : id === 'an-top-versions' ? '🏷️ ' : id === 'an-top-langs' ? '🌐 ' : '';
      (arr || []).forEach(it => {
        const li = document.createElement('li');
        li.textContent = `${prefix}${it.value} (${it.count})`;
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

/***** Global progress helpers *****/
let _pgTimer = null;
function startProgress(label) {
  try {
    const el = document.getElementById('global-progress');
    const bar = document.getElementById('global-progress-bar');
    const txt = document.getElementById('global-progress-text');
    if (!el || !bar || !txt) return;
    el.hidden = false;
    bar.style.width = '0%';
    let base = label || 'Đang xử lý...';
    txt.textContent = base;
    let p = 0;
    clearInterval(_pgTimer);
    _pgTimer = setInterval(() => {
      p = Math.min(p + Math.random() * 8 + 2, 90);
      const pct = p.toFixed(0) + '%';
      bar.style.width = pct;
      txt.textContent = base + ' ' + '(' + pct + ')';
    }, 200);
  } catch {}
}
function stopProgress(doneText) {
  try {
    const el = document.getElementById('global-progress');
    const bar = document.getElementById('global-progress-bar');
    const txt = document.getElementById('global-progress-text');
    if (!el || !bar || !txt) return;
    clearInterval(_pgTimer);
    bar.style.width = '100%';
    if (doneText) txt.textContent = doneText;
    setTimeout(() => { try { el.hidden = true; bar.style.width = '0%'; txt.textContent = ''; } catch {} }, 500);
  } catch {}
}
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}

/***** Busy helpers *****/
async function withBusy(btn, fn, busyText) {
  let prev;
  try {
    if (btn) {
      prev = btn.textContent;
      btn.disabled = true;
      if (busyText) btn.textContent = busyText;
    }
    return await fn();
  } finally {
    if (btn) {
      btn.disabled = false;
      if (typeof prev !== 'undefined') btn.textContent = prev;
    }
  }
}
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}

/***** Settings helpers *****/
function settingsLoadLocal() {
  try {
    const raw = localStorage.getItem('rag_settings') || '{}';
    const s = JSON.parse(raw);
    if (settingsStreamDefault) settingsStreamDefault.checked = !!s.stream_default;
    if (settingsLangs && typeof s.langs === 'string') settingsLangs.value = s.langs;
  } catch {}
}
function settingsSaveLocal() {
  try {
    const s = {
      stream_default: settingsStreamDefault ? !!settingsStreamDefault.checked : false,
      langs: settingsLangs ? (settingsLangs.value || '') : ''
    };
    localStorage.setItem('rag_settings', JSON.stringify(s));
  } catch {}
}
function settingsApplyToUI() {
  try {
    // Streaming default
    const s = JSON.parse(localStorage.getItem('rag_settings') || '{}');
    if (streamCk && typeof s.stream_default === 'boolean') streamCk.checked = !!s.stream_default;
    // Preselect languages in filters after filters loaded
    const langsCsv = (s.langs || '').trim();
    if (langsCsv && filterLangsSel) {
      const want = new Set(langsCsv.split(',').map(x => x.trim()).filter(Boolean));
      Array.from(filterLangsSel.options || []).forEach(opt => { opt.selected = want.has(opt.value); });
    }
  } catch {}
}

async function uploadAndIngest() {
  startProgress('Đang ingest file...');
  try {
    const files = fileUploadInput && fileUploadInput.files ? Array.from(fileUploadInput.files) : [];
if (!files.length) { notifyWarn('Chọn file để upload'); return; }
    const fd = new FormData();
    files.forEach(f => fd.append('files', f));
    if (dbSelect.value) fd.append('db', dbSelect.value);
    if (ingestVersion && ingestVersion.value.trim()) fd.append('version', ingestVersion.value.trim());
    const resp = await fetch('/api/upload', { method: 'POST', body: fd });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || resp.status);
resultDiv.textContent = `Đã upload ${data.saved.length} file, index ${data.chunks_indexed} chunks.`; notifySuccess(`Ingest thành công: ${data.saved.length} file, ${data.chunks_indexed} chunks`);
await loadFilters();
    stopProgress('Hoàn tất ingest');
  } catch (e) {
    notifyError('Lỗi upload: ' + e);
    stopProgress('Lỗi');
  }
}

async function exportChat(format) {
  const id = chatSelect.value;
if (!id) { notifyWarn('Chưa chọn chat'); return; }
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
notifyError('Lỗi export: ' + e);
  }
}

async function sendFeedback() {
  try {
    const score = gFbScore;
if (!score) { notifyWarn('Chọn 👍 hoặc 👎 trước khi gửi'); return; }
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
notifySuccess('Đã gửi feedback!');
  } catch (e) {
notifyError('Lỗi gửi feedback: ' + e);
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
notifyError('Lỗi export DB: ' + e);
  }
}

async function searchChats() {
  const q = (chatSearchInput.value || '').trim();
if (!q) { notifyWarn('Nhập từ khóa'); return; }
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
notifyError('Lỗi search: ' + e);
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

function _friendlyConnError(e) {
  try {
    const s = String(e || '');
    if (s.includes('11434') || s.toLowerCase().includes('failed to establish a new connection')) {
      return 'Không kết nối được tới dịch vụ embedding (Ollama). Hãy chạy "ollama serve" hoặc đổi Provider sang OpenAI trong Cài đặt.';
    }
  } catch {}
  return null;
}

async function ingest() {
  startProgress('Đang ingest mặc định...');
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
      stopProgress('Hoàn tất ingest');
    } else {
      resultDiv.textContent = `Lỗi ingest: ${data.detail}`;
      stopProgress('Lỗi');
    }
  } catch (e) {
    const msg = _friendlyConnError(e);
    resultDiv.textContent = msg ? msg : `Lỗi kết nối server: ${e}`;
    stopProgress('Lỗi');
  }
}

async function ingestByPaths() {
  startProgress('Đang ingest theo đường dẫn...');
  const raw = (ingestPaths && ingestPaths.value || '').trim();
  if (!raw) {
    notifyWarn('Nhập Paths (có thể là glob, phân tách bằng dấu ,)');
    stopProgress('Lỗi');
    return;
  }
  // Pre-check tokens
  try {
    const items = raw.split(',').map(s => s.trim()).filter(Boolean);
    if (items.length > 50) {
      const ok = confirm(`Có ${items.length} mục. Chỉ nên <= 50. Tiếp tục?`);
      if (!ok) { stopProgress('Huỷ'); return; }
    }
    const invalid = [];
    for (const it of items) {
      const isURL = /^https?:\/\//i.test(it);
      const hasGlob = /[\*\?]/.test(it);
      const hasExt = /\.[A-Za-z0-9]+$/.test(it);
      if (!isURL && !hasGlob && !hasExt) invalid.push(it);
    }
    if (invalid.length) {
      const head = invalid.slice(0, 3).join(', ');
      const ok = confirm(`Một số mục có vẻ không hợp lệ (vd: ${head}${invalid.length>3?'…':''}). Tiếp tục?`);
      if (!ok) { stopProgress('Huỷ'); return; }
    }
  } catch {}
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
      stopProgress('Hoàn tất ingest');
    } else {
      resultDiv.textContent = `Lỗi ingest: ${data.detail}`;
      stopProgress('Lỗi');
    }
  } catch (e) {
    const msg = _friendlyConnError(e);
    resultDiv.textContent = msg ? msg : `Lỗi kết nối server: ${e}`;
    stopProgress('Lỗi');
  }
}

async function ask() {
  const q = queryInput.value.trim();
  const k = parseInt((topkInput && topkInput.value) || '5', 10);
  const streaming = streamCk.checked;
  const method = methodSel ? (methodSel.value || 'vector') : 'vector';
  const bm25_weight = bm25Range ? parseFloat(bm25Range.value || '0.5') : 0.5;
  const rerank_enable = rerankCk ? !!rerankCk.checked : false;
  const rerank_top_n = rerankTopN ? parseInt(rerankTopN.value || '10', 10) : 10;
  const rewrite_enable = rewriteCk ? !!rewriteCk.checked : false;
  const rewrite_n = rewriteN ? parseInt(rewriteN.value || '2', 10) : 2;
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
      if (multihopCk && multihopCk.checked) {
        await askStreamingMH(q, k, method, bm25_weight, chat_id, save_chat, { languages, versions });
      } else {
        await askStreaming(q, k, method, bm25_weight, chat_id, save_chat, { rewrite_enable, rewrite_n, languages, versions });
      }
    } else {
      if (multihopCk && multihopCk.checked) {
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
    const msg = _friendlyConnError(e);
    resultDiv.textContent = msg ? msg : `Lỗi kết nối server: ${e}`;
  }
}

async function askStreaming(q, k, method, bm25_weight, chat_id, save_chat, opt) {
  const rerank_enable = rerankCk ? !!rerankCk.checked : false;
  const rerank_top_n = rerankTopN ? parseInt(rerankTopN.value || '10', 10) : 10;
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
  const rerank_enable = rerankCk ? !!rerankCk.checked : false;
  const rerank_top_n = rerankTopN ? parseInt(rerankTopN.value || '10', 10) : 10;
  const depth = hopDepth ? parseInt(hopDepth.value || '2', 10) : 2;
  const fanout = hopFanout ? parseInt(hopFanout.value || '2', 10) : 2;
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

if (ingestBtn) ingestBtn.addEventListener('click', ingest);
if (askBtn) askBtn.addEventListener('click', () => withBusy(askBtn, () => ask(), 'Đang gửi...'));

if (dbSelect) dbSelect.addEventListener('change', async () => {
  const name = dbSelect.value;
  if (name) await useDb(name);
  await loadChats();
  await loadFilters();
  await loadDocs();
  settingsApplyToUI();
  await loadLogsInfo();
  await loadAnalytics();
  await loadLogsSummary();
});

if (dbCreateBtn) dbCreateBtn.addEventListener('click', async () => { await createDb(); await loadChats(); });
if (dbDeleteBtn) dbDeleteBtn.addEventListener('click', async () => { await deleteDb(); await loadChats(); });
if (chatNewBtn) chatNewBtn.addEventListener('click', createChat);
if (chatRenameBtn) chatRenameBtn.addEventListener('click', renameChat);
if (chatDeleteBtn) chatDeleteBtn.addEventListener('click', deleteChat);
if (chatDeleteAllBtn) chatDeleteAllBtn.addEventListener('click', deleteAllChats);
if (chatExportJsonBtn) chatExportJsonBtn.addEventListener('click', () => exportChat('json'));
if (chatExportMdBtn) chatExportMdBtn.addEventListener('click', () => exportChat('md'));
if (chatExportDbJsonBtn) chatExportDbJsonBtn.addEventListener('click', () => exportDb('json'));
if (chatExportDbMdBtn) chatExportDbMdBtn.addEventListener('click', () => exportDb('md'));
if (chatSearchBtn) chatSearchBtn.addEventListener('click', searchChats);
if (ingestPathsBtn) ingestPathsBtn.addEventListener('click', () => withBusy(ingestPathsBtn, () => ingestByPaths(), 'Đang thêm...'));
if (uploadBtn) uploadBtn.addEventListener('click', () => withBusy(uploadBtn, () => uploadAndIngest(), 'Đang ingest...'));
if (evalRunBtn) evalRunBtn.addEventListener('click', () => withBusy(evalRunBtn, () => runEval(), 'Đang chạy eval...'));
if (fbUpBtn) fbUpBtn.addEventListener('click', () => { gFbScore = 1; });
if (fbDownBtn) fbDownBtn.addEventListener('click', () => { gFbScore = -1; });
if (fbSendBtn) fbSendBtn.addEventListener('click', () => withBusy(fbSendBtn, () => sendFeedback(), 'Đang gửi...'));
if (logsEnableCk) logsEnableCk.addEventListener('change', async () => { await setLogsEnabled(logsEnableCk.checked); });
if (logsExportBtn) logsExportBtn.addEventListener('click', exportLogs);
if (analyticsRefreshBtn) analyticsRefreshBtn.addEventListener('click', loadAnalytics);
if (logsSummaryBtn) logsSummaryBtn.addEventListener('click', loadLogsSummary);
if (docDeleteBtn) docDeleteBtn.addEventListener('click', () => withBusy(docDeleteBtn, () => deleteSelectedDocs(), 'Đang xóa...'));
if (reloadBtn) reloadBtn.addEventListener('click', async () => { await loadDbs(); await loadChats(); await loadFilters(); await loadDocs(); settingsApplyToUI(); await loadLogsInfo(); await loadAnalytics(); await loadLogsSummary(); await loadHealth(); });

// Settings events
if (menuSettings && settingsOverlay && settingsModal && settingsClose && settingsSave) {
  const openSettings = () => { settingsOverlay.hidden = false; settingsModal.hidden = false; settingsLoadLocal(); };
  const closeSettings = () => { settingsOverlay.hidden = true; settingsModal.hidden = true; };
  menuSettings.addEventListener('click', openSettings);
  settingsClose.addEventListener('click', closeSettings);
  settingsOverlay.addEventListener('click', closeSettings);
  window.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeSettings(); });
  settingsSave.addEventListener('click', async () => {
    try {
      // Save local settings
      settingsSaveLocal();
      settingsApplyToUI();
      // Save provider to backend
      if (settingsProvider && settingsProvider.value) {
        await setProvider(settingsProvider.value);
        uiSave();
      }
      closeSettings();
    } catch (e) {
      notifyError('Lưu cài đặt lỗi: ' + e);
    }
  });
}
if (settingsResetUI) settingsResetUI.addEventListener('click', () => {
  try {
    localStorage.removeItem(UI_STATE_KEY);
    resetAdvancedDefaults();
    if (topkInput) topkInput.value = '5';
    uiSave();
    notifySuccess('Đã khôi phục UI mặc định');
  } catch (e) { notifyError('Khôi phục UI lỗi: ' + e); }
});

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
} catch (e) { notifyError('Lỗi export citations: ' + e); }
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
} catch (e) { notifyError('Lỗi export citations DB: ' + e); }
});

// init
settingsLoadLocal();
loadProvider().then(() => loadDbs().then(async () => {
  await loadChats();
  await loadFilters();
  await loadDocs();
  settingsApplyToUI();
  uiLoad();
  bindUiAutosave();
  await loadLogsInfo();
  await loadAnalytics();
  await loadLogsSummary();
  await loadHealth();
}));

if (methodSel) {
  methodSel.addEventListener('change', () => {
    const m = methodSel.value;
    const show = m === 'hybrid';
    if (bm25Wrap) bm25Wrap.style.display = show ? '' : 'none';
    uiSave();
  });
}

if (rerankCk) {
  rerankCk.addEventListener('change', () => {
    const on = rerankCk.checked;
    if (rerankTopWrap) rerankTopWrap.style.display = on ? '' : 'none';
    if (rerankAdv) rerankAdv.style.display = on ? '' : 'none';
    uiSave();
  });
}

if (bm25Range && bm25Val) {
  bm25Range.addEventListener('input', () => {
    bm25Val.textContent = bm25Range.value;
    uiSave();
  });
}

if (multihopCk) {
  multihopCk.addEventListener('change', () => {
    const on = multihopCk.checked;
    if (multihopDepthWrap) multihopDepthWrap.style.display = on ? '' : 'none';
    if (multihopFanoutWrap) multihopFanoutWrap.style.display = on ? '' : 'none';
    if (multihopFanout1Wrap) multihopFanout1Wrap.style.display = on ? '' : 'none';
    if (multihopBudgetWrap) multihopBudgetWrap.style.display = on ? '' : 'none';
    uiSave();
  });
}

if (rewriteCk) {
  rewriteCk.addEventListener('change', () => {
    if (rewriteNWrap) rewriteNWrap.style.display = rewriteCk.checked ? '' : 'none';
    uiSave();
  });
}

if (providerSel) {
  providerSel.addEventListener('change', async () => {
    await setProvider(providerSel.value);
    await loadHealth();
  });
}

function resetAdvancedDefaults() {
  try {
    if (topkInput) topkInput.value = '5';
    if (methodSel) methodSel.value = 'vector';

    if (bm25Range) {
      bm25Range.value = '0.5';
      if (bm25Val) bm25Val.textContent = bm25Range.value;
    }
    if (bm25Wrap) bm25Wrap.style.display = 'none';

    if (rerankCk) rerankCk.checked = false;
    if (rerankTopN) rerankTopN.value = '10';
    if (rrProvider) rrProvider.value = 'auto';
    if (rrMaxK) rrMaxK.value = '50';
    if (rrBatch) rrBatch.value = '16';
    if (rrThreads) rrThreads.value = '1';
    if (rerankTopWrap) rerankTopWrap.style.display = 'none';
    if (rerankAdv) rerankAdv.style.display = 'none';

    if (rewriteCk) rewriteCk.checked = false;
    if (rewriteN) rewriteN.value = '2';
    if (rewriteNWrap) rewriteNWrap.style.display = 'none';

    if (multihopCk) multihopCk.checked = false;
    if (hopDepth) hopDepth.value = '2';
    if (hopFanout) hopFanout.value = '2';
    if (hopFanout1) hopFanout1.value = '1';
    if (hopBudget) hopBudget.value = '0';
    if (multihopDepthWrap) multihopDepthWrap.style.display = 'none';
    if (multihopFanoutWrap) multihopFanoutWrap.style.display = 'none';
    if (multihopFanout1Wrap) multihopFanout1Wrap.style.display = 'none';
    if (multihopBudgetWrap) multihopBudgetWrap.style.display = 'none';

    // Trigger existing change handlers to keep UI consistent
    if (methodSel) methodSel.dispatchEvent(new Event('change'));
    if (rerankCk) rerankCk.dispatchEvent(new Event('change'));
    if (rewriteCk) rewriteCk.dispatchEvent(new Event('change'));
    if (multihopCk) multihopCk.dispatchEvent(new Event('change'));
  } catch (e) {
    console.warn('resetAdvancedDefaults error', e);
  }
}

if (advResetBtn) advResetBtn.addEventListener('click', resetAdvancedDefaults);

// ===== UI state (localStorage) =====
const UI_STATE_KEY = 'rag_ui_state';
function uiCollect() {
  try {
    return {
      provider: providerSel ? providerSel.value : undefined,
      topk: topkInput ? String(topkInput.value || '5') : undefined,
      method: methodSel ? methodSel.value : undefined,
      bm25: bm25Range ? String(bm25Range.value || '0.5') : undefined,
      rerank: rerankCk ? !!rerankCk.checked : undefined,
      rerank_topn: rerankTopN ? String(rerankTopN.value || '10') : undefined,
      rr_provider: rrProvider ? rrProvider.value : undefined,
      rr_maxk: rrMaxK ? String(rrMaxK.value || '50') : undefined,
      rr_batch: rrBatch ? String(rrBatch.value || '16') : undefined,
      rr_threads: rrThreads ? String(rrThreads.value || '1') : undefined,
      rewrite: rewriteCk ? !!rewriteCk.checked : undefined,
      rewrite_n: rewriteN ? String(rewriteN.value || '2') : undefined,
      multihop: multihopCk ? !!multihopCk.checked : undefined,
      depth: hopDepth ? String(hopDepth.value || '2') : undefined,
      fanout: hopFanout ? String(hopFanout.value || '2') : undefined,
      fanout1: hopFanout1 ? String(hopFanout1.value || '1') : undefined,
      budget: hopBudget ? String(hopBudget.value || '0') : undefined,
      stream: streamCk ? !!streamCk.checked : undefined,
      stats_collapsed: statsBody ? !!statsBody.hidden : undefined,
      docs_collapsed: docsBody ? !!docsBody.hidden : undefined,
      chats_collapsed: chatsBody ? !!chatsBody.hidden : undefined,
    };
  } catch { return {}; }
}
function uiSave() {
  try { localStorage.setItem(UI_STATE_KEY, JSON.stringify(uiCollect())); } catch {}
}
function uiLoad() {
  try {
    const raw = localStorage.getItem(UI_STATE_KEY) || '{}';
    const s = JSON.parse(raw);
    if (s.topk && topkInput) topkInput.value = String(s.topk);
    if (s.method && methodSel) methodSel.value = s.method;
    if (s.bm25 && bm25Range) { bm25Range.value = String(s.bm25); if (bm25Val) bm25Val.textContent = bm25Range.value; }
    if (typeof s.rerank === 'boolean' && rerankCk) rerankCk.checked = !!s.rerank;
    if (s.rerank_topn && rerankTopN) rerankTopN.value = String(s.rerank_topn);
    if (s.rr_provider && rrProvider) rrProvider.value = s.rr_provider;
    if (s.rr_maxk && rrMaxK) rrMaxK.value = String(s.rr_maxk);
    if (s.rr_batch && rrBatch) rrBatch.value = String(s.rr_batch);
    if (s.rr_threads && rrThreads) rrThreads.value = String(s.rr_threads);
    if (typeof s.rewrite === 'boolean' && rewriteCk) rewriteCk.checked = !!s.rewrite;
    if (s.rewrite_n && rewriteN) rewriteN.value = String(s.rewrite_n);
    if (typeof s.multihop === 'boolean' && multihopCk) multihopCk.checked = !!s.multihop;
    if (s.depth && hopDepth) hopDepth.value = String(s.depth);
    if (s.fanout && hopFanout) hopFanout.value = String(s.fanout);
    if (s.fanout1 && hopFanout1) hopFanout1.value = String(s.fanout1);
    if (s.budget && hopBudget) hopBudget.value = String(s.budget);
    if (typeof s.stream === 'boolean' && streamCk) streamCk.checked = !!s.stream;
    if (typeof s.stats_collapsed === 'boolean' && statsBody) statsBody.hidden = !!s.stats_collapsed;
    if (typeof s.docs_collapsed === 'boolean' && docsBody) { docsBody.hidden = !!s.docs_collapsed; if (docsToggleBtn) docsToggleBtn.setAttribute('aria-expanded', String(!docsBody.hidden)); }
    if (typeof s.chats_collapsed === 'boolean' && chatsBody) { chatsBody.hidden = !!s.chats_collapsed; if (chatsToggleBtn) chatsToggleBtn.setAttribute('aria-expanded', String(!chatsBody.hidden)); }
    // Trigger change handlers to sync visibility
    if (methodSel) methodSel.dispatchEvent(new Event('change'));
    if (rerankCk) rerankCk.dispatchEvent(new Event('change'));
    if (rewriteCk) rewriteCk.dispatchEvent(new Event('change'));
    if (multihopCk) multihopCk.dispatchEvent(new Event('change'));
  } catch {}
}

// Auto-save events for UI controls
function bindUiAutosave() {
  const bind = (el, evt='change') => { if (!el) return; el.addEventListener(evt, uiSave); };
  [topkInput, methodSel, bm25Range, rerankCk, rerankTopN, rrProvider, rrMaxK, rrBatch, rrThreads, rewriteCk, rewriteN, multihopCk, hopDepth, hopFanout, hopFanout1, hopBudget, streamCk].forEach(e => bind(e));
  if (statsToggleBtn && statsBody) {
    statsToggleBtn.addEventListener('click', () => { try { statsBody.hidden = !statsBody.hidden; uiSave(); } catch {} });
  }
  if (docsToggleBtn && docsBody) {
    docsToggleBtn.addEventListener('click', () => { try { docsBody.hidden = !docsBody.hidden; docsToggleBtn.setAttribute('aria-expanded', String(!docsBody.hidden)); uiSave(); } catch {} });
  }
  if (chatsToggleBtn && chatsBody) {
    chatsToggleBtn.addEventListener('click', () => { try { chatsBody.hidden = !chatsBody.hidden; chatsToggleBtn.setAttribute('aria-expanded', String(!chatsBody.hidden)); uiSave(); } catch {} });
  }
}

// ===== Toast notifications =====
const _toastContainer = () => {
  let el = document.getElementById('toasts');
  if (!el) {
    el = document.createElement('div');
    el.id = 'toasts';
    el.className = 'toasts';
    document.body.appendChild(el);
  }
  return el;
};
function toast(message, type = 'info', ms = 4000) {
  try {
    const c = _toastContainer();
    const t = document.createElement('div');
    t.className = `toast ${type}`;
    t.innerHTML = `<span class="msg"></span><span class="close" title="Đóng">✕</span>`;
    t.querySelector('.msg').textContent = String(message || '');
    t.querySelector('.close').addEventListener('click', () => { try { c.removeChild(t); } catch {} });
    c.appendChild(t);
    setTimeout(() => { try { c.removeChild(t); } catch {} }, ms);
  } catch (e) {
    console.warn('toast error', e);
  }
}
// Replace blocking alerts with non-blocking toasts
try { window.alert = (msg) => toast(msg, 'info'); } catch {}
// Toast helpers
function notifyError(msg) { try { toast(msg, 'error', 6000); } catch {} }
function notifySuccess(msg) { try { toast(msg, 'success', 3500); } catch {} }
function notifyWarn(msg) { try { toast(msg, 'warn', 4000); } catch {} }

// Quick Start overlay & keyboard shortcuts
const quickOverlay = document.getElementById('quickstart-overlay');
const quickModal = document.getElementById('quickstart-modal');
const quickClose = document.getElementById('quickstart-close');
const quickOk = document.getElementById('quickstart-ok');
function openQuickStart() {
  try { if (quickOverlay) quickOverlay.hidden = false; if (quickModal) quickModal.hidden = false; } catch {}
}
function closeQuickStart() {
  try { if (quickOverlay) quickOverlay.hidden = true; if (quickModal) quickModal.hidden = true; } catch {}
}
if (menuHelp) menuHelp.addEventListener('click', openQuickStart);
if (quickClose) quickClose.addEventListener('click', closeQuickStart);
if (quickOk) quickOk.addEventListener('click', closeQuickStart);
if (quickOverlay) quickOverlay.addEventListener('click', closeQuickStart);
window.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeQuickStart(); });

// Keyboard shortcuts: Enter to send, Ctrl+Enter toggle streaming
window.addEventListener('keydown', (e) => {
  try {
    const active = document.activeElement;
    if (!active) return;
    if (active === queryInput) {
      if (e.key === 'Enter' && e.ctrlKey) {
        if (streamCk) { streamCk.checked = !streamCk.checked; uiSave(); toast(`Streaming: ${streamCk.checked ? 'Bật' : 'Tắt'}`, 'info'); }
        e.preventDefault();
      } else if (e.key === 'Enter' && !e.shiftKey && !e.altKey && !e.metaKey) {
        if (askBtn) askBtn.click();
        e.preventDefault();
      }
    }
  } catch {}
});
