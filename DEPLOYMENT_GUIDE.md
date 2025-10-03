# 🚀 Ollama RAG - Complete Deployment Guide

Hướng dẫn toàn diện để deploy Ollama RAG application trên Windows với Cloudflare Tunnel!

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Manual Setup](#manual-setup)
4. [Production Deployment](#production-deployment)
5. [Troubleshooting](#troubleshooting)
6. [Maintenance](#maintenance)

---

## 🎯 Prerequisites

### System Requirements

- **OS**: Windows 10/11 (64-bit)
- **RAM**: Minimum 8GB (16GB recommended for llama3.1:8b)
- **Disk**: 10GB free space
- **Network**: Internet connection

### Software Requirements

- **Python**: 3.8+ (tested with 3.12)
- **PowerShell**: 5.1+ (Windows default)
- **Git**: For version control
- **Ollama**: Latest version (0.12.0+)

### Optional

- **NSSM**: For Windows Service management
- **Custom Domain**: For branded Cloudflare Tunnel URL

---

## ⚡ Quick Start (5 minutes)

### 1. Clone Repository

```powershell
cd C:\Users\pc\Downloads
git clone https://github.com/tiximax/ollama-rag.git
cd ollama-rag
```

### 2. Install Dependencies

```powershell
# Install Python packages
pip install -r requirements.txt

# Install Ollama (if not already installed)
# Download from: https://ollama.com/download
```

### 3. Start All Services

```powershell
# One-command start!
.\start-all.ps1
```

That's it! 🎉 Services are now running:
- **Ollama**: http://localhost:11434
- **Backend**: http://localhost:8000
- **Docs**: http://localhost:8000/docs
- **Public URL**: Check PowerShell window for Cloudflare URL

---

## 🔧 Manual Setup (Step by Step)

### Step 1: Setup Ollama

```powershell
# Start Ollama service
Start-Process "ollama" -ArgumentList "serve" -WindowStyle Hidden

# Verify Ollama
ollama list

# Pull models (if needed)
ollama pull llama3.1:8b
ollama pull nomic-embed-text
```

### Step 2: Configure Environment

```powershell
# Create .env file (if not exists)
echo "VECTOR_BACKEND=faiss" > .env
echo "LLM_MODEL=llama3.1:8b" >> .env
echo "OLLAMA_BASE_URL=http://localhost:11434" >> .env
```

### Step 3: Start Backend

```powershell
# Start FastAPI backend
uvicorn src.api.server:app --host 0.0.0.0 --port 8000 --reload
```

### Step 4: Setup Cloudflare Tunnel

```powershell
# Download cloudflared (if not already downloaded)
# It should be in the project directory

# Login to Cloudflare
.\cloudflared.exe tunnel login

# Create tunnel
.\cloudflared.exe tunnel create ollama-rag

# Start Quick Tunnel (easiest method)
.\cloudflared.exe tunnel --url http://localhost:8000
```

### Step 5: Test Deployment

```powershell
# Test local endpoints
curl http://localhost:8000/health
curl http://localhost:8000/docs

# Test public URL (use URL from cloudflared output)
curl https://your-tunnel-url.trycloudflare.com/health
```

---

## 🏭 Production Deployment

### Option A: Auto-Start Scripts (Recommended for Development)

#### Using start-all.ps1

```powershell
# Start everything
.\start-all.ps1

# Stop everything
.\stop-all.ps1
```

**Pros:**
- ✅ Quick and easy
- ✅ See logs in real-time
- ✅ Easy debugging

**Cons:**
- ❌ Manual start after reboot
- ❌ Multiple PowerShell windows

---

### Option B: Windows Services (Recommended for Production)

See detailed guide: [WINDOWS_SERVICE_SETUP.md](./WINDOWS_SERVICE_SETUP.md)

#### Quick Service Setup

```powershell
# Run as Administrator!

# 1. Download NSSM
Invoke-WebRequest -Uri "https://nssm.cc/release/nssm-2.24.zip" -OutFile "$env:TEMP\nssm.zip"
Expand-Archive -Path "$env:TEMP\nssm.zip" -DestinationPath "$env:TEMP\nssm"
Copy-Item "$env:TEMP\nssm\nssm-2.24\win64\nssm.exe" .\

# 2. Install services
.\nssm.exe install OllamaService "ollama" "serve"
.\nssm.exe install OllamaRAGBackend python "-m uvicorn src.api.server:app --host 0.0.0.0 --port 8000"
.\cloudflared.exe service install

# 3. Configure auto-start
.\nssm.exe set OllamaService Start SERVICE_AUTO_START
.\nssm.exe set OllamaRAGBackend Start SERVICE_AUTO_START
.\nssm.exe set OllamaRAGBackend DependOnService OllamaService

# 4. Start services
Start-Service OllamaService, OllamaRAGBackend
.\cloudflared.exe service start
```

**Pros:**
- ✅ Auto-start on boot
- ✅ Runs in background
- ✅ Production-ready
- ✅ System integration

**Cons:**
- ❌ Requires admin privileges
- ❌ More complex setup

---

### Option C: Docker (If Docker Works)

See: [docker-compose.yml](./docker-compose.yml) and [Dockerfile](./Dockerfile)

```powershell
# Build and run
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

---

## 🌍 Public Access Options

### Option 1: Quick Tunnel (Free, Easiest)

```powershell
.\cloudflared.exe tunnel --url http://localhost:8000
```

- ✅ Free, no domain needed
- ✅ Instant setup
- ✅ HTTPS included
- ❌ Random URL (changes every restart)
- ❌ Not for production

### Option 2: Named Tunnel (Free, Custom Domain)

Requires: Your own domain added to Cloudflare

```powershell
# Create tunnel
.\cloudflared.exe tunnel create ollama-rag

# Route DNS
.\cloudflared.exe tunnel route dns ollama-rag api.yourdomain.com

# Start tunnel with config
.\cloudflared.exe tunnel --config cloudflare-tunnel-config.yml run ollama-rag
```

- ✅ Custom URL (api.yourdomain.com)
- ✅ Free SSL/TLS
- ✅ DDoS protection
- ✅ Production-ready
- ❌ Requires domain

See: [CLOUDFLARE_TUNNEL_SETUP.md](./CLOUDFLARE_TUNNEL_SETUP.md)

---

## 🔍 Verification & Testing

### Health Checks

```powershell
# Local health check
curl http://localhost:8000/health

# Public health check
curl https://your-url.trycloudflare.com/health

# Expected response:
# {
#   "status": "healthy",
#   "ollama_connected": true,
#   "db": "chroma",
#   "version": "0.15.0"
# }
```

### API Testing

```powershell
# Test query endpoint (PowerShell)
$body = @{query='What is RAG?'; k=3} | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:8000/api/query -Method Post -Body $body -ContentType 'application/json'

# Test with curl
curl -X POST http://localhost:8000/api/query -H "Content-Type: application/json" -d "{\"query\":\"What is RAG?\",\"k\":3}"
```

### Load Testing

```powershell
# Simple load test
for ($i=1; $i -le 10; $i++) {
    Write-Host "Request $i"
    curl http://localhost:8000/health
}
```

---

## 📊 Monitoring

### Service Status

```powershell
# Check services
Get-Service | Where-Object {$_.Name -like "*Ollama*"}

# Check processes
Get-Process ollama, python, cloudflared

# Check ports
netstat -ano | findstr :8000
netstat -ano | findstr :11434
```

### Logs

```powershell
# Backend logs (if running as service)
Get-Content logs\backend.log -Tail 50 -Wait

# Tunnel logs
Get-Content logs\tunnel.log -Tail 50 -Wait

# Windows Event Logs
Get-EventLog -LogName Application -Source OllamaRAGBackend -Newest 10
```

### Performance

```powershell
# API latency
Measure-Command {Invoke-RestMethod http://localhost:8000/health}

# Ollama latency
Measure-Command {Invoke-RestMethod http://localhost:11434/api/tags}
```

---

## 🔧 Troubleshooting

### Backend won't start

```powershell
# Check Python
python --version

# Check dependencies
pip list | findstr fastapi

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Check port
netstat -ano | findstr :8000
# If port busy: taskkill /PID <PID> /F
```

### Ollama connection failed

```powershell
# Verify Ollama running
Get-Process ollama

# Test Ollama API
curl http://localhost:11434/api/tags

# Restart Ollama
Get-Process ollama | Stop-Process -Force
Start-Process ollama -ArgumentList serve -WindowStyle Hidden
```

### Cloudflare Tunnel issues

```powershell
# Check cloudflared
.\cloudflared.exe --version

# Re-login
.\cloudflared.exe tunnel login

# List tunnels
.\cloudflared.exe tunnel list

# Check tunnel status
.\cloudflared.exe tunnel info ollama-rag
```

### Port conflicts

```powershell
# Find what's using port 8000
netstat -ano | findstr :8000

# Kill process
taskkill /PID <PID> /F

# Or use different port
uvicorn src.api.server:app --host 0.0.0.0 --port 8001
```

### Memory issues

```powershell
# Check memory usage
Get-Process ollama, python | Select-Object Name, @{Name='Memory(MB)';Expression={[math]::Round($_.WS/1MB,2)}}

# Use smaller model
ollama pull tinyllama  # 637MB instead of 4.9GB
# Update .env: LLM_MODEL=tinyllama
```

---

## 🔄 Maintenance

### Update Application

```powershell
# Pull latest code
git pull origin master

# Update dependencies
pip install -r requirements.txt --upgrade

# Restart services
.\stop-all.ps1
.\start-all.ps1
```

### Update Ollama Models

```powershell
# Pull latest model
ollama pull llama3.1:8b

# Remove old models
ollama rm old-model
```

### Backup Data

```powershell
# Backup ChromaDB
Copy-Item -Path "data\chroma" -Destination "backups\chroma_$(Get-Date -Format 'yyyyMMdd')" -Recurse

# Backup logs
Copy-Item -Path "logs" -Destination "backups\logs_$(Get-Date -Format 'yyyyMMdd')" -Recurse
```

### Clean Up

```powershell
# Clear logs
Remove-Item logs\*.log

# Clear cache
Remove-Item data\cache\* -Recurse

# Restart services
.\stop-all.ps1
.\start-all.ps1
```

---

## 🎯 Performance Tuning

### Optimize Backend

```env
# .env settings for performance
VECTOR_BACKEND=faiss  # Faster than chroma
LLM_MODEL=llama3.1:8b  # Balance between speed and quality
OLLAMA_NUM_PARALLEL=4  # Concurrent requests
OLLAMA_NUM_GPU=1  # Use GPU if available
```

### Optimize Ollama

```powershell
# Set environment variables for Ollama
$env:OLLAMA_NUM_PARALLEL = "4"
$env:OLLAMA_MAX_LOADED_MODELS = "2"
$env:OLLAMA_KEEP_ALIVE = "5m"

# Restart Ollama with optimizations
Get-Process ollama | Stop-Process -Force
Start-Process ollama -ArgumentList serve -WindowStyle Hidden
```

### Rate Limiting

Already configured via `slowapi` in the backend:
- **Default**: 100 requests/minute
- **Query endpoints**: 20 requests/minute

---

## 📚 Additional Resources

- **API Documentation**: http://localhost:8000/docs (Swagger UI)
- **Ollama Docs**: https://ollama.com/docs
- **Cloudflare Tunnel Docs**: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/
- **GitHub Repository**: https://github.com/tiximax/ollama-rag

---

## 🎉 Success Checklist

✅ Ollama running on port 11434
✅ Backend running on port 8000
✅ Cloudflare Tunnel connected
✅ Health endpoint returns `{"status": "healthy"}`
✅ Can query API locally
✅ Can access API via public URL
✅ Services auto-start (if using Windows Services)
✅ Monitoring and logs working

---

## 💡 Pro Tips

1. **Use `start-all.ps1`** for quick development
2. **Setup Windows Services** for production
3. **Use Named Tunnel** with custom domain for branding
4. **Monitor logs** regularly for issues
5. **Backup data** before major updates
6. **Use smaller models** (tinyllama) for testing
7. **Rate limiting** is already configured (slowapi)
8. **CORS fixed** - no wildcard in production!

---

## 🆘 Need Help?

- **Issues**: https://github.com/tiximax/ollama-rag/issues
- **Discussions**: https://github.com/tiximax/ollama-rag/discussions
- **Email**: support@bitsness.vn

---

**Built with ❤️ by the Ollama RAG Team**

**Version**: 0.4.0
**Last Updated**: 2025-10-03
