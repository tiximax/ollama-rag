# 🚀 Ollama RAG - Production Deployment Guide

**Deploy local Ollama + FastAPI to internet via Cloudflare Tunnel**

---

## 📋 **Prerequisites**

### **Required:**
- ✅ Windows 10/11
- ✅ Python 3.9+ (Đã có: 3.12.10)
- ✅ Ollama installed & running
- ✅ Models: `llama3.2:3b`, `nomic-embed-text` (Đã pull!)
- ✅ Cloudflare account (free tier OK)
- ✅ Domain name (có thể dùng subdomain miễn phí từ Cloudflare)

### **Optional:**
- Git (for version control)
- GPU (for faster inference)

---

## 🎯 **Deployment Architecture**

```
┌─────────────────────────────────────────────────────────┐
│  Your PC (Windows)                                      │
│  ┌──────────────┐      ┌─────────────────┐            │
│  │ Ollama       │ ───▶ │ FastAPI (8000)  │            │
│  │ (11434)      │      │ + RAG Engine    │            │
│  └──────────────┘      └────────┬────────┘            │
│                                  │                      │
│                      ┌───────────▼──────────┐          │
│                      │ Cloudflare Tunnel    │          │
│                      │ (cloudflared)        │          │
│                      └───────────┬──────────┘          │
└──────────────────────────────────┼──────────────────────┘
                                   │ Encrypted
                       ┌───────────▼───────────┐
                       │ Cloudflare Edge       │
                       │ (Global CDN)          │
                       └───────────┬───────────┘
                                   │ HTTPS
                       ┌───────────▼───────────┐
                       │ 🌐 Public Internet   │
                       │ yourdomain.com        │
                       └───────────────────────┘
```

**Benefits:**
- ✅ No port forwarding needed
- ✅ Automatic HTTPS/SSL
- ✅ DDoS protection (Cloudflare)
- ✅ Global CDN acceleration
- ✅ Keep Ollama local (GPU/CPU optimization)

---

## 🚀 **Quick Start (3 steps)**

### **Step 1: Deploy Application**

```powershell
# Clone repo (if not already)
git clone https://github.com/yourusername/ollama-rag
cd ollama-rag

# Run deployment script (automatic setup!)
.\deploy.ps1
```

**What it does:**
1. ✅ Check Python & Ollama
2. ✅ Pull required models (if missing)
3. ✅ Create virtual environment
4. ✅ Install dependencies
5. ✅ Setup production config
6. ✅ Start FastAPI server

**Expected output:**
```
🚀 Ollama RAG - Production Deployment
======================================

✅ Python installed: Python 3.12.10
✅ Ollama installed
✅ Models ready
✅ Virtual environment ready
✅ Dependencies installed
✅ Production config loaded
✅ Data directories ready

========================================
🎉 Ready to launch!
========================================

🌐 Local URL: http://localhost:8000
📚 API Docs: http://localhost:8000/docs
💚 Health: http://localhost:8000/health

INFO:     Uvicorn running on http://0.0.0.0:8000
```

✅ **App is now running locally!**

---

### **Step 2: Setup Cloudflare Tunnel**

#### **2.1. Install cloudflared**

**Option A: Winget (Recommended)**
```powershell
winget install --id Cloudflare.cloudflared
```

**Option B: Chocolatey**
```powershell
choco install cloudflared
```

**Option C: Manual**
```powershell
# Download
Invoke-WebRequest -Uri "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe" -OutFile "cloudflared.exe"

# Move to PATH
Move-Item cloudflared.exe C:\Windows\System32\cloudflared.exe
```

**Verify:**
```powershell
cloudflared --version
# Output: cloudflared version 2024.x.x
```

#### **2.2. Login to Cloudflare**

```powershell
cloudflared tunnel login
```

**What happens:**
1. Browser opens → Login to Cloudflare
2. Select your domain
3. Certificate saved to: `C:\Users\<username>\.cloudflared\cert.pem`

#### **2.3. Create Tunnel**

```powershell
cloudflared tunnel create ollama-rag
```

**Output:**
```
Tunnel credentials written to C:\Users\pc\.cloudflared\abc123-xyz.json
Created tunnel ollama-rag with id abc123-xyz
```

**📝 Note:** Save the tunnel ID (`abc123-xyz`)!

#### **2.4. Configure Tunnel**

Create config file:
```powershell
# Create directory if not exists
New-Item -Path "$env:USERPROFILE\.cloudflared" -ItemType Directory -Force

# Edit config
notepad "$env:USERPROFILE\.cloudflared\config.yml"
```

**Paste this (replace placeholders):**
```yaml
tunnel: abc123-xyz
credentials-file: C:\Users\pc\.cloudflared\abc123-xyz.json

ingress:
  - hostname: ollama-rag.yourdomain.com
    service: http://localhost:8000
  - service: http_status:404
```

**Replace:**
- `abc123-xyz` → Your actual tunnel ID
- `ollama-rag.yourdomain.com` → Your desired subdomain

#### **2.5. Setup DNS**

```powershell
cloudflared tunnel route dns abc123-xyz ollama-rag.yourdomain.com
```

**Or manually:**
1. Go to Cloudflare Dashboard → DNS
2. Add CNAME record:
   - **Name:** `ollama-rag`
   - **Target:** `abc123-xyz.cfargotunnel.com`
   - **Proxy:** Enabled (orange cloud)

---

### **Step 3: Start Tunnel & Test**

#### **3.1. Run Tunnel (Foreground - for testing)**

