// ===== State Management =====
const state = {
  currentDB: null,
  currentChat: null,
  messages: [],
  provider: 'ollama'
};

// ===== DOM Elements =====
const sidebar = document.getElementById('sidebar');
const sidebarToggle = document.getElementById('sidebar-toggle');
const sidebarClose = document.getElementById('sidebar-close');
const dbSelect = document.getElementById('db-select');
const chatList = document.getElementById('chat-list');
const btnChatNew = document.getElementById('btn-chat-new');
const chatMessages = document.getElementById('chat-messages');
const inputQuery = document.getElementById('input-query');
const btnSend = document.getElementById('btn-send');
const fabAdd = document.getElementById('fab-add');
const btnSettings = document.getElementById('btn-settings');
const btnAnalytics = document.getElementById('btn-analytics');
const toastContainer = document.getElementById('toast-container');

// ===== Toast System =====
function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = message;
  toastContainer.appendChild(toast);
  
  setTimeout(() => {
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

// ===== Sidebar Toggle =====
sidebarToggle?.addEventListener('click', () => {
  sidebar?.classList.toggle('open');
});

sidebarClose?.addEventListener('click', () => {
  sidebar?.classList.remove('open');
});

// Close sidebar when clicking outside on mobile
document.addEventListener('click', (e) => {
  if (window.innerWidth <= 768) {
    if (!sidebar?.contains(e.target) && !sidebarToggle?.contains(e.target)) {
      sidebar?.classList.remove('open');
    }
  }
});

// ===== Modal System =====
const modals = {
  'modal-add': document.getElementById('modal-add'),
  'modal-settings': document.getElementById('modal-settings'),
  'modal-analytics': document.getElementById('modal-analytics')
};

function openModal(modalId) {
  const modal = modals[modalId];
  if (modal) {
    modal.hidden = false;
    document.body.style.overflow = 'hidden';
  }
}

function closeModal(modalId) {
  const modal = modals[modalId];
  if (modal) {
    modal.hidden = true;
    document.body.style.overflow = '';
  }
}

// Close button handlers
document.querySelectorAll('.modal-close').forEach(btn => {
  btn.addEventListener('click', () => {
    const modalId = btn.dataset.modal;
    closeModal(modalId);
  });
});

// Close on overlay click
document.querySelectorAll('.modal-overlay').forEach(overlay => {
  overlay.addEventListener('click', () => {
    const modal = overlay.closest('.modal');
    if (modal) {
      modal.hidden = true;
      document.body.style.overflow = '';
    }
  });
});

// Close on Escape key
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    Object.values(modals).forEach(modal => {
      if (modal && !modal.hidden) {
        modal.hidden = true;
        document.body.style.overflow = '';
      }
    });
  }
});

// Button handlers
fabAdd?.addEventListener('click', () => openModal('modal-add'));
btnSettings?.addEventListener('click', () => openModal('modal-settings'));
btnAnalytics?.addEventListener('click', () => openModal('modal-analytics'));

// ===== Tab System =====
document.querySelectorAll('.tab').forEach(tab => {
  tab.addEventListener('click', () => {
    const targetTab = tab.dataset.tab;
    
    // Update tab buttons
    tab.parentElement.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    
    // Update tab content
    const modal = tab.closest('.modal');
    modal.querySelectorAll('.tab-content').forEach(content => {
      content.classList.remove('active');
    });
    modal.querySelector(`#tab-${targetTab}`)?.classList.add('active');
  });
});

// ===== Load DBs =====
async function loadDBs() {
  try {
    const resp = await fetch('/api/dbs');
    const data = await resp.json();
    
    if (dbSelect) {
      dbSelect.innerHTML = '';
      data.dbs.forEach(db => {
        const opt = document.createElement('option');
        opt.value = db;
        opt.textContent = db;
        dbSelect.appendChild(opt);
      });
      
      if (data.dbs.length > 0) {
        state.currentDB = data.dbs[0];
        dbSelect.value = state.currentDB;
      }
    }
  } catch (e) {
    showToast('Lỗi load DBs: ' + e.message, 'error');
  }
}

// ===== Load Chats =====
async function loadChats() {
  try {
    const params = new URLSearchParams();
    if (state.currentDB) params.set('db', state.currentDB);
    
    const resp = await fetch('/api/chats?' + params.toString());
    const data = await resp.json();
    
    if (chatList) {
      chatList.innerHTML = '';
      data.chats.forEach(chat => {
        const li = document.createElement('li');
        li.textContent = chat.name || chat.id;
        li.dataset.chatId = chat.id;
        li.addEventListener('click', () => loadChat(chat.id));
        chatList.appendChild(li);
      });
    }
  } catch (e) {
    console.error('Load chats error:', e);
  }
}

