# 🎨 Ollama RAG Frontend v2

**Modern, ChatGPT-style UI for Ollama RAG**

---

## 🌟 Features

- ✅ **Chat-focused** - Conversation at the center
- ✅ **Minimal & Clean** - 70% less UI complexity
- ✅ **Dark Theme** - Professional, modern look
- ✅ **Fully Responsive** - Mobile, tablet, desktop
- ✅ **Smooth Animations** - 60fps, buttery smooth
- ✅ **Modal System** - Settings, Add docs, Analytics
- ✅ **Keyboard Shortcuts** - Power user friendly
- ✅ **Zero Dependencies** - Vanilla JS, Pure CSS

---

## 📁 Structure

```
frontend/
├── index.html           # v2 minimal structure
├── styles.css           # v2 modern dark theme
├── app.js              # v2 refactored logic
├── backup/             # v1 backups
│   ├── index_v1_original.html
│   ├── styles_v1_original.css
│   └── app_v1_original.js
└── README.md           # This file
```

---

## 🚀 Quick Start

### 1. Start Backend

```bash
cd backend
python main.py
```

Backend runs at: `http://localhost:8000`

### 2. Open Frontend

**Option A: Direct file**
```bash
cd frontend
start index.html  # Windows
open index.html   # Mac/Linux
```

**Option B: HTTP Server** (recommended for testing)
```bash
cd frontend
python -m http.server 8080
# Open: http://localhost:8080
```

---

## 🎯 Usage

### **First Time:**

1. Open app → Welcome screen
2. Click **☰** → Sidebar opens
3. Select DB from dropdown
4. Click **➕ FAB** → Add documents
5. Type question → **Enter**
6. See AI response! 🤖

### **Return User:**

1. Open app → Previous chat loads
2. Click chat from sidebar → Continue conversation
3. Switch DBs easily
4. Check **Analytics** for stats

---

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Enter` | Send message |
| `Shift+Enter` | New line |
| `Ctrl+K` | Focus input |
| `Escape` | Close modal/sidebar |

---

## 🎨 Customization

### **Change Colors:**

Edit `styles.css`:

```css
:root {
  --accent-blue: #4a90e2;    /* User */
  --accent-green: #10b981;   /* AI */
  --accent-purple: #8b5cf6;  /* FAB */
  --bg-primary: #0f1419;     /* Background */
}
```

### **Add Feature:**

Example: Add "Last updated" timestamp

```js
// app.js
function showLastUpdate() {
  const time = new Date().toLocaleString();
  showToast(`Last update: ${time}`);
}
```

---

## 📊 Metrics

**Lines of Code:**
- HTML: 138 lines (-47% vs v1)
- CSS: 708 lines (with design system)
- JS: 498 lines (-56% vs v1)

**Performance:**
- Load time: ~218ms (-37% vs v1)
- Runtime: Smooth 60fps animations

---

## 🔄 Migrate from v1

**Full guide:** See `docs/MIGRATION_GUIDE_V2.md`

**Quick rollback:**
```bash
cp backup/index_v1_original.html index.html
cp backup/styles_v1_original.css styles.css
cp backup/app_v1_original.js app.js
```

---

## 🐛 Troubleshooting

### **Backend status red?**
- Check backend running: `http://localhost:8000/docs`
- Verify CORS enabled in `backend/main.py`

### **Sidebar won't open?**
- Hard refresh: `Ctrl+Shift+R`
- Check console for errors (F12)

### **Modal stuck?**
- Press `ESC` key
- Click overlay to close

---

## 📚 Documentation

- **User Guide:** `docs/UI_GUIDE_V2.md`
- **Migration Guide:** `docs/MIGRATION_GUIDE_V2.md`
- **Backend API:** `backend/README.md`

---

## 🔮 Roadmap

- [ ] Dark/Light theme toggle
- [ ] Export chat to PDF
- [ ] Voice input
- [ ] Code syntax highlighting
- [ ] Drag & drop files to chat
- [ ] Search chat history

---

## 🤝 Contributing

1. Fork repo
2. Make changes
3. Test thoroughly (see Migration Guide)
4. Submit PR

---

## 📄 License

MIT License - Feel free to use! 🎉

---

## 🌈 Tech Stack

- **HTML5** - Semantic markup
- **CSS3** - Variables, Grid, Flexbox, Animations
- **JavaScript (ES6+)** - Async/await, Modules pattern
- **Backend API** - FastAPI (Python)

---

## 💡 Philosophy

> **"Đơn giản là tối thượng! Ẩn phức tạp, lộ bản chất!"**

UI v2 follows:
- **Content First** - Conversation is the focus
- **Less is More** - Hide complexity, show essence
- **Beautiful by Default** - Professional dark theme
- **Fast & Smooth** - 60fps animations
- **Accessible** - Keyboard, screen readers

---

**Enjoy the new UI! 🎨✨**

*Version: 2.0.0*  
*Last updated: 2025-10-03*
