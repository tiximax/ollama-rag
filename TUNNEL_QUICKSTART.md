# 🌐 Cloudflare Tunnel - Quick Start Guide

**Created:** 2025-10-03  
**Status:** ✅ Cloudflared installed (v2025.8.1)

---

## 🚀 **Super Quick Setup (Automated)**

### **Run the interactive setup script:**
```powershell
.\setup-tunnel.ps1
```

**This will:**
1. ✅ Check if cloudflared is installed
2. ✅ Verify server is running
3. 🔐 Login to Cloudflare (opens browser)
4. 🔧 Create tunnel
5. 🌐 Setup DNS record
6. ⚙️ Create config file
7. 🔒 Update CORS settings
8. ▶️ Option to start tunnel immediately

**Total time:** ~5 minutes

---

## 📝 **Manual Setup (Step by Step)**

### **Prerequisites:**
```powershell
# Already done! ✅
winget install --id Cloudflare.cloudflared
```

### **Step 1: Login**
```powershell
cloudflared tunnel login
```
- Opens browser
- Login to Cloudflare account
- Select your domain
- Certificate saved to: `C:\Users\pc\.cloudflared\cert.pem`

### **Step 2: Create Tunnel**
```powershell
cloudflared tunnel create ollama-rag
```
**Output:**
```
Tunnel credentials written to C:\Users\pc\.cloudflared\<TUNNEL_ID>.json
Created tunnel ollama-rag with id <TUNNEL_ID>
```
**⚠️ Save the TUNNEL_ID!**

### **Step 3: Configure Tunnel**

Create file: `C:\Users\pc\.cloudflared\config.yml`

```yaml
tunnel: <YOUR_TUNNEL_ID>
credentials-file: C:\Users\pc\.cloudflared\<YOUR_TUNNEL_ID>.json

ingress:
  - hostname: ollama-rag.yourdomain.com
    service: http://localhost:8000
    originRequest:
      connectTimeout: 30s
  - service: http_status:404
```

**Replace:**
- `<YOUR_TUNNEL_ID>` with actual tunnel ID
- `ollama-rag.yourdomain.com` with your domain

### **Step 4: Setup DNS**

**Option A: Automatic**
```powershell
cloudflared tunnel route dns <TUNNEL_ID> ollama-rag.yourdomain.com
```

**Option B: Manual (Cloudflare Dashboard)**
1. Go to: DNS → Records → Add record
2. Settings:
   - **Type:** CNAME
   - **Name:** ollama-rag
   - **Target:** `<TUNNEL_ID>.cfargotunnel.com`
   - **Proxy status:** Proxied (🟠 orange cloud)

### **Step 5: Update CORS**

Edit `.env`:
```bash
CORS_ORIGINS=http://localhost:8000,https://ollama-rag.yourdomain.com
```

Restart server:
```powershell
# Stop (Ctrl+C in server window)
.\start.ps1
```

### **Step 6: Start Tunnel**

**Option A: Foreground (testing)**
```powershell
cloudflared tunnel run ollama-rag
```

**Option B: Windows Service (production)**
```powershell
cloudflared service install
Start-Service cloudflared
```

---

## 🧪 **Test Your Deployment**

### **Check tunnel status:**
```powershell
cloudflared tunnel list
```

### **Test endpoints:**
```
✅ Public docs: https://ollama-rag.yourdomain.com/docs
✅ Health check: https://ollama-rag.yourdomain.com/health
✅ Test query: https://ollama-rag.yourdomain.com/api/query
```

### **Test with PowerShell:**
```powershell
# Health check
Invoke-WebRequest https://ollama-rag.yourdomain.com/health

# Query API
$body = @{ query = "Hello!" } | ConvertTo-Json
Invoke-RestMethod -Uri https://ollama-rag.yourdomain.com/api/query -Method POST -Body $body -Headers @{"Content-Type"="application/json"}
```

---

## 🔧 **Management Commands**

### **Tunnel Operations**
```powershell
# List all tunnels
cloudflared tunnel list

# Get tunnel info
cloudflared tunnel info ollama-rag

# Run tunnel (foreground)
cloudflared tunnel run ollama-rag

# Delete tunnel
cloudflared tunnel delete ollama-rag
```

### **Service Management (Windows)**
```powershell
# Install as service
cloudflared service install

# Start service
Start-Service cloudflared

# Stop service
Stop-Service cloudflared

# Restart service
Restart-Service cloudflared

# Check status
Get-Service cloudflared

# Uninstall service
cloudflared service uninstall
```

### **Logs**
```powershell
# View logs (if running foreground)
# Logs appear in terminal

# Service logs (Windows Event Viewer)
Get-EventLog -LogName Application -Source cloudflared -Newest 20

# Or enable file logging in config.yml:
# logfile: C:\Users\pc\.cloudflared\tunnel.log
# loglevel: info
```

---

## 🔐 **Security Best Practices**

### **1. Enable Cloudflare Access (Free!)**

Add authentication layer:

1. **Cloudflare Dashboard** → **Zero Trust** → **Access** → **Applications**
2. **Add an application:**
   - Name: Ollama RAG
   - Domain: `ollama-rag.yourdomain.com`
3. **Add access policy:**
   - Name: Email verification
   - Action: Allow
   - Include: Emails ending in `@yourdomain.com`

**Result:** Users must login before accessing!

### **2. Rate Limiting**

Cloudflare Dashboard → **Security** → **WAF** → **Rate Limiting Rules**
- Rule name: API Rate Limit
- Match: URI Path contains `/api/`
- Rate: 100 requests/minute

### **3. Firewall Rules**

Dashboard → **Security** → **WAF** → **Custom Rules**
- Block specific countries (optional)
- Allow only specific IPs (optional)
- Block bots (optional)

### **4. DDoS Protection**

**Enabled by default!** ✅
- Dashboard → **Security** → **DDoS**
- Configure sensitivity levels

---

## 🐛 **Troubleshooting**

### **Issue: Tunnel won't connect**
```powershell
# Check tunnel status
cloudflared tunnel info ollama-rag

# Test connection with debug
cloudflared tunnel run --loglevel debug ollama-rag
```

### **Issue: 502 Bad Gateway**
**Cause:** FastAPI server not running

**Fix:**
```powershell
# Check if server is running
Invoke-WebRequest http://localhost:8000/health

# If not, start it
.\start.ps1
```

### **Issue: DNS not resolving**
**Cause:** DNS propagation delay

**Wait:** Up to 5 minutes for DNS propagation

**Check:**
```powershell
# Test DNS
nslookup ollama-rag.yourdomain.com

# Or use online tools
# https://dnschecker.org
```

### **Issue: CORS errors in browser**
**Cause:** CORS not configured for public domain

**Fix:**
```bash
# Edit .env
CORS_ORIGINS=http://localhost:8000,https://ollama-rag.yourdomain.com

# Restart server
```

### **Issue: Certificate errors**
**Cause:** Login credentials expired

**Fix:**
```powershell
# Re-login
cloudflared tunnel login
```

---

## 📊 **Monitoring**

### **Cloudflare Analytics**
- Dashboard → **Analytics & Logs**
- Real-time traffic
- Bandwidth usage
- Cache hit rates
- Geographic distribution

### **Application Monitoring**
```powershell
# Health check
Invoke-WebRequest https://ollama-rag.yourdomain.com/health | Select-Object -ExpandProperty Content

# System resources
Get-Process python,ollama | Select-Object Name, WorkingSet, CPU
```

### **Uptime Monitoring (Free Tools)**
- UptimeRobot: https://uptimerobot.com
- StatusCake: https://www.statuscake.com
- Pingdom: https://www.pingdom.com

---

## 💡 **Pro Tips**

### **1. Multiple Services**
Edit `config.yml` to route multiple services:
```yaml
ingress:
  # Main app
  - hostname: ollama-rag.yourdomain.com
    service: http://localhost:8000
  
  # Admin panel (example)
  - hostname: admin.yourdomain.com
    service: http://localhost:9000
  
  # Catch-all
  - service: http_status:404
```

### **2. Path-based Routing**
```yaml
ingress:
  - hostname: api.yourdomain.com
    path: ^/v1/.*
    service: http://localhost:8000
```

### **3. Load Balancing** (Multiple servers)
```yaml
ingress:
  - hostname: ollama-rag.yourdomain.com
    service: http://loadbalancer:8000
    originRequest:
      originServerName: ollama-rag.yourdomain.com
```

### **4. Automatic Restarts**
For production, ensure tunnel restarts on system reboot:
```powershell
# Service mode handles this automatically
cloudflared service install
Start-Service cloudflared

# Set service to start automatically
Set-Service cloudflared -StartupType Automatic
```

---

## 📚 **Additional Resources**

- **Cloudflare Tunnel Docs:** https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/
- **Cloudflare Zero Trust:** https://developers.cloudflare.com/cloudflare-one/
- **Cloudflare API:** https://developers.cloudflare.com/api/
- **Community Forum:** https://community.cloudflare.com/

---

## ✅ **Quick Setup Checklist**

- [x] cloudflared installed (v2025.8.1)
- [ ] Cloudflare account with domain
- [ ] Tunnel created
- [ ] DNS configured
- [ ] Config file created
- [ ] CORS updated
- [ ] Tunnel running
- [ ] Public URL tested
- [ ] Authentication enabled (optional)
- [ ] Monitoring setup (optional)

---

## 🎯 **One-Command Setup**

For automated setup, just run:
```powershell
.\setup-tunnel.ps1
```

Follow the interactive prompts, and you'll be live in ~5 minutes! 🚀

---

**Created:** 2025-10-03  
**Status:** Ready to deploy  
**Support:** See `DEPLOY_GUIDE.md` or `CLOUDFLARE_TUNNEL_SETUP.md`

🎉 **Your app will be accessible worldwide!**