// ===== Load Chat Messages =====
async function loadChat(chatId) {
  try {
    const params = new URLSearchParams();
    if (state.currentDB) params.set('db', state.currentDB);
    
    const resp = await fetch(`/api/chats/${chatId}?${params.toString()}`);
    const data = await resp.json();
    
    state.currentChat = chatId;
    state.messages = data.messages || [];
    
    renderMessages();
    
    // Update active chat in list
    chatList?.querySelectorAll('li').forEach(li => {
      li.classList.toggle('active', li.dataset.chatId === chatId);
    });
  } catch (e) {
    showToast('Lỗi load chat: ' + e.message, 'error');
  }
}

// ===== Render Messages =====
function renderMessages() {
  if (!chatMessages) return;
  
  chatMessages.innerHTML = '';
  
  if (state.messages.length === 0) {
    chatMessages.innerHTML = `
      <div class="welcome">
        <div class="welcome-icon">💡</div>
        <h2>Chào mừng!</h2>
        <p>Hỏi tôi về tài liệu của bạn</p>
      </div>
    `;
    return;
  }
  
  state.messages.forEach(msg => {
    const div = document.createElement('div');
    div.className = `message ${msg.role}`;
    
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = msg.role === 'user' ? '👤' : '🤖';
    
    const content = document.createElement('div');
    content.className = 'message-content';
    content.textContent = msg.content;
    
    div.appendChild(avatar);
    div.appendChild(content);
    
    // Add sources if available
    if (msg.sources && msg.sources.length > 0) {
      const sources = document.createElement('div');
      sources.className = 'message-sources';
      msg.sources.forEach(src => {
        const chip = document.createElement('div');
        chip.className = 'source-chip';
        chip.textContent = `📄 ${src}`;
        sources.appendChild(chip);
      });
      div.appendChild(sources);
    }
    
    chatMessages.appendChild(div);
  });
  
  // Scroll to bottom
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

// ===== Send Message =====
async function sendMessage() {
  const query = inputQuery?.value?.trim();
  if (!query) return;
  
  // Add user message to UI
  state.messages.push({ role: 'user', content: query });
  renderMessages();
  
  // Clear input
  if (inputQuery) inputQuery.value = '';
  
  try {
    const params = new URLSearchParams();
    if (state.currentDB) params.set('db', state.currentDB);
    params.set('query', query);
    if (state.currentChat) params.set('chat_id', state.currentChat);
    
    const resp = await fetch('/api/query?' + params.toString(), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        query, 
        db: state.currentDB,
        chat_id: state.currentChat,
        provider: state.provider
      })
    });
    
    const data = await resp.json();
    
    if (!resp.ok) throw new Error(data.detail || 'Query failed');
    
    // Add assistant response
    const sources = (data.metadatas || []).map(m => m.source).filter(Boolean);
    state.messages.push({ 
      role: 'assistant', 
      content: data.answer,
      sources: sources
    });
    
    renderMessages();
  } catch (e) {
    showToast('Lỗi: ' + e.message, 'error');
  }
}

// ===== Send Button Handler =====
btnSend?.addEventListener('click', sendMessage);

// ===== Enter to Send =====
inputQuery?.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

// ===== Auto-resize Textarea =====
inputQuery?.addEventListener('input', () => {
  inputQuery.style.height = 'auto';
  inputQuery.style.height = Math.min(inputQuery.scrollHeight, 160) + 'px';
});

// ===== New Chat =====
btnChatNew?.addEventListener('click', () => {
  state.currentChat = null;
  state.messages = [];
  renderMessages();
  chatList?.querySelectorAll('li').forEach(li => li.classList.remove('active'));
  showToast('Hội thoại mới đã tạo', 'success');
  sidebar?.classList.remove('open');
});

// ===== DB Change =====
dbSelect?.addEventListener('change', () => {
  state.currentDB = dbSelect.value;
  state.currentChat = null;
  state.messages = [];
  renderMessages();
  loadChats();
});

// ===== Add Documents =====
const fileUpload = document.getElementById('file-upload');
const inputUrl = document.getElementById('input-url');
const btnAddDocs = document.getElementById('btn-add-docs');
const addStatus = document.getElementById('add-status');