```powershell
cloudflared tunnel run ollama-rag
```

**Expected output:**
```
2025-10-03 INFO  Connection established
2025-10-03 INFO  Registered tunnel ollama-rag
2025-10-03 INFO  Serving at https://ollama-rag.yourdomain.com
```

#### **3.2. Test Deployment**

Open browser:
```
https://ollama-rag.yourdomain.com/docs
https://ollama-rag.yourdomain.com/health
```

**Expected response (health):**
```json
{
  "status": "healthy",
  "ollama_status": "connected",
  "ollama_url": "http://localhost:11434",
  "available_models": ["llama3.2:3b", "nomic-embed-text"],
  "timestamp": "2025-10-03T12:00:00Z"
}
```

✅ **Deployment successful!** 🎉

---

## 🔧 **Production Setup (Run as Service)**

### **Install as Windows Service**

```powershell
# Install service
cloudflared service install

# Start service
Start-Service cloudflared

# Check status
Get-Service cloudflared
```

**Service will auto-start on Windows boot!**

### **Service Management**

```powershell
# Stop
Stop-Service cloudflared

# Restart
Restart-Service cloudflared

# Uninstall
cloudflared service uninstall
```

---

## 📊 **Monitoring & Logs**

### **Application Logs**

```powershell
# View FastAPI logs (if running via deploy.ps1)
# Logs appear in terminal

# Or run with file logging
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-config logging.json
```

### **Tunnel Logs**

```powershell
# Live logs (if running foreground)
cloudflared tunnel run --loglevel debug ollama-rag

# Service logs
Get-EventLog -LogName Application -Source cloudflared -Newest 20
```

### **Cloudflare Dashboard**

- Analytics: https://dash.cloudflare.com → Analytics
- Traffic: Real-time visitor stats
- Security: WAF events, rate limiting

---

## 🔐 **Security Hardening**

### **1. Enable Cloudflare Access (Free!)**

Add authentication layer:

1. Cloudflare Dashboard → Zero Trust → Access → Applications
2. Create new application:
   - **Application name:** Ollama RAG
   - **Application domain:** `ollama-rag.yourdomain.com`
3. Add access policy:
   - **Policy name:** Email verification
   - **Action:** Allow
   - **Include:** Emails ending in `@yourdomain.com`

**Result:** Users need to login before accessing app!

### **2. Update CORS (Production)**

Edit `.env.production`:
```bash
# Restrict to your domain only
CORS_ORIGINS=https://ollama-rag.yourdomain.com
```

Restart app:
```powershell
# Stop current process (Ctrl+C)
# Re-run
.\deploy.ps1
```

### **3. Rate Limiting**

Cloudflare Dashboard → Security → WAF → Rate Limiting Rules:
- **Name:** API Rate Limit
- **Match:** URI Path contains `/api/`
- **Rate:** 100 requests per minute

---

## 🛠️ **Troubleshooting**

### **Issue: Tunnel not connecting**

```powershell
# Check tunnel status
cloudflared tunnel info ollama-rag

# Test connection
cloudflared tunnel run --loglevel debug ollama-rag
```

### **Issue: 502 Bad Gateway**

**Cause:** FastAPI not running

**Fix:**
```powershell
# Check if app is running
Invoke-WebRequest -Uri http://localhost:8000/health

# If not, restart
.\deploy.ps1
```

### **Issue: Ollama timeout**

**Cause:** Model too large or CPU overloaded

**Fix:** Use smaller model:
```powershell
# Edit .env
# LLM_MODEL=llama3.2:1b  # Smaller, faster model
```

### **Issue: Out of memory**

**Fix:** Reduce context size:
```bash
# .env.production
OLLAMA_NUM_CTX=1024  # Smaller context window
```

---

## 📝 **Commands Cheat Sheet**

### **Application**
```powershell
# Start app
.\deploy.ps1

# Start manually
venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Run tests
pytest tests/ -v
```

### **Ollama**
```powershell
# List models
ollama list

# Pull model
ollama pull llama3.2:3b

# Remove model
ollama rm llama3.2:3b

# Check running models
ollama ps
```

### **Cloudflare Tunnel**
```powershell
# List tunnels
cloudflared tunnel list

# Run tunnel
cloudflared tunnel run ollama-rag

# Delete tunnel
cloudflared tunnel delete ollama-rag

# Service commands
Start-Service cloudflared
Stop-Service cloudflared
Restart-Service cloudflared
```

---

## 🎯 **Next Steps**

1. ✅ **Setup monitoring:** Integrate with Cloudflare Analytics
2. ✅ **Add authentication:** Enable Cloudflare Access
3. ✅ **Backup data:** Regular backups of `data/kb` folder
4. ✅ **Performance tuning:** Optimize based on usage patterns
5. ✅ **CI/CD:** Automate deployments with GitHub Actions

---

## 📚 **Additional Resources**

- **Cloudflare Tunnel Docs:** https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/
- **Ollama Docs:** https://ollama.ai/docs
- **FastAPI Docs:** https://fastapi.tiangolo.com
- **Project GitHub:** https://github.com/yourusername/ollama-rag

---

## 🆘 **Support**

- **Issues:** https://github.com/yourusername/ollama-rag/issues
- **Discussions:** https://github.com/yourusername/ollama-rag/discussions
- **Email:** support@yourdomain.com

---

**Deployment Date:** 2025-10-03  
**Version:** 1.0.0  
**Author:** Your Name  

🎉 **Happy deploying!** 🚀
