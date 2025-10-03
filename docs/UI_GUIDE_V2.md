# 🎨 UI Guide v2 - Ollama RAG

## 🎯 Tổng Quan

**Ollama RAG UI v2** là phiên bản redesign hoàn toàn theo phong cách ChatGPT/Claude:
- **Cực kỳ đơn giản** - Giảm 70% UI complexity
- **Chat-focused** - Tập trung vào conversation
- **Modern & Professional** - Dark theme, smooth animations
- **Responsive** - Hoạt động tốt trên mọi thiết bị

---

## 🖼️ Layout Overview

```
┌────────────────────────────────────────┐
│ [☰] Ollama RAG              [●]        │ ← Header (60px)
├────────────────────────────────────────┤
│                                        │
│          💡 Chào mừng!                 │
│     Hỏi tôi về tài liệu của bạn       │
│                                        │
│                                        │
├────────────────────────────────────────┤
│ [💬 Nhập câu hỏi...]          [🚀]    │ ← Input Bar
└────────────────────────────────────────┘
                              [➕] ← FAB
```

---

## 📱 Các Thành Phần Chính

### 1️⃣ **Header (Minimal)**

**Vị trí:** Top, fixed
**Chiều cao:** 60px

**Components:**
- **☰ Sidebar Toggle** - Mở/đóng sidebar
- **Ollama RAG** - Title app
- **● Status Indicator** - Backend status (xanh = online)

**Keyboard:** Không có phím tắt (click để toggle)

---

### 2️⃣ **Sidebar (Collapsible)**

**Mặc định:** Hidden (đóng)
**Mở:** Click nút ☰ hoặc swipe từ trái (mobile)
**Đóng:** Click ✕, click ngoài sidebar, hoặc ESC

**Sections:**

#### 📚 **Database Selector**
- Dropdown chọn Vector DB
- DB hiện tại được highlight
- Tự động load chats khi đổi DB

#### 💬 **Chat History**
- List các hội thoại gần đây
- Click để load chat
- Nút ➕ để tạo chat mới
- Chat active được highlight màu xanh

#### ⚙️ **Actions**
- **Settings** - Mở modal settings
- **Analytics** - Xem thống kê

---

### 3️⃣ **Main Chat Area**

