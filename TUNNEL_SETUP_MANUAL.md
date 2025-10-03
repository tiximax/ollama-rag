# 🌐 Cloudflare Tunnel - Manual Setup Instructions

**Status:** ✅ Cloudflared installed (v2025.8.1)  
**Server:** ✅ Running on http://localhost:8000

---

## 🚀 **Quick Manual Setup (5 Steps)**

Since the interactive script requires user input, here's a manual walkthrough:

### **Step 1: Login to Cloudflare** (Required once)

Open a **new PowerShell window** and run:
```powershell
cloudflared tunnel login
```

**What happens:**
- Browser opens automatically
- Login to your Cloudflare account
- Select your domain
- Certificate is saved to: `C:\Users\pc\.cloudflared\cert.pem`

✅ **Done when you see:** "You have successfully logged in."

---

### **Step 2: Create Tunnel**

```powershell
cloudflared tunnel create ollama-rag
```

**Expected output:**
```
Tunnel credentials written to C:\Users\pc\.cloudflared\<TUNNEL_ID>.json
Created tunnel ollama-rag with id <TUNNEL_ID>
```

**📝 IMPORTANT:** Copy the `<TUNNEL_ID>` - you'll need it!

---

### **Step 3: Create Configuration File**

Create file: `C:\Users\pc\.cloudflared\config.yml`

**Quick way:**
```powershell
# Replace <TUNNEL_ID> and <YOUR_DOMAIN> with your actual values
$tunnelId = "<TUNNEL_ID>"  # From step 2
$domain = "<YOUR_DOMAIN>"  # e.g., example.com
$subdomain = "ollama-rag"  # Or your preference

$config = @"
tunnel: $tunnelId
credentials-file: C:\Users\pc\.cloudflared\$tunnelId.json

ingress:
  - hostname: $subdomain.$domain
    service: http://localhost:8000
    originRequest:
      connectTimeout: 30s
  - service: http_status:404
"@

$config | Out-File -FilePath "$env:USERPROFILE\.cloudflared\config.yml" -Encoding UTF8
Write-Host "Config created!" -ForegroundColor Green
```

**Or manually create:** `C:\Users\pc\.cloudflared\config.yml`
```yaml
tunnel: <TUNNEL_ID>
credentials-file: C:\Users\pc\.cloudflared\<TUNNEL_ID>.json

ingress:
  - hostname: ollama-rag.yourdomain.com
    service: http://localhost:8000
    originRequest:
      connectTimeout: 30s
  - service: http_status:404
```

---

### **Step 4: Setup DNS**

**Option A: Automatic (Recommended)**
```powershell
# Replace with your values
$tunnelId = "<TUNNEL_ID>"
$fullDomain = "ollama-rag.yourdomain.com"

cloudflared tunnel route dns $tunnelId $fullDomain
```

**Option B: Manual (Cloudflare Dashboard)**
1. Go to: https://dash.cloudflare.com
2. Select your domain → DNS
3. Add record:
   - **Type:** CNAME
   - **Name:** ollama-rag (or your subdomain)
   - **Target:** `<TUNNEL_ID>.cfargotunnel.com`
   - **Proxy status:** Proxied (🟠 orange cloud ON)
   - Click **Save**

---

### **Step 5: Start Tunnel**

**Option A: Test Mode (Foreground)**
```powershell
cloudflared tunnel run ollama-rag
```

**Expected output:**
```
2025-10-03 INFO  Connection established
2025-10-03 INFO  Registered tunnel ollama-rag
```

✅ **Done!** Your app is now live at `https://ollama-rag.yourdomain.com`

**Option B: Production (Windows Service)**
```powershell
# Install as service
cloudflared service install

# Start service
Start-Service cloudflared

# Verify
Get-Service cloudflared
```

---

## 🧪 **Test Your Deployment**

### **1. Wait for DNS (2-3 minutes)**
```powershell
# Check DNS propagation
nslookup ollama-rag.yourdomain.com
```

### **2. Test Health Endpoint**
```powershell
Invoke-WebRequest https://ollama-rag.yourdomain.com/health
```

**Expected:** Status 200 OK

### **3. Open in Browser**
```
https://ollama-rag.yourdomain.com/docs
```

---

## 🔧 **Update CORS (Important!)**

After tunnel is working, update CORS:

```powershell
# Edit .env file
notepad .env

# Add your public domain to CORS_ORIGINS:
# CORS_ORIGINS=http://localhost:8000,https://ollama-rag.yourdomain.com

# Restart server
Stop-Process -Name python -Force
.\start.ps1
```

---

## 📊 **Management Commands**

### **Check Tunnel Status**
```powershell
# List all tunnels
cloudflared tunnel list

# Get tunnel info
cloudflared tunnel info ollama-rag

# Check service status
Get-Service cloudflared
```

### **Stop Tunnel**
```powershell
# If running foreground: Press Ctrl+C

# If running as service:
Stop-Service cloudflared
```

### **Restart Tunnel**
```powershell
Restart-Service cloudflared
```

### **View Logs**
```powershell
# If running foreground: logs appear in terminal

# If running as service:
Get-EventLog -LogName Application -Source cloudflared -Newest 10
```

---

## 🐛 **Troubleshooting**

### **Issue: "Failed to create tunnel"**
**Cause:** Already exists or authentication issue

**Fix:**
```powershell
# List existing tunnels
cloudflared tunnel list

# Delete if needed
cloudflared tunnel delete ollama-rag

# Re-login
cloudflared tunnel login
```

### **Issue: "502 Bad Gateway"**
**Cause:** Local server not running

**Fix:**
```powershell
# Check server
Invoke-WebRequest http://localhost:8000/health

# If not running
.\start.ps1
```

### **Issue: "DNS not resolving"**
**Cause:** DNS propagation delay

**Wait:** 2-5 minutes, then test:
```powershell
nslookup ollama-rag.yourdomain.com
# Or check: https://dnschecker.org
```

### **Issue: "CORS errors"**
**Cause:** Public domain not in CORS config

**Fix:**
```bash
# Edit .env
CORS_ORIGINS=http://localhost:8000,https://ollama-rag.yourdomain.com

# Restart server
```

---

## 📝 **Example Complete Setup**

Here's a complete example with actual commands:

```powershell
# 1. Login (one-time)
cloudflared tunnel login

# 2. Create tunnel
cloudflared tunnel create ollama-rag
# Output: Created tunnel ollama-rag with id abc123-def456-ghi789

# 3. Set variables
$tunnelId = "abc123-def456-ghi789"
$domain = "example.com"
$subdomain = "ollama-rag"

# 4. Create config
$config = @"
tunnel: $tunnelId
credentials-file: C:\Users\pc\.cloudflared\$tunnelId.json

ingress:
  - hostname: $subdomain.$domain
    service: http://localhost:8000
  - service: http_status:404
"@
$config | Out-File -FilePath "$env:USERPROFILE\.cloudflared\config.yml" -Encoding UTF8

# 5. Setup DNS
cloudflared tunnel route dns $tunnelId "$subdomain.$domain"

# 6. Start tunnel
cloudflared tunnel run ollama-rag

# 7. Test (in another terminal)
Start-Sleep -Seconds 10
Invoke-WebRequest "https://$subdomain.$domain/health"
```

---

## ✅ **Checklist**

- [ ] Cloudflared installed ✅ (Already done!)
- [ ] Cloudflare account with domain
- [ ] Run `cloudflared tunnel login`
- [ ] Run `cloudflared tunnel create ollama-rag`
- [ ] Copy tunnel ID
- [ ] Create config file with your domain
- [ ] Setup DNS (automatic or manual)
- [ ] Update CORS in .env
- [ ] Restart server
- [ ] Start tunnel
- [ ] Test public URL

---

## 🎯 **Quick Commands Summary**

```powershell
# Complete setup in 5 commands:
cloudflared tunnel login
cloudflared tunnel create ollama-rag
# [Create config file - see Step 3 above]
cloudflared tunnel route dns <TUNNEL_ID> ollama-rag.yourdomain.com
cloudflared tunnel run ollama-rag
```

---

## 📞 **Need Help?**

- **Cloudflare Docs:** https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/
- **Community:** https://community.cloudflare.com/
- **Local Docs:** See `TUNNEL_QUICKSTART.md` or `DEPLOY_GUIDE.md`

---

**Created:** 2025-10-03  
**Server:** ✅ Running  
**Cloudflared:** ✅ Installed  
**Status:** Ready to deploy!

🚀 **Follow the steps above and you'll be live in ~5 minutes!**
