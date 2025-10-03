# Cloudflare Tunnel Setup Guide

**Expose Ollama RAG app to internet securely via Cloudflare Tunnel** 🌐

---

## 📋 Prerequisites

- Cloudflare account (free)
- Domain registered (or use free Cloudflare subdomain)
- Docker installed
- App running locally

---

## 🚀 Quick Setup (10 minutes)

### Step 1: Install cloudflared

**Windows:**
```powershell
# Download cloudflared
Invoke-WebRequest -Uri "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe" -OutFile "cloudflared.exe"

# Move to a permanent location
Move-Item cloudflared.exe C:\Windows\System32\cloudflared.exe

# Verify installation
cloudflared --version
```

**Alternative (Chocolatey):**
```powershell
choco install cloudflared
```

---

### Step 2: Login to Cloudflare

```bash
cloudflared tunnel login
```

This will:
1. Open browser
2. Select your domain
3. Authorize cloudflared

---

### Step 3: Create Tunnel

```bash
# Create a new tunnel
cloudflared tunnel create ollama-rag

# This creates:
# - Tunnel ID
# - Credentials file at: C:\Users\<user>\.cloudflared\<tunnel-id>.json
```

**Note the Tunnel ID** from output!

---

### Step 4: Create Config File

Create `C:\Users\pc\.cloudflared\config.yml`:

```yaml
tunnel: <YOUR-TUNNEL-ID>
credentials-file: C:\Users\pc\.cloudflared\<YOUR-TUNNEL-ID>.json

ingress:
  # Route for main app
  - hostname: ollama-rag.yourdomain.com
    service: http://localhost:8000

  # Catch-all rule (required)
  - service: http_status:404
```

**Replace:**
- `<YOUR-TUNNEL-ID>` with your actual tunnel ID
- `ollama-rag.yourdomain.com` with your domain/subdomain

---

### Step 5: Route DNS

```bash
# Point your domain to the tunnel
cloudflared tunnel route dns ollama-rag ollama-rag.yourdomain.com
```

This automatically creates a CNAME record in Cloudflare DNS.

---

### Step 6: Run Tunnel

**Option A: Foreground (for testing)**
```bash
cloudflared tunnel run ollama-rag
```

**Option B: Background (Windows Service)**
```powershell
# Install as service
cloudflared service install

# Start service
Start-Service cloudflared
```

**Option C: Docker (in docker-compose)**
See `docker-compose.yml` - uncomment cloudflared service

---

## 🎯 Complete Example

### 1. Start Docker Stack

```bash
# Build and start all services
docker-compose up -d --build

# Check logs
docker-compose logs -f
```

### 2. Start Cloudflare Tunnel

**Separate terminal:**
```bash
cloudflared tunnel run ollama-rag
```

### 3. Access Your App

Visit: `https://ollama-rag.yourdomain.com`

✅ Secure HTTPS automatically!
✅ No port forwarding needed!
✅ No firewall rules!

---

## 🔧 Configuration Options

### Multiple Services

Edit `config.yml` for multiple routes:

```yaml
tunnel: <YOUR-TUNNEL-ID>
credentials-file: C:\Users\pc\.cloudflared\<YOUR-TUNNEL-ID>.json

ingress:
  # Frontend
  - hostname: ollama-rag.yourdomain.com
    service: http://localhost:8000

  # API only
  - hostname: api.ollama-rag.yourdomain.com
    service: http://localhost:8000
    path: ^/api/.*

  # Health check
  - hostname: health.ollama-rag.yourdomain.com
    service: http://localhost:8000
    path: ^/health

  # Catch-all
  - service: http_status:404
```

---

### Update CORS

Update `docker-compose.yml` with your public domain:

```yaml
environment:
  - CORS_ORIGINS=https://ollama-rag.yourdomain.com
```

Rebuild:
```bash
docker-compose down
docker-compose up -d --build
```

---

## 🐛 Troubleshooting

### Tunnel Not Connecting

```bash
# Check tunnel status
cloudflared tunnel info ollama-rag

# Check if service is running
Get-Service cloudflared  # Windows
```

### DNS Not Resolving

```bash
# Verify DNS record
nslookup ollama-rag.yourdomain.com

# Should show Cloudflare IP
```

### Backend Not Accessible

```bash
# Test locally first
curl http://localhost:8000/health

# Check Docker logs
docker-compose logs backend
```

---

## 📊 Architecture

```
┌─────────────────────────────────────────┐
│         Internet Users                   │
└────────────────┬────────────────────────┘
                 │
                 │ HTTPS
                 │
┌────────────────▼────────────────────────┐
│     Cloudflare Network (Global)         │
│     - DDoS Protection                   │
│     - SSL/TLS                           │
│     - CDN                               │
└────────────────┬────────────────────────┘
                 │
                 │ Cloudflare Tunnel
                 │ (Encrypted)
                 │
┌────────────────▼────────────────────────┐
│     Your Local Machine (Windows)        │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │  cloudflared (Port 0)           │   │
│  └──────────┬──────────────────────┘   │
│             │                           │
│  ┌──────────▼──────────────────────┐   │
│  │  Docker Compose                  │   │
│  │                                  │   │
│  │  ┌──────────────────────────┐   │   │
│  │  │  Backend (Port 8000)     │   │   │
│  │  │  - FastAPI               │   │   │
│  │  │  - Web UI                │   │   │
│  │  └───────────┬──────────────┘   │   │
│  │              │                   │   │
│  │  ┌───────────▼──────────────┐   │   │
│  │  │  Ollama (Port 11434)     │   │   │
│  │  │  - LLM Models            │   │   │
│  │  └──────────────────────────┘   │   │
│  └──────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

---

## 🔒 Security Best Practices

### 1. Enable Cloudflare Access (Optional)

Protect your app with authentication:

```bash
# In Cloudflare Dashboard:
# Zero Trust > Access > Applications > Add an application
# Add email-based auth or SSO
```

### 2. Rate Limiting

```yaml
# In config.yml, add:
ingress:
  - hostname: ollama-rag.yourdomain.com
    service: http://localhost:8000
    originRequest:
      noTLSVerify: false
      connectTimeout: 30s
      keepAliveTimeout: 90s
```

### 3. Logs

```bash
# Check tunnel logs
cloudflared tunnel logs ollama-rag
```

---

## 📈 Monitoring

### Check Tunnel Status

```bash
cloudflared tunnel info ollama-rag
```

### View Metrics

Cloudflare Dashboard > Zero Trust > Access > Tunnels

Shows:
- Request count
- Bandwidth usage
- Uptime

---

## 🎉 Done!

Your Ollama RAG app is now:
- ✅ Publicly accessible via HTTPS
- ✅ Protected by Cloudflare
- ✅ No port forwarding needed
- ✅ Free SSL certificate
- ✅ DDoS protection included

---

## 📚 Resources

- [Cloudflare Tunnel Docs](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)
- [cloudflared GitHub](https://github.com/cloudflare/cloudflared)
- [Tunnel Dashboard](https://dash.cloudflare.com/)

---

**Need help?** Check the troubleshooting section or open an issue!