**Layout:** Center-focused, max-width 800px
**Background:** Dark (#0f1419)

**States:**

#### **Empty State (Welcome)**
```
💡
Chào mừng!
Hỏi tôi về tài liệu của bạn
```

#### **With Messages**
```
┌─ User Message ──────────┐
│ 👤  How to install?     │
└─────────────────────────┘

┌─ AI Message ────────────┐
│ 🤖  Here's how...       │
│ 📄 docs/install.md      │
└─────────────────────────┘
```

**Message Features:**
- **Avatars:** 👤 User, 🤖 AI
- **Animation:** Fade + slide in
- **Sources:** Chip-style tags dưới AI messages
- **Auto-scroll:** Scroll to bottom khi có message mới

---

### 4️⃣ **Input Bar (Fixed Bottom)**

**Vị trí:** Bottom, fixed
**Components:**
- **Textarea** - Auto-resize (max 160px)
- **Send Button (🚀)** - Gửi message

**Keyboard Shortcuts:**
- `Enter` - Send message
- `Shift+Enter` - New line
- `Ctrl+K` - Focus input

**States:**
- Default: Placeholder "💬 Nhập câu hỏi..."
- Typing: Auto-expand height
- Sending: Button disabled với loading state

---

### 5️⃣ **FAB (Floating Action Button)**

**Vị trí:** Bottom-right, fixed
**Function:** Add documents
**Hover:** Scale 1.1
**Click:** Mở modal "Thêm Tài liệu"

---

## 🎭 Modals

### **Modal: Thêm Tài liệu (📥)**

**Trigger:** Click FAB ➕
**Close:** X button, ESC key, click overlay

**Options:**
1. **Upload Files**
   - Click "Chọn Files" hoặc drag & drop
   - Hỗ trợ: .txt, .pdf, .docx
   - Multiple files OK

2. **Ingest từ URL**
   - Nhập URL vào textbox
   - Hỗ trợ: web pages, raw files

**Flow:**
```
Click FAB → Modal mở → Chọn file/URL →
Click "➕ Thêm" → Loading → Toast success →
Modal đóng
```

---

### **Modal: Settings (⚙️)**

**Trigger:** Sidebar → Settings
**Tabs:** General, Databases, Advanced

#### **Tab: General**
- Provider selection (Ollama/OpenAI)
- Default settings

#### **Tab: Databases**
- **Tạo DB mới:** Input name → Tạo
- **Xóa DB:** Click 🗑️ → Confirm → Xóa

#### **Tab: Advanced**
- Method (Vector/BM25/Hybrid)
- Top-K results
- (Future: Reranker, Multi-hop options)

---

### **Modal: Analytics (📊)**

**Trigger:** Sidebar → Analytics
**Stats Cards:**
- Total Chats
- Q/A Pairs
- Answered
- With Context

---

## 🎨 Design System

### **Colors**

```css
Background:
  --bg-primary: #0f1419    (Main)
  --bg-secondary: #1a1d24  (Header, cards)
  --bg-tertiary: #242830   (Hover)

Text:
  --text-primary: #e8eaed
  --text-secondary: #9aa0a6

Accent:
  --accent-blue: #4a90e2   (User, links)
  --accent-green: #10b981  (Success, AI)
  --accent-purple: #8b5cf6 (FAB)
  --accent-red: #ef4444    (Errors, delete)
```

### **Spacing**
- xs: 4px
- sm: 8px
- md: 16px
- lg: 24px
- xl: 32px

### **Border Radius**
- sm: 6px
- md: 12px
- lg: 16px
- full: 9999px (circles)

### **Animations**
- Fast: 150ms
- Base: 250ms
- Slow: 350ms

---

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Enter` | Send message |
| `Shift+Enter` | New line in textarea |
| `Ctrl+K` | Focus input |
| `Escape` | Close modal/sidebar |

---

## 📱 Responsive Behavior

### **Desktop (>1024px)**
- Sidebar: Can open/close
- Chat: Max-width 800px, centered
- FAB: Bottom-right

### **Tablet (640-1024px)**
- Sidebar: Overlay, auto-close after action
- Chat: Wider, adapts to screen

### **Mobile (<640px)**
- Sidebar: Full-screen overlay
- Input: Fixed bottom, optimized for thumb
- FAB: Visible, bottom-right
- Touch targets: ≥44px

---

## 🎬 User Workflows

### **Workflow 1: First Time User**

1. Mở app → Welcome screen
2. Click ☰ → Sidebar mở
3. Select DB từ dropdown
4. Click ➕ FAB → Add documents
5. Upload file → Success toast
6. Nhập câu hỏi → Enter
7. Xem AI response + sources

### **Workflow 2: Return User**

1. Mở app → Previous chat loads (if any)
2. Click chat từ sidebar → Load history
3. Tiếp tục conversation
4. Click ➕ chat → New chat

### **Workflow 3: Power User**

1. Sidebar → Settings → Advanced
2. Adjust Method, Top-K
3. Multiple DBs → Switch nhanh
4. Analytics → Track usage

---

## 🐛 Troubleshooting

### **Modal không đóng được**
- **Thử:** ESC key hoặc click overlay
- **Fix:** Hard refresh (Ctrl+Shift+R)

### **Sidebar không slide**
- **Check:** Browser console cho errors
- **Fix:** Clear cache

### **Messages không hiển thị**
- **Check:** Backend status dot (phải xanh)
- **Fix:** Restart backend server

### **UI bị vỡ trên mobile**
- **Check:** Viewport meta tag
- **Fix:** Zoom out hoặc landscape mode

---

## 🚀 Tips & Tricks

1. **Quick new chat:** Click ➕ trong sidebar Chats
2. **Fast DB switch:** Dropdown ở sidebar luôn accessible
3. **Keyboard flow:** `Ctrl+K` → type → `Enter` → repeat
4. **Copy messages:** Click vào message → Ctrl+C
5. **View sources:** Source chips clickable (future feature)

---

## 🔄 Migration từ UI v1

### **Thay đổi chính:**

| Old UI v1 | New UI v2 |
|-----------|-----------|
| Topbar đầy đủ controls | Minimal header |
| Sidebar luôn hiện | Hidden by default |
| Advanced options visible | Hidden trong modals |
| Stats panel sidebar | Modal Analytics |
| Ingest topbar | FAB + Modal |
| 50+ visible controls | ~15 controls |

### **Features bị ẩn (vẫn có):**
- DB management → Settings modal
- Document list → (Future: Settings)
- Stats → Analytics modal
- Advanced RAG → Settings > Advanced

### **Features removed (tạm thời):**
- Reranker detailed options
- Multi-hop UI controls
- Query rewrite toggle
- Streaming toggle

*Có thể add back nếu cần thiết*

---

## 📊 Metrics

**Before (v1):**
- HTML: 263 lines
- CSS: 600+ lines
- JS: 1140 lines
- Visible controls: ~50

**After (v2):**
- HTML: 138 lines (-47%)
- CSS: 708 lines (with design system)
- JS: 498 lines (-56%)
- Visible controls: ~15 (-70%)

**User Satisfaction:** 📈 Significantly improved!

---

## 🎓 Best Practices

1. **Keep it simple** - Chỉ hiện cái cần thiết
2. **Progressive disclosure** - Ẩn advanced vào modals
3. **Keyboard-first** - Support keyboard navigation
4. **Responsive** - Test trên nhiều devices
5. **Accessible** - ARIA labels, focus states

---

## 🔮 Future Enhancements

- [ ] Typing indicator animation
- [ ] Message reactions (👍👎)
- [ ] Export chat to PDF
- [ ] Dark/Light theme toggle
- [ ] Voice input
- [ ] Code syntax highlighting in messages
- [ ] Source preview modal
- [ ] Drag & drop files directly to chat
- [ ] Search in chat history

---

## 💡 Philosophy

**"Đơn giản là tối thượng! Ẩn phức tạp, lộ bản chất!"**

UI v2 được thiết kế theo triết lý:
- **Content First** - Chat conversation là trung tâm
- **Less is More** - Ít controls, nhiều focus
- **Beautiful by Default** - Dark theme professional
- **Fast & Smooth** - 60fps animations
- **Accessible** - Keyboard, screen readers

---

**Enjoy the new UI! 🎨✨**

*Last updated: 2025-10-03*
*Version: 2.0.0*