btnAddDocs?.addEventListener('click', async () => {
  const files = fileUpload?.files;
  const url = inputUrl?.value?.trim();
  
  if (!files?.length && !url) {
    showToast('Chọn file hoặc nhập URL', 'error');
    return;
  }
  
  try {
    btnAddDocs.disabled = true;
    btnAddDocs.textContent = '⏳ Đang xử lý...';
    
    if (files?.length > 0) {
      const fd = new FormData();
      Array.from(files).forEach(f => fd.append('files', f));
      if (state.currentDB) fd.append('db', state.currentDB);
      
      const resp = await fetch('/api/upload', {
        method: 'POST',
        body: fd
      });
      
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.detail || 'Upload failed');
      
      showToast(`✅ Đã thêm ${data.saved?.length || 0} file`, 'success');
      
      if (fileUpload) fileUpload.value = '';
    } else if (url) {
      const params = new URLSearchParams();
      if (state.currentDB) params.set('db', state.currentDB);
      params.set('paths', url);
      
      const resp = await fetch('/api/ingest_by_paths?' + params.toString(), {
        method: 'POST'
      });
      
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.detail || 'Ingest failed');
      
      showToast(`✅ Đã thêm từ URL`, 'success');
      
      if (inputUrl) inputUrl.value = '';
    }
    
    closeModal('modal-add');
  } catch (e) {
    showToast('Lỗi: ' + e.message, 'error');
  } finally {
    btnAddDocs.disabled = false;
    btnAddDocs.textContent = '➕ Thêm';
  }
});

// ===== Settings Handlers =====
const btnCreateDb = document.getElementById('btn-create-db');
const btnDeleteDb = document.getElementById('btn-delete-db');
const inputNewDb = document.getElementById('input-new-db');

btnCreateDb?.addEventListener('click', async () => {
  const name = inputNewDb?.value?.trim();
  if (!name) {
    showToast('Nhập tên DB', 'error');
    return;
  }
  
  try {
    const resp = await fetch(`/api/dbs/${name}`, { method: 'POST' });
    const data = await resp.json();
    
    if (!resp.ok) throw new Error(data.detail || 'Create failed');
    
    showToast('✅ Đã tạo DB: ' + name, 'success');
    await loadDBs();
    if (inputNewDb) inputNewDb.value = '';
  } catch (e) {
    showToast('Lỗi: ' + e.message, 'error');
  }
});

btnDeleteDb?.addEventListener('click', async () => {
  if (!state.currentDB) return;
  
  if (!confirm(`Xóa DB "${state.currentDB}"? Không thể hoàn tác!`)) return;
  
  try {
    const resp = await fetch(`/api/dbs/${state.currentDB}`, { method: 'DELETE' });
    const data = await resp.json();
    
    if (!resp.ok) throw new Error(data.detail || 'Delete failed');
    
    showToast('✅ Đã xóa DB', 'success');
    await loadDBs();
  } catch (e) {
    showToast('Lỗi: ' + e.message, 'error');
  }
});

// ===== Load Analytics =====
async function loadAnalytics() {
  try {
    const params = new URLSearchParams();
    if (state.currentDB) params.set('db', state.currentDB);
    
    const resp = await fetch('/api/analytics/db?' + params.toString());
    const data = await resp.json();
    
    if (!resp.ok) return;
    
    document.getElementById('stat-chats').textContent = data.chats || '-';
    document.getElementById('stat-qa').textContent = data.qa_pairs || '-';
    document.getElementById('stat-answered').textContent = data.answered || '-';
    document.getElementById('stat-context').textContent = data.with_contexts || '-';
  } catch (e) {
    console.error('Load analytics error:', e);
  }
}

// Load analytics when modal opens
btnAnalytics?.addEventListener('click', loadAnalytics);

// ===== Backend Status =====
const backendStatus = document.getElementById('backend-status');

async function checkBackend() {
  try {
    const resp = await fetch('/api/health');
    if (resp.ok) {
      backendStatus?.classList.add('online');
      backendStatus?.setAttribute('title', 'Backend connected');
    }
  } catch (e) {
    backendStatus?.classList.remove('online');
    backendStatus?.setAttribute('title', 'Backend offline');
  }
}

// Check backend every 30s
checkBackend();
setInterval(checkBackend, 30000);

// ===== Initialize =====
loadDBs().then(() => {
  loadChats();
});

console.log('✅ Ollama RAG UI v2 loaded!');
