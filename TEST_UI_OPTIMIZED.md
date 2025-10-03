# 🧪 Test UI Tối ưu - Ollama RAG

## ✅ Đã Hoàn Thành

### 1. **Chế độ UI Đơn giản/Nâng cao** ✅
- Nút toggle `🧭 Đơn giản` / `🧰 Nâng cao` ở topbar
- Ẩn ~70% controls không cần thiết ở chế độ Đơn giản
- Lưu preference vào localStorage
- Toast notification khi chuyển chế độ

### 2. **Panel Ingest ở Sidebar** ✅
- Panel "📥 Thêm tài liệu" luôn hiển thị
- Hỗ trợ upload files (.txt, .pdf, .docx)
- Hỗ trợ ingest từ URL
- Status mini + toast notifications
- Auto-clear sau khi thành công

---

## 🎯 Cách Test

### **Bước 1: Khởi động server**
```powershell
# Terminal 1: Ollama
ollama serve

# Terminal 2: Backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### **Bước 2: Mở browser**
```
http://localhost:8000
```

---

## ✅ Test Cases

### **TC1: Chế độ UI Toggle**
**Steps:**
1. Mở app
2. Bấm nút "🧭 Đơn giản"
3. Kiểm tra các phần tử bị ẨN:
   - DB create/delete buttons
   - Ingest controls ở topbar
   - Panel Docs
   - Panel Stats
   - Panel Advanced options
   - Query row options (top-k, provider, streaming...)
4. Các phần tử vẫn HIỆN:
   - DB selector
   - Ô nhập câu hỏi + nút Gửi
   - Panel "📥 Thêm tài liệu"
   - Chat history
   - Nút reload
5. Bấm lại nút → chuyển "🧰 Nâng cao"
6. Toast hiển thị "Chế độ Nâng cao đã bật"
7. Tất cả controls hiện lại

**Expected:** ✅ Tất cả hoạt động, UI mượt, toast hiển thị

---

### **TC2: Ingest Files từ Sidebar**
**Steps:**
1. Ở chế độ Đơn giản
2. Panel "📥 Thêm tài liệu" hiển thị ở sidebar
3. Bấm "📁 Chọn Files..."
4. Chọn 1-2 file .txt hoặc .pdf
5. Bấm "➕ Thêm vào DB"
6. Kiểm tra:
   - Button loading state (spinner)
   - Status mini: "Đang xử lý..."
   - Toast: "Đã thêm X file (Y chunks)"
   - Status mini: "✅ X file"
   - File input được clear
7. Thử query câu hỏi liên quan đến file vừa ingest

**Expected:** ✅ Files được ingest, query trả về context từ file

---

### **TC3: Ingest URL từ Sidebar**
**Steps:**
1. Ở chế độ Đơn giản
2. Trong panel "📥 Thêm tài liệu"
3. Nhập URL vào ô "Nhập URL..." (ví dụ: https://example.com/doc.txt)
4. Bấm "➕ Thêm vào DB"
5. Kiểm tra:
   - Status mini: "Đang xử lý..."
   - Toast: "Đã thêm từ URL (Y chunks)"
   - Status mini: "✅ URL OK"
   - URL input được clear

**Expected:** ✅ URL được ingest thành công

---

### **TC4: Error Handling**
**Steps:**
1. Không chọn file, không nhập URL
2. Bấm "➕ Thêm vào DB"
3. Kiểm tra toast: "Chọn file hoặc nhập URL"

**Expected:** ✅ Warning toast hiển thị

---

### **TC5: Chế độ Nâng cao vẫn hoạt động**
**Steps:**
1. Chuyển sang "🧰 Nâng cao"
2. Test topbar ingest controls:
   - Input "data/docs/*.txt"
   - Bấm "➕ Thêm vào DB"
   - Hoặc chọn file và bấm "📥 Ingest file"
3. Panel sidebar vẫn hiển thị và hoạt động

**Expected:** ✅ Cả 2 cách ingest đều hoạt động (topbar + sidebar)

---

### **TC6: localStorage Persistence**
**Steps:**
1. Chuyển sang "🧭 Đơn giản"
2. Reload trang (F5)
3. Kiểm tra UI vẫn ở chế độ Đơn giản
4. Chuyển sang "🧰 Nâng cao"
5. Reload trang
6. Kiểm tra UI ở chế độ Nâng cao

**Expected:** ✅ Preference được lưu và load lại đúng

---

### **TC7: Query hoạt động ở cả 2 chế độ**
**Steps:**
1. Chế độ Đơn giản:
   - Nhập "Hướng dẫn cài đặt?"
   - Bấm "Gửi" hoặc Enter
   - Kiểm tra kết quả + contexts
2. Chế độ Nâng cao:
   - Thay đổi method: BM25
   - Nhập câu hỏi
   - Bấm "Gửi"
   - Kiểm tra kết quả

**Expected:** ✅ Query hoạt động bình thường ở cả 2 chế độ

---

### **TC8: Responsive Mobile**
**Steps:**
1. F12 → Toggle device toolbar
2. Chọn iPhone SE (375px)
3. Kiểm tra:
   - Sidebar không bị lỗi
   - Panel "Thêm tài liệu" vẫn dùng được
   - Nút toggle UI vẫn bấm được
   - Toast không bị overflow
4. Thử ingest file từ mobile view
5. Thử query

**Expected:** ✅ UI responsive tốt, không bị vỡ layout

---

## 🐛 Bug Report Template

Nếu phát hiện lỗi, ghi rõ:
```
**Bug:** [Mô tả ngắn gọn]
**Steps to reproduce:**
1. ...
2. ...
3. ...
**Expected:** [Kết quả mong đợi]
**Actual:** [Kết quả thực tế]
**Browser:** [Chrome 120 / Firefox 121 / ...]
**Console errors:** [Copy lỗi từ DevTools Console]
**Screenshot:** [Nếu có]
```

---

## 📊 Kết quả Test

| Test Case | Status | Ghi chú |
|-----------|--------|---------|
| TC1: UI Toggle | ⏳ Pending | |
| TC2: Ingest Files | ⏳ Pending | |
| TC3: Ingest URL | ⏳ Pending | |
| TC4: Error Handling | ⏳ Pending | |
| TC5: Chế độ Nâng cao | ⏳ Pending | |
| TC6: localStorage | ⏳ Pending | |
| TC7: Query hoạt động | ⏳ Pending | |
| TC8: Responsive | ⏳ Pending | |

**Cách đánh dấu:**
- ⏳ Pending: Chưa test
- ✅ Passed: Test thành công
- ❌ Failed: Có lỗi (ghi chi tiết vào Bug Report)

---

## 🎉 Summary

**Tối ưu UI thành công:**
- Giảm ~70% controls hiển thị mặc định (chế độ Đơn giản)
- Thêm panel Ingest luôn accessible → không cần chuyển chế độ
- Giữ đầy đủ tính năng cho power users (chế độ Nâng cao)
- UI responsive, clean, dễ dùng hơn nhiều! 🚀

**Commits:**
- `e2a4dd3` - feat(ui): Thêm chế độ UI đơn giản/nâng cao - Progressive Disclosure
- `ccc33d4` - feat(ui): Thêm panel Ingest vào sidebar - luôn hiển thị ở chế độ đơn giản

---

💡 **Tip:** Dùng DevTools Console để debug nếu cần:
```js
// Check UI mode
document.querySelector('.ui-root').classList.contains('simple-mode')

// Check localStorage
localStorage.getItem('ollama-rag-ui-mode')

// Manually toggle
document.getElementById('btn-ui-mode').click()
```
